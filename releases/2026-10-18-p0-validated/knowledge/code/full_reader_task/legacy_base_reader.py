"""Read-only knowledge consumer, pinned to a reviewed manifest and versions."""
import copy
import importlib.util
import json
from pathlib import Path
from .primitives import canonical_sha,sha,textsha,rows,read


class KnowledgeReader:
    def __init__(self,bundle,*,expected_versions=None,expected_manifest_sha256=None):
        self.root=Path(bundle).resolve()
        if not expected_manifest_sha256 or sha(self.root/'manifest.json')!=expected_manifest_sha256:
            raise ValueError('missing or incompatible manifest fingerprint')
        self.manifest=read(self.root/'manifest.json')
        if self.manifest.get('schema')!='finrisk-read-consumer-v1':raise ValueError('unsupported schema')
        if not expected_versions or set(expected_versions)!={'content','projection','articles','rules','scope'} or self.manifest['versions']!=expected_versions:
            raise ValueError('missing or incompatible versions')
        self.versions=copy.deepcopy(expected_versions)
        for name,meta in self.manifest['files'].items():
            p=(self.root/name).resolve()
            if not p.is_relative_to(self.root) or sha(p)!=meta['sha256']:raise ValueError('payload fingerprint mismatch: '+name)
        required={'units.jsonl','sources.jsonl','candidates.jsonl','rebinds.jsonl','articles.jsonl','legal_sources.jsonl'}
        if not required<=set(self.manifest['files']):raise ValueError('required data not registered')
        def unique(name,key):
            result={}
            for r in rows(self.root/name):
                if r[key] in result:raise ValueError('duplicate ID: '+r[key])
                result[r[key]]=r
            return result
        self.units=unique('units.jsonl','unit_id');self.sources=unique('sources.jsonl','file_id')
        self.candidates=unique('candidates.jsonl','file_id');self.rebinds=unique('rebinds.jsonl','unit_id')
        self.articles=unique('articles.jsonl','article_id');self.legal_sources=unique('legal_sources.jsonl','source_id')
        for source in self.sources.values():
            if textsha(source['full_text'])!=source['text_sha256']:raise ValueError('source text fingerprint mismatch')
        for fid,candidate in self.candidates.items():
            if candidate['draft']['file_id']!=fid or canonical_sha(candidate['draft'])!=candidate['effective_draft_json_sha256']:
                raise ValueError('current draft fingerprint mismatch')
        for unit in self.units.values():
            source=self.sources.get(unit['file_id']);candidate=self.candidates.get(unit['file_id'])
            if source is None or candidate is None or unit['source_sha256']!=source['source_sha256']:
                raise ValueError('source/current draft identity mismatch')
            current=candidate['effective_draft_json_sha256'];old=unit['candidate_sha256']
            patch=self.rebinds.get(unit['unit_id'])
            if patch:
                if (patch['file_id']!=unit['file_id'] or patch['expected_baseline_draft_sha256']!=old or
                    patch['current_effective_draft_sha256']!=current or patch['requires_versions']!=self.versions or
                    patch['allowed_changed_fields']!=['candidate_sha256'] or patch['ranking_text_changed'] is not False or
                    patch['preserve_stable_case_behavior_IDs'] is not True):raise ValueError('invalid metadata-only rebind')
            elif old!=current:raise ValueError('stale candidate binding without reviewed patch')
            for key in ['source_spans','parent_source_spans','context_spans']:
                for span in unit.get(key) or []:self._literal(source,span)
            for association in unit.get('associations') or []:
                for quote_key,span_key in [('party_quote','party_source_spans'),('quote','quote_source_spans')]:
                    spans=association.get(span_key) or []
                    for span in spans:self._literal(source,span)
                    quote=association.get(quote_key)
                    if quote and spans and quote not in [self._literal(source,s) for s in spans]:
                        raise ValueError('association quotation mismatch')
        if not set(self.rebinds)<=set(self.units):raise ValueError('rebind references unregistered unit')
        for article in self.articles.values():
            source=self.legal_sources.get(article['source_id'])
            start,end=article['start'],article['end']
            if (not source or type(start) is not int or type(end) is not int or
                not 0<=start<end<=len(source['text'])):
                raise ValueError('invalid legal article source range')
            if (not source or textsha(source['text'])!=article['original_source_text_sha256'] or
                source['text'][article['start']:article['end']]!=article['text'] or textsha(article['text'])!=article['text_sha256']):
                raise ValueError('legal article source mismatch')
        self.scope=None;scope_dir=self.manifest.get('scope_subdir')
        if scope_dir:
            module_path=self.root/scope_dir/'evidence_loader.py'
            if str(Path(scope_dir)/'evidence_loader.py').replace('\\','/') not in self.manifest['files']:
                raise ValueError('scope reader code not registered')
            spec=importlib.util.spec_from_file_location('pinned_scope_reader',module_path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            self.scope=module.EvidenceLoader(self.root/scope_dir,expected_versions=self.versions)
        self.spans={}
        for uid in self.units:
            for layer in ['hit','extended']:
                for span in self._segments(uid,layer):self._register(span)
            if self.scope and uid in self.scope.units:
                for span in self._segments(uid,'supplement'):self._register(span)

    @staticmethod
    def _literal(source,span):
        start,end=span['start'],span['end']
        if type(start) is not int or type(end) is not int or not 0<=start<end<=len(source['full_text']):
            raise ValueError('invalid registered source range')
        return source['full_text'][start:end]

    def _register(self,span):
        previous=self.spans.get(span['span_id'])
        if previous is not None and previous!=span:raise ValueError('conflicting span ID')
        self.spans[span['span_id']]=span

    def _segments(self,uid,layer):
        unit=self.units[uid];source=self.sources[unit['file_id']]
        if self.scope and uid in self.scope.units:
            segments=copy.deepcopy(self.scope.read(uid,layer=layer)['segments'])
            for segment in segments:
                if self._literal(source,segment)!=segment['text']:raise ValueError('reviewed scope/current source mismatch')
            return segments
        if layer=='supplement':raise ValueError('same-behavior supplement not reviewed for this unit')
        positions=unit['source_spans'] if layer=='hit' else unit.get('parent_source_spans') or unit.get('context_spans') or unit['source_spans']
        return [dict(span_id=f'IDXSPAN:{uid}:{layer}:{i}',file_id=unit['file_id'],layer=layer,
            start=p['start'],end=p['end'],text=self._literal(source,p),text_sha256=textsha(self._literal(source,p)),
            source_sha256=source['source_sha256']) for i,p in enumerate(positions)]

    def read(self,unit_id,*,layer='hit'):
        if unit_id not in self.units:raise ValueError('unknown unit ID')
        if layer not in ['hit','supplement','extended']:raise ValueError('unknown evidence layer')
        unit=self.units[unit_id];segments=self._segments(unit_id,layer)
        return dict(unit_id=unit_id,file_id=unit['file_id'],versions=copy.deepcopy(self.versions),
            stable_case_ids=copy.deepcopy(unit.get('case_ids') or []),stable_behavior_ids=copy.deepcopy(unit.get('behavior_ids') or []),
            associations=copy.deepcopy(unit.get('associations') or []),layer=layer,segments=segments,
            text='\n'.join(s['text'] for s in segments),
            source_sha256=unit['source_sha256'],current_draft_sha256=self.candidates[unit['file_id']]['effective_draft_json_sha256'],
            binding_repaired_by_metadata_overlay=unit_id in self.rebinds,
            scope_reviewed=self.scope is not None and unit_id in self.scope.units,
            source_evidence_ambiguous=unit.get('evidence_ambiguous'),
            may_include_other_actors_or_behaviors=True if layer=='extended' or unit.get('evidence_ambiguous') is True else None,
            join_semantics='separate_registered_spans_not_one_continuous_quote_or_shared_attribution',
            attribution_status='candidate_associations_preserved_not_current_query_fact',human_approved=False,
            runtime_relevance=None,score_interpretation='ranking_score_not_violation_probability')

    def read_span(self,span_id):
        if span_id not in self.spans:raise ValueError('unknown registered span ID')
        return copy.deepcopy(self.spans[span_id])

    def read_article(self,article_id):
        if article_id not in self.articles:raise ValueError('unknown registered legal article')
        result=copy.deepcopy(self.articles[article_id])
        result.update(reading_identity='official_text_snapshot_not_model_rule',
            current_business_fact_proof=False,historical_case_applicability_confirmed=False,human_approved=False)
        return result

