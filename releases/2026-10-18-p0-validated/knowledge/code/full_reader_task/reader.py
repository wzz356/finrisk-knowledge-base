"""Validated SQLite mappings with bounded shared decoded-byte cache."""
import copy
import json
import sqlite3
import time
import zlib
from collections import OrderedDict
from collections.abc import Mapping
from pathlib import Path

from .legacy_base_reader import KnowledgeReader
from .primitives import canonical_sha,read,sha,textsha

VERSION_KEYS={'content','projection','articles','rules','scope'}
KINDS=('units','sources','documents','candidates','rebinds','articles','legal_sources','scope_units','scope_sources','scope_spans','spans')


class ByteCache:
    def __init__(self,max_entries=64,max_bytes=8*1024*1024):
        self.max_entries=max_entries;self.max_bytes=max_bytes;self.data=OrderedDict();self.bytes=0
        self.peak_entries=0;self.peak_bytes=0

    def get(self,key):
        if key not in self.data:return None
        self.data.move_to_end(key);return self.data[key]

    def put(self,key,value):
        if len(value)>self.max_bytes:return
        if key in self.data:self.bytes-=len(self.data.pop(key))
        while self.data and (len(self.data)>=self.max_entries or self.bytes+len(value)>self.max_bytes):
            self.bytes-=len(self.data.popitem(last=False)[1])
        self.data[key]=value;self.bytes+=len(value)
        self.peak_entries=max(self.peak_entries,len(self.data));self.peak_bytes=max(self.peak_bytes,self.bytes)

    def info(self):
        return dict(entries=len(self.data),bytes=self.bytes,max_entries=self.max_entries,max_bytes=self.max_bytes,
                    peak_entries=self.peak_entries,peak_bytes=self.peak_bytes,representation='utf8_json_bytes; decoded objects returned fresh')


class SQLiteMapping(Mapping):
    def __init__(self,connection,kind,cache):self.connection=connection;self.kind=kind;self.cache=cache
    def __len__(self):return self.connection.execute('SELECT count(*) FROM records WHERE kind=?',(self.kind,)).fetchone()[0]
    def __iter__(self):
        cursor=self.connection.execute('SELECT id FROM records WHERE kind=? ORDER BY id',(self.kind,))
        for row in cursor:yield row[0]
    def __contains__(self,key):return self.connection.execute('SELECT 1 FROM records WHERE kind=? AND id=?',(self.kind,key)).fetchone() is not None
    def __getitem__(self,key):
        raw=self.cache.get((self.kind,key))
        if raw is None:
            row=self.connection.execute('SELECT body FROM records WHERE kind=? AND id=?',(self.kind,key)).fetchone()
            if row is None:raise KeyError(key)
            raw=zlib.decompress(row[0]);self.cache.put((self.kind,key),raw)
        return json.loads(raw)


class IndexedScope:
    def __init__(self,owner):
        self.units=owner.scope_units;self.sources=owner.scope_sources;self.spans=owner.scope_spans
    def read(self,uid,*,layer='hit'):
        return dict(segments=[self.spans[sid] for sid in self.units[uid]['layers'].get(layer,[])])


class IndexedData(KnowledgeReader):
    """A real initialized storage object used by both builder and consumer."""
    def __init__(self,connection,versions):
        if not versions or set(versions)!=VERSION_KEYS:raise ValueError('missing or incompatible versions')
        self.connection=connection;self.versions=copy.deepcopy(versions);self.cache=ByteCache()
        for kind in KINDS:setattr(self,kind,SQLiteMapping(connection,kind,self.cache))
        self.scope=IndexedScope(self) if len(self.scope_units) else None

    def cache_info(self):return self.cache.info()
    def close(self):
        self.connection.close();self.cache.data.clear();self.cache.bytes=0
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


def insert(connection,kind,key,value,*,identical_ok=False):
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    try:connection.execute('INSERT INTO records VALUES (?,?,?)',(kind,key,zlib.compress(raw)))
    except sqlite3.IntegrityError as exc:
        if identical_ok:
            old=connection.execute('SELECT body FROM records WHERE kind=? AND id=?',(kind,key)).fetchone()
            if old and zlib.decompress(old[0])==raw:return
        raise ValueError('duplicate or conflicting ID: '+kind+':'+key) from exc


