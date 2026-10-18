"""标准库只读证据加载器；不搜索、不改写原文、不决定违法或归属。"""
import copy
import hashlib
import json
from pathlib import Path


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(rows, key):
    result = {}
    for row in rows:
        if row[key] in result:
            raise ValueError('duplicate registered ID: ' + row[key])
        result[row[key]] = row
    return result


class EvidenceLoader:
    """expected_versions 必须与交接包五类版本完全相同。"""

    def __init__(self, bundle_dir, *, expected_versions=None):
        self.root = Path(bundle_dir).resolve()
        self.manifest = json.loads((self.root / 'handoff_manifest.json').read_text(encoding='utf-8'))
        if (not expected_versions or
                expected_versions != self.manifest.get('versions') or
                set(expected_versions) != {'content', 'projection', 'articles', 'rules', 'scope'}):
            raise ValueError('version missing or incompatible')
        if self.manifest.get('schema') != 'finrisk-evidence-handoff-v1':
            raise ValueError('version unsupported schema')
        for name, receipt in self.manifest['files'].items():
            target = (self.root / name).resolve()
            if not target.is_relative_to(self.root):
                raise ValueError('scope path outside bundle')
            if _sha(target.read_bytes()) != receipt['sha256']:
                raise ValueError('fingerprint mismatch: ' + name)
        for name in ['sources.jsonl', 'spans.jsonl', 'scope_overlays.jsonl']:
            if name not in self.manifest['files']:
                raise ValueError('fingerprint registration missing: ' + name)
        def rows(name):
            with (self.root / name).open(encoding='utf-8') as f:
                return [json.loads(line) for line in f if line.strip()]
        self.sources = _unique(rows('sources.jsonl'), 'source_id')
        self.spans = _unique(rows('spans.jsonl'), 'span_id')
        self.units = _unique(rows('scope_overlays.jsonl'), 'unit_id')
        if set(self.spans) & set(self.units):
            raise ValueError('duplicate ID across unit/span namespace')
        self.span_units = {}
        for source in self.sources.values():
            if _sha(source['text'].encode('utf-8')) != source['source_sha256']:
                raise ValueError('fingerprint source text mismatch')
        for span in self.spans.values():
            source = self.sources.get(span['source_id'])
            if source is not None and span.get('source_sha256', source['source_sha256']) != source['source_sha256']:
                raise ValueError('fingerprint span source mismatch')
            start, end = span['start'], span['end']
            if (source is None or type(start) is not int or type(end) is not int or
                    not 0 <= start < end <= len(source['text']) or
                    source['text'][start:end] != span['text'] or
                    _sha(span['text'].encode('utf-8')) != span['text_sha256']):
                raise ValueError('span invalid or not literal source')
        for unit in self.units.values():
            source = self.sources.get(unit['source_id'])
            if source is None or unit['source_sha256'] != source['source_sha256']:
                raise ValueError('fingerprint unit source mismatch')
            for layer, ids in unit['layers'].items():
                if layer not in ('hit', 'supplement', 'extended'):
                    raise ValueError('scope unknown layer')
                for span_id in ids:
                    span = self.spans.get(span_id)
                    if span is None or span['source_id'] != unit['source_id'] or span['layer'] != layer:
                        raise ValueError('scope span not registered for unit/layer')
                    self.span_units.setdefault(span_id, []).append(unit['unit_id'])
        if set(self.spans) != set(self.span_units):
            raise ValueError('scope orphan span')

    def read(self, identifier, *, layer='hit', start=None, end=None):
        """默认只返回命中原句；扩展、补充需显式指定。仅接受登记的完整区间。"""
        if layer not in ('hit', 'supplement', 'extended'):
            raise ValueError('scope unknown layer')
        if identifier in self.units:
            if start is not None or end is not None:
                raise ValueError('range requires registered span ID')
            unit = self.units[identifier]
            ids = unit['layers'].get(layer, [])
            result = copy.deepcopy(unit)
        elif identifier in self.spans:
            span = self.spans[identifier]
            if span['layer'] != layer:
                raise ValueError('scope span layer mismatch')
            if ((start is not None or end is not None) and
                    (start, end) != (span['start'], span['end'])):
                raise ValueError('range not registered')
            parents = self.span_units[identifier]
            result = copy.deepcopy(self.units[parents[0]])
            result['registered_parent_unit_ids'] = list(parents)
            ids = [identifier]
        else:
            raise ValueError('unknown registered ID')
        result['requested_id'] = identifier
        result['layer'] = layer
        result['versions'] = copy.deepcopy(self.manifest['versions'])
        result['segments'] = [copy.deepcopy(self.spans[i]) for i in ids]
        result['text'] = '\n'.join(s['text'] for s in result['segments'])
        result['join_semantics'] = 'separate_registered_spans_not_continuous_quote_or_shared_attribution'
        result['runtime_relevance'] = None
        result['runtime_relevance_contract'] = {
            'fields': ['query_id', 'score', 'rank', 'relevance_grade', 'query_reason', 'query_limits'],
            'origin': 'runtime_only_not_static_case_fact',
            'score_interpretation': 'ranking_score_not_violation_probability'}
        return result
