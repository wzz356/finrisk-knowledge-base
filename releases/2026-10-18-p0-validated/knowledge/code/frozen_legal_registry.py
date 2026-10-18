"""Portable, hash-pinned research registry; no historical applicability inference."""
import copy
import json
import re
from collections import deque
from datetime import date
from pathlib import Path, PurePosixPath

from runtime_common import rows, sha, textsha


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def checked_slice(text, start, end):
    _require(isinstance(text, str) and type(start) is int and type(end) is int,
             'text and integer character coordinates required')
    _require(0 <= start < end <= len(text), 'invalid or empty slice interval')
    return text[start:end]


def dependency_closure(roots, adjacency, registered, limit=32):
    _require(isinstance(roots, (list, tuple)) and bool(roots), 'nonempty roots required')
    _require(all(isinstance(x, str) and x for x in roots) and len(set(roots)) == len(roots),
             'root IDs must be unique strings')
    _require(type(limit) is int and 1 <= limit <= 32, 'limit must be an integer in 1..32')
    pending, visited, resolved, missing = deque(roots), set(), [], []
    while pending and len(visited) < limit:
        current = pending.popleft()
        if current in visited:
            continue
        visited.add(current)
        if current not in registered:
            missing.append(current)
            continue
        resolved.append(current)
        targets = adjacency.get(current, [])
        _require(isinstance(targets, (list, tuple)) and all(isinstance(t, str) and t for t in targets),
                 'adjacency must contain lists of article IDs')
        pending.extend(t for t in targets if t not in visited)
    unread = list(dict.fromkeys(t for t in pending if t not in visited))
    hit = len(visited) >= limit
    return {'resolved': resolved, 'missing': missing, 'unread': unread,
            'status': 'partial' if missing or unread or hit else 'complete', 'limit_reached': hit}


def _normalized(text):
    return ''.join(re.sub(r'^L\d+:\s?', '', text, flags=re.MULTILINE).split())