def validate_records(reader,*,register=False,progress=None):
    """Stream every original record; no corpus-sized dict/set or decoded cache."""
    c=reader.connection;counts=dict(literal_ranges=0,unit_layers=0,reviewed_rebinds=0)
    regular_span_count=0;registered_scope_spans=set()
    for source in reader.sources.values():
        if textsha(source['full_text'])!=source['text_sha256']:raise ValueError('source text fingerprint mismatch')
    if progress:progress(dict(stage='sources_validated',count=len(reader.sources)))
    if len(reader.documents)!=len(reader.sources):raise ValueError('document/source count mismatch')
    for fid,candidate in reader.candidates.items():
        if candidate['draft']['file_id']!=fid or canonical_sha(candidate['draft'])!=candidate['effective_draft_json_sha256']:
            raise ValueError('current draft fingerprint mismatch')
    if progress:progress(dict(stage='candidates_validated',count=len(reader.candidates)))
    for source in reader.scope_sources.values():
        if textsha(source['text'])!=source['source_sha256']:raise ValueError('scope source text fingerprint mismatch')
    for span in reader.scope_spans.values():
        source=reader.scope_sources.get(span['source_id']);a,b=span['start'],span['end']
        if (not source or type(a) is not int or type(b) is not int or not 0<=a<b<=len(source['text']) or
            source['text'][a:b]!=span['text'] or textsha(span['text'])!=span['text_sha256'] or
            span.get('source_sha256',source['source_sha256'])!=source['source_sha256']):raise ValueError('scope span source mismatch')
    for uid,sunit in reader.scope_units.items():
        if uid in reader.scope_spans:raise ValueError('duplicate scope unit/span namespace')
        if uid not in reader.units and (uid not in reader.articles or sunit.get('article_id')!=uid):
            raise ValueError('scope references unregistered unit/article')
        source=reader.scope_sources.get(sunit['source_id'])
        if not source or source['source_sha256']!=sunit['source_sha256']:raise ValueError('scope unit source mismatch')
        for layer,ids in sunit['layers'].items():
            if layer not in ('hit','supplement','extended'):raise ValueError('scope unknown layer')
            for sid in ids:
                span=reader.scope_spans.get(sid)
                if not span or span['source_id']!=sunit['source_id'] or span['layer']!=layer:raise ValueError('scope span not registered for unit/layer')
    # Orphan check uses indexed references rather than a corpus-sized set.
    referenced_scope=set()
    for u in reader.scope_units.values():
        for ids in u['layers'].values():referenced_scope.update(ids)
    if len(referenced_scope)!=len(reader.scope_spans):raise ValueError('scope orphan span')
    for ordinal,unit in enumerate(reader.units.values(),1):
        uid=unit['unit_id'];source=reader.sources.get(unit['file_id']);candidate=reader.candidates.get(unit['file_id'])
        if not source or not candidate or unit['source_sha256']!=source['source_sha256']:raise ValueError('source/current draft identity mismatch')
        old=unit['candidate_sha256'];current=candidate['effective_draft_json_sha256'];patch=reader.rebinds.get(uid)
        if patch:
            if (patch['file_id']!=unit['file_id'] or patch['expected_baseline_draft_sha256']!=old or
                patch['current_effective_draft_sha256']!=current or patch['requires_versions']!=reader.versions or
                patch['allowed_changed_fields']!=['candidate_sha256'] or patch['ranking_text_changed'] is not False or
                patch['preserve_stable_case_behavior_IDs'] is not True):raise ValueError('invalid metadata-only rebind')
            counts['reviewed_rebinds']+=1
        elif old!=current:raise ValueError('stale candidate binding without reviewed patch')
        for key in ('source_spans','parent_source_spans','context_spans','prefix_source_spans'):
            for span in unit.get(key) or []:reader._literal(source,span);counts['literal_ranges']+=1
        for association in unit.get('associations') or []:
            for qkey,skey in (('party_quote','party_source_spans'),('quote','quote_source_spans')):
                spans=association.get(skey) or [];texts=[reader._literal(source,s) for s in spans];counts['literal_ranges']+=len(spans)
                if association.get(qkey) and spans and association[qkey] not in texts:raise ValueError('association quotation mismatch')
        for layer in ('hit','extended','supplement'):
            if layer=='supplement' and (not reader.scope or uid not in reader.scope.units):continue
            for segment in reader._segments(uid,layer):
                if register:insert(c,'spans',segment['span_id'],segment,identical_ok=True)
                elif reader.spans.get(segment['span_id'])!=segment:raise ValueError('registered span mismatch')
                if segment['span_id'] in reader.scope_spans:registered_scope_spans.add(segment['span_id'])
                else:regular_span_count+=1
            counts['unit_layers']+=1
        if progress and ordinal%10000==0:progress(dict(stage='units_validating',completed=ordinal,total=len(reader.units)))
    for uid in reader.rebinds:
        if uid not in reader.units:raise ValueError('rebind references unregistered unit')
    # Each ordinary ID encodes (unique unit ID, layer, index); only reviewed scope
    # IDs may be shared. Every expected value was compared above, so count equality
    # also rules out extra/orphan IDs without re-reading the complete span corpus.
    if len(reader.spans)!=regular_span_count+len(registered_scope_spans):raise ValueError('orphan or invalid registered span')
    for article in reader.articles.values():
        source=reader.legal_sources.get(article['source_id']);a,b=article['start'],article['end']
        if (not source or type(a) is not int or type(b) is not int or not 0<=a<b<=len(source['text'])):raise ValueError('invalid legal article source range')
        if (textsha(source['text'])!=article['original_source_text_sha256'] or source['text'][a:b]!=article['text'] or
            textsha(article['text'])!=article['text_sha256']):raise ValueError('legal article source mismatch')
    if progress:progress(dict(stage='records_validated',units=len(reader.units),**counts))
    return counts


