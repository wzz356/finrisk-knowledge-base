"""Load pinned organization material without imposing a case snapshot limit."""
import copy
from pathlib import Path
from runtime_common import read,rows,sha,textsha
from frozen_legal_registry import LegalRegistry

def _index(records,key):
    out={}
    for r in records:
        value=r.get(key)
        if not isinstance(value,str) or not value or value in out:raise ValueError('duplicate or missing '+key)
        out[value]=r
    return out

class KnowledgeAssets:
    def __init__(self,root,lock):
        self.root=Path(root).resolve();path=self.root/'expanded/contracts/knowledge_manifest.json'
        if sha(path)!=lock['expanded_manifest_sha256']:raise ValueError('knowledge manifest pin mismatch')
        manifest=read(path)
        if manifest.get('schema')!='finrisk-enhancement-knowledge-v1' or manifest.get('enhancement_version')!='knowledge-organization-expanded-v1':raise ValueError('unknown enhancement version')
        if manifest['base_versions']!=lock['base_versions']:raise ValueError('asset base versions differ')
        for name,meta in manifest['files'].items():
            p=(self.root/name).resolve()
            if not p.is_relative_to(self.root) or p.stat().st_size!=meta['bytes'] or sha(p)!=meta['sha256']:raise ValueError('asset payload changed')
        adapter=Path(__file__).with_name('frozen_legal_registry.py')
        if sha(adapter)!=lock['legal_adapter']['copied_code_sha256']:raise ValueError('legal adapter changed')
        self.versions=copy.deepcopy(lock['base_versions'])
        self.legal=LegalRegistry(self.root/'legal',lock['legal_manifest_sha256'])
        self.cards=_index(rows(self.root/'expanded/knowledge/mechanisms.jsonl'),'mechanism_id')
        self.links=list(rows(self.root/'expanded/knowledge/case_links.jsonl'))
        self.spans=_index(rows(self.root/'expanded/knowledge/source_spans.jsonl'),'span_id')
        sources=_index(rows(self.root/'expanded/knowledge/source_documents.jsonl'),'file_id')
        for s in self.spans.values():
            full=sources[s['file_id']]['full_text'];a,b=s['start'],s['end']
            if type(a) is not int or type(b) is not int or not 0<=a<b<=len(full) or full[a:b]!=s['text'] or textsha(s['text'])!=s['text_sha256']:raise ValueError('case guide source quotation mismatch')
        for card in self.cards.values():
            if card.get('human_approved') is not False or card.get('label_mapping_is_automatic') is not False:raise ValueError('guide provenance differs')
            if any(a not in self.legal.articles for a in card['article_ids']):raise ValueError('dangling legal reference')
        for link in self.links:
            if link['mechanism_id'] not in self.cards or link['span_id'] not in self.spans:raise ValueError('dangling case-guide link')
        self.navigation=read(self.root/'expanded/navigation/index.json')
        if self.navigation.get('hard_filter') is not False:raise ValueError('navigation cannot restrict corpus retrieval')
        if len(self.cards)!=12 or len(self.legal.articles)!=67:raise ValueError('unexpected source material count')
        self.official_label_coverage=read(self.root/'expanded/navigation/label_coverage.json')

    def list_mechanisms(self):return copy.deepcopy(self.navigation['mechanisms'])

    def read_mechanism(self,mechanism_id,level='L0'):
        if mechanism_id not in self.cards or level not in ['L0','L1','L2']:raise ValueError('unknown mechanism or level')
        c=copy.deepcopy(self.cards[mechanism_id])
        if level=='L0':return {k:c[k] for k in ['mechanism_id','title','overview','identity','coverage','human_approved']}
        if level=='L2':
            ids=sorted({l['span_id'] for l in self.links if l['mechanism_id']==mechanism_id})
            c.update(case_evidence=[copy.deepcopy(self.spans[s]) for s in ids],legal_evidence=[self.read_article(a) for a in c['article_ids']])
        return c

    def read_article(self,article_id,include_dependencies=True,as_of=None):return self.legal.read_article(article_id,include_dependencies,as_of)

    def coverage(self,mechanism_id):
        if mechanism_id not in self.cards:raise ValueError('unknown mechanism')
        card=self.cards[mechanism_id]
        return copy.deepcopy(dict(material_scope=card['coverage'],dependency_reading=self.legal.dependency_closure(card['article_ids']),
            normative_applicability=dict(status='not_assessed_for_current_input',axes=card['scope_axes']),
            all_official_labels_covered=False,official_label_coverage=self.official_label_coverage,
            current_input_facts_assessed=False,full_corpus_relevance_known=False,human_approved=False))