class LegalRegistry:
    def __init__(self, root, expected_manifest_sha256):
        self.root = Path(root).resolve()
        manifest_path = self.root / 'manifest.json'
        _require(isinstance(expected_manifest_sha256, str) and re.fullmatch('[0-9a-f]{64}', expected_manifest_sha256),
                 'a pinned manifest SHA256 is required')
        _require(sha(manifest_path) == expected_manifest_sha256, 'manifest SHA256 mismatch')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        self.files = {}
        for item in manifest['files']:
            name = item['path']
            path = self._path(name)
            _require(name != 'manifest.json' and name not in self.files, 'duplicate or recursive payload')
            _require(path.is_file() and sha(path) == item['sha256'] and path.stat().st_size == item['bytes'],
                     'payload SHA256 or size mismatch: ' + name)
            self.files[name] = item
        disk = {p.relative_to(self.root).as_posix() for p in self.root.rglob('*') if p.is_file()}
        _require(disk == set(self.files) | {'manifest.json'}, 'manifest must cover every payload')
        _require({'articles.jsonl', 'source_registry.jsonl', 'dependencies.jsonl', 'verification.json'} <= set(self.files),
                 'required registry payload missing')
        self.sources = self._index('source_registry.jsonl', 'source_id')
        self.articles = self._index('articles.jsonl', 'article_id')
        self.verification = json.loads(self._path('verification.json').read_text(encoding='utf-8-sig'))
        for article in self.articles.values():
            source = self.sources.get(article['source_id'])
            _require(source is not None and source['research_reference_allowed'] is True,
                     'unknown or quarantined article source')
            _require(article['version_id'] == source['version_id'], 'cross-version article')
            _require(article['production_active'] is False and article['human_approved'] is False
                     and article['review_origin'] == 'current_session_model', 'research provenance required')
            _require(textsha(article['text']) == article['text_sha256'], 'article text hash mismatch')
            self._verify_span(article)
        self.edges, self.adjacency, seen = list(rows(self._path('dependencies.jsonl'))), {}, set()
        for edge in self.edges:
            origin, target = edge['from_article_id'], edge['to_article_id']
            kind = edge['relationship_type']
            key = (origin, target, kind)
            _require(origin in self.articles and key not in seen, 'unknown origin or duplicate dependency')
            _require(kind in {'official_cross_reference', 'assistant_required_context'}, 'unknown dependency kind')
            _require(edge['from_version_id'] == self.articles[origin]['version_id'], 'cross-version dependency origin')
            if target in self.articles:
                _require(edge['to_version_id'] == self.articles[target]['version_id'], 'cross-version dependency target')
            _require(edge['evidence']['snapshot_file'] in self.files, 'unmanifested dependency evidence')
            if kind == 'official_cross_reference':
                quote = edge['evidence'].get('text')
                _require(bool(quote) and quote in self.articles[origin]['text'], 'official cross-reference lacks literal proof')
            seen.add(key)
            self.adjacency.setdefault(origin, []).append(target)

    def _path(self, name):
        _require(isinstance(name, str) and name and '\\' not in name and ':' not in name,
                 'portable relative path required')
        parts = PurePosixPath(name)
        _require(not parts.is_absolute() and '..' not in parts.parts, 'payload path escapes registry')
        path = (self.root / name).resolve()
        _require(path.is_relative_to(self.root), 'payload path escapes registry')
        return path

    def _index(self, filename, key):
        result = {}
        for item in rows(self._path(filename)):
            identity = item[key]
            _require(isinstance(identity, str) and identity and identity not in result, 'duplicate or invalid ' + key)
            result[identity] = item
        return result

    def _verify_span(self, article):
        provenance = article['provenance']
        name, span = provenance['snapshot_file'], provenance['span']
        _require(name in self.files, 'unmanifested article snapshot')
        raw = self._path(name).read_bytes()
        text = raw.decode('utf-8')
        start, end = span['start_char'], span['end_char']
        sliced = checked_slice(text, start, end)
        _require(type(span['start_byte_utf8']) is int and type(span['end_byte_utf8']) is int,
                 'UTF8 coordinates must be integers')
        _require(span['start_byte_utf8'] == len(text[:start].encode('utf-8'))
                 and span['end_byte_utf8'] == len(text[:end].encode('utf-8'))
                 and textsha(sliced) == span['span_sha256'], 'UTF8 span or span hash mismatch')
        mode, transform = provenance['coordinate_system'], provenance['transform']
        if mode == 'legacy_literal_char':
            _require(transform == 'none' and sliced == article['text'], 'legacy literal slice mismatch')
        else:
            _require(mode == 'reader_snapshot_char_and_utf8'
                     and transform == 'remove_line_labels_and_unicode_whitespace'
                     and _normalized(sliced) == _normalized(article['text']), 'reader span transformation mismatch')

    def dependency_closure(self, article_ids, limit=32):
        return dependency_closure(article_ids, self.adjacency, self.articles, limit)

    def read_article(self, article_id, include_dependencies=True, as_of=None):
        _require(isinstance(article_id, str) and article_id in self.articles, 'unknown or quarantined article ID')
        _require(type(include_dependencies) is bool, 'include_dependencies must be boolean')
        if as_of is not None:
            _require(isinstance(as_of, str), 'as_of must be an ISO date or None')
            date.fromisoformat(as_of)
        article = self.articles[article_id]
        coverage = self.dependency_closure([article_id]) if include_dependencies else {
            'resolved': [article_id], 'missing': [], 'unread': self.adjacency.get(article_id, []),
            'status': 'partial' if self.adjacency.get(article_id) else 'complete', 'limit_reached': False}
        coverage.update(as_of=as_of, current_business_fact_proof=False,
                        historical_case_applicability_confirmed=False, raw_original_files=0,
                        historical_review='not_automatically_verified',
                        snapshot_representation='saved_reader_text_not_original_HTTP_bytes')
        dependencies = [self.articles[x] for x in coverage['resolved'] if x != article_id]
        sources = {a['source_id']: self.sources[a['source_id']] for a in [article] + dependencies}
        return copy.deepcopy({'article': article, 'dependencies': dependencies, 'coverage': coverage,
                              'sources': sources})