class FullKnowledgeReader(IndexedData):
    def __init__(self,root,expected_manifest_sha256=None,expected_versions=None,*,progress=None):
        start=time.perf_counter();self.root=Path(root).resolve();mp=self.root/'manifest.json'
        if not expected_manifest_sha256 or sha(mp)!=expected_manifest_sha256:raise ValueError('missing or incompatible manifest fingerprint')
        self.manifest=read(mp)
        if self.manifest.get('schema')!='finrisk-full-reader-v1':raise ValueError('unsupported schema')
        if not expected_versions or set(expected_versions)!=VERSION_KEYS or self.manifest['versions']!=expected_versions:raise ValueError('missing or incompatible versions')
        if 'knowledge.sqlite' not in self.manifest.get('files',{}):raise ValueError('required database not registered')
        for name,meta in self.manifest['files'].items():
            path=(self.root/name).resolve()
            if not path.is_relative_to(self.root) or path.stat().st_size!=meta['bytes'] or sha(path)!=meta['sha256']:raise ValueError('payload fingerprint mismatch: '+name)
        if progress:progress(dict(stage='payload_fingerprints_valid',elapsed_seconds=time.perf_counter()-start))
        db=self.root/'knowledge.sqlite'
        connection=sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1',uri=True)
        try:
            connection.execute('PRAGMA query_only=ON');connection.execute('PRAGMA cache_size=-4096');connection.execute('PRAGMA temp_store=MEMORY')
            if connection.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('database integrity check failed')
            meta=dict(connection.execute('SELECT key,value FROM metadata'))
            if json.loads(meta['versions'])!=expected_versions or meta['schema']!='finrisk-full-reader-v1':raise ValueError('database version mismatch')
            super().__init__(connection,expected_versions)
            for kind in KINDS:
                if len(getattr(self,kind))!=self.manifest['counts'][kind]:raise ValueError('database record count mismatch: '+kind)
            self.validation=validate_records(self,progress=progress)
        except Exception:
            connection.close();raise
        self.startup_seconds=time.perf_counter()-start
