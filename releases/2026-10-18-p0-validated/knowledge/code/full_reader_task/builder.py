"""Streaming, offline SQLite package builder and exhaustive mechanical checks."""
import argparse
import json
import shutil
import sqlite3
import time
from pathlib import Path

from .legacy_base_reader import KnowledgeReader
from .primitives import canonical_sha,read,rows,save,sha
from .reader import FullKnowledgeReader,IndexedData,KINDS,VERSION_KEYS,insert,validate_records

INPUT_KINDS={'structured':('units','unit_id'),'raw':('units','unit_id'),
             'documents':('documents','official_file_id'),'candidates':('candidates','file_id'),
             'rebinds':('rebinds','unit_id'),'articles':('articles','article_id'),
             'legal_sources':('legal_sources','source_id'),'scope_units':('scope_units','unit_id'),
             'scope_sources':('scope_sources','source_id'),'scope_spans':('scope_spans','span_id')}


def _manifest(target,versions,provenance,counts):
    # Keep the complete consumer implementation within the fingerprinted package.
    package=Path(__file__).resolve().parent
    code=target/'full_reader_task';code.mkdir(exist_ok=True)
    for name in ('__init__.py','reader.py','builder.py','primitives.py','legacy_base_reader.py'):
        origin=package/name;destination=code/name
        if origin.resolve()!=destination.resolve():shutil.copyfile(origin,destination)
    entry=package.parent/'full_reader.py'
    if entry.resolve()!=(target/'full_reader.py').resolve():shutil.copyfile(entry,target/'full_reader.py')
    files={p.relative_to(target).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))
           for p in sorted(target.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    value=dict(schema='finrisk-full-reader-v1',versions=versions,files=files,source_inputs=provenance,counts=counts,
               storage='SQLite compressed original JSON records; indexed by stable IDs',
               limitations=['mechanical_identity_and_literal_ranges_only','candidate_roles_and_uncertainty_preserved','no_current_business_fact_or_semantic_approval'])
    manifest=target/'manifest.json'
    if manifest.exists():manifest.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    else:save(manifest,value)
    return dict(manifest_sha256=sha(manifest),versions=versions,bundle=target.name)


def build_index(target,*,input_files,versions,expected_counts=None,source_labels=None,extra_provenance=None):
    """Build a new target from explicit JSONL inputs; refuse every duplicate ID."""
    target=Path(target).resolve()
    if target.exists():raise ValueError('new isolated target required')
    if not versions or set(versions)!=VERSION_KEYS:raise ValueError('missing or incompatible versions')
    if set(input_files)!=set(INPUT_KINDS):raise ValueError('all input record categories must be explicit')
    paths={k:Path(v).resolve() for k,v in input_files.items()}
    provenance={k:dict(path=(source_labels or {}).get(k,k+'/'+p.name),sha256=sha(p),bytes=p.stat().st_size) for k,p in paths.items()}
    provenance.update(extra_provenance or {})
    target.mkdir(parents=True,exist_ok=False);started=time.perf_counter()
    connection=sqlite3.connect(target/'knowledge.sqlite')
    try:
        connection.execute('PRAGMA journal_mode=DELETE');connection.execute('PRAGMA synchronous=FULL')
        connection.execute('PRAGMA cache_size=-4096');connection.execute('PRAGMA temp_store=MEMORY')
        connection.executescript('CREATE TABLE records(kind TEXT NOT NULL,id TEXT NOT NULL,body BLOB NOT NULL,PRIMARY KEY(kind,id)) WITHOUT ROWID; CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL) WITHOUT ROWID;')
        scanned={}
        for name in ('documents','candidates','rebinds','articles','legal_sources','scope_sources','scope_spans','scope_units','structured','raw'):
            kind,key=INPUT_KINDS[name];scanned[name]=0
            for row in rows(paths[name]):
                identifier=row[key]
                if not isinstance(identifier,str) or not identifier:raise ValueError('invalid stable ID')
                insert(connection,kind,identifier,row);scanned[name]+=1
                if name=='documents':
                    insert(connection,'sources',identifier,dict(file_id=identifier,full_text=row['full_text'],source_sha256=row['source_sha256'],text_sha256=row['text_sha256']))
        if expected_counts:
            for kind,count in expected_counts.items():
                if scanned.get(kind)!=count:raise ValueError('full corpus inventory changed: '+kind)
        for name,p in paths.items():
            if sha(p)!=provenance[name]['sha256']:raise ValueError('input changed during build: '+name)
        store=IndexedData(connection,versions)
        validation=validate_records(store,register=True)
        counts={kind:len(getattr(store,kind)) for kind in KINDS}
        connection.execute('INSERT INTO metadata VALUES (?,?)',('schema','finrisk-full-reader-v1'))
        connection.execute('INSERT INTO metadata VALUES (?,?)',('versions',json.dumps(versions,ensure_ascii=False,sort_keys=True)))
        connection.commit()
        report=dict(passed=True,scanned=scanned,counts=counts,validation=validation,
                    build_seconds=time.perf_counter()-started,cache=store.cache_info(),sqlite_cache_bytes=4*1024*1024,
                    original_records_preserved=True,API_calls=0,semantic_review=False)
    except Exception:
        connection.rollback();raise
    finally:connection.close()
    save(target/'build_report.json',report)
    lock=_manifest(target,versions,provenance,counts)
    # Public construction and mechanical readback run once in verify_full_reader.
    return lock


def verify_full_reader(target,lock,*,legacy_readings=None,legacy_bundle=None,legacy_lock=None,progress=None):
    target=Path(target);started=time.perf_counter();reads=0;spans=0;supplements=0
    with FullKnowledgeReader(target,expected_manifest_sha256=lock['manifest_sha256'],expected_versions=lock['versions'],progress=progress) as reader:
        startup=reader.startup_seconds;read_start=time.perf_counter()
        if progress:progress(dict(stage='public_constructor_complete',startup_seconds=startup))
        sample=[];stride=max(1,len(reader.units)//256)
        for ordinal,uid in enumerate(reader.units,1):
            if len(sample)<256 and (ordinal-1)%stride==0:sample.append(uid)
            layers=['hit','extended']
            if reader.scope and uid in reader.scope.units:layers.append('supplement');supplements+=1
            for layer in layers:
                result=reader.read(uid,layer=layer)
                if result['unit_id']!=uid or result['human_approved'] is not False or result['runtime_relevance'] is not None:raise ValueError('read contract mismatch')
                for segment in result['segments']:
                    if reader.read_span(segment['span_id'])!=segment:raise ValueError('mechanical span readback mismatch')
                    spans+=1
                reads+=1
            if progress and ordinal%10000==0:progress(dict(stage='full_readback',completed_units=ordinal,total_units=len(reader.units),read_calls=reads,segment_readbacks=spans))
        read_seconds=time.perf_counter()-read_start
        if progress:progress(dict(stage='full_readback_complete',units=len(reader.units),seconds=read_seconds,read_calls=reads,segment_readbacks=spans))
        legacy_count=0;unique=set()
        if legacy_readings:
            oracle=KnowledgeReader(legacy_bundle,expected_manifest_sha256=legacy_lock['manifest_sha256'],expected_versions=legacy_lock['versions'])
            with (target/'legacy_comparison.jsonl').open('x',encoding='utf-8') as report:
                for old in rows(legacy_readings):
                    uid=old['unit_id'];actual=reader.read(uid);expected=oracle.read(uid)
                    digest=canonical_sha(actual)
                    if actual!=expected or digest!=old['expected_read_sha256']:raise ValueError('legacy position read mismatch: '+uid)
                    report.write(json.dumps(dict(query_id=old['query_id'],arm=old['arm'],rank=old['rank'],unit_id=uid,expected_read_sha256=old['expected_read_sha256'],actual_read_sha256=digest,all_fields_equal=True),ensure_ascii=False)+'\n')
                    legacy_count+=1;unique.add(uid)
            if legacy_count!=960:raise ValueError('legacy position count changed')
        if progress:progress(dict(stage='legacy_complete',positions=legacy_count))
        timings=[];batch_started=time.perf_counter()
        for _ in range(2):
            for uid in sample:
                for layer in ('hit','extended'):
                    read_started=time.perf_counter();reader.read(uid,layer=layer)
                    timings.append((time.perf_counter()-read_started)*1000)
        timings.sort()
        benchmark=dict(read_calls=len(timings),sample_units=len(sample),batch_seconds=time.perf_counter()-batch_started,
                       mean_read_ms=sum(timings)/len(timings) if timings else 0,
                       p50_read_ms=timings[len(timings)//2] if timings else 0,
                       p95_read_ms=timings[min(len(timings)-1,int(len(timings)*.95))] if timings else 0,
                       max_read_ms=max(timings) if timings else 0,whole_process_RSS_measured=False)
        info=reader.cache_info()
        report=dict(passed=True,total_units=len(reader.units),total_documents=len(reader.sources),total_candidates=len(reader.candidates),
                    read_calls=reads,segment_readbacks=spans,reviewed_supplement_units=supplements,legacy_positions=legacy_count,
                    legacy_distinct_units=len(unique),legacy_full_values_equal=True if legacy_count else None,
                    startup_seconds=startup,mechanical_read_seconds=read_seconds,
                    mean_read_milliseconds=read_seconds*1000/reads if reads else 0,verification_seconds=time.perf_counter()-started,
                    cache=info,sqlite_cache_bytes=4*1024*1024,all_runtime_records_lazy=True,no_writable_sidecars=True,
                    persistent_read_benchmark=benchmark,
                    lifecycle='每进程持久保留已验证实例；禁止每次工具调用重建。',
                    API_calls=0,semantic_review=False,limitation='机械身份、字面区间、旧返回值一致性；不代表全库语义审查或当前业务事实核准。')
    save(target/'verification_report.json',report)
    manifest=read(target/'manifest.json')
    return _manifest(target,lock['versions'],manifest['source_inputs'],manifest['counts'])


def build_full_reader(target,*,source_root,progress=None):
    source_root=Path(source_root).resolve()
    v2=source_root/'outputs/FinRisk_知识库V2_20261012';sealed=source_root/'outputs/FinRisk_知识组织增强_交付_20261018_v2'
    final=sealed/'case_reader/final';scope=final/'scope';old_lock=read(sealed/'case_reader/final_lock.json')
    # Verify the exact reviewed source snapshot and the scope handoff before copying rows.
    KnowledgeReader(final,expected_manifest_sha256=old_lock['manifest_sha256'],expected_versions=old_lock['versions'])
    paths=dict(structured=v2/'indexes/all9639_final/structured.jsonl',raw=v2/'indexes/all9639_final/raw.jsonl',
               documents=v2/'normalized_final/data/documents.jsonl',candidates=source_root/'outputs/FinRisk_知识库V2.1轻量收尾_20261015/effective_candidates.jsonl.gz',
               rebinds=source_root/'outputs/FinRisk_知识库增量改进_20261018/handoff_scope/projection_candidate_rebinds.jsonl',
               articles=final/'articles.jsonl',legal_sources=final/'legal_sources.jsonl',scope_units=scope/'scope_overlays.jsonl',
               scope_sources=scope/'sources.jsonl',scope_spans=scope/'spans.jsonl')
    extra={}
    for key,p in [('reviewed_scope_manifest',scope/'handoff_manifest.json'),('reviewed_legacy_manifest',final/'manifest.json'),('reviewed_versions',sealed/'case_reader/final_lock.json'),('legacy_positions',sealed/'regression/legacy_readings.jsonl')]:
        extra[key]=dict(path=p.relative_to(source_root).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
    lock=build_index(target,input_files=paths,versions=old_lock['versions'],
                     expected_counts=dict(structured=65475,raw=45403,documents=9639,candidates=9639,rebinds=33),
                     source_labels={k:p.relative_to(source_root).as_posix() for k,p in paths.items()},extra_provenance=extra)
    return verify_full_reader(target,lock,legacy_readings=sealed/'regression/legacy_readings.jsonl',legacy_bundle=final,legacy_lock=old_lock,progress=progress)


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    build=sub.add_parser('build');build.add_argument('--source-root',required=True);build.add_argument('--target',required=True)
    verify=sub.add_parser('verify');verify.add_argument('--source-root',required=True);verify.add_argument('--target',required=True);verify.add_argument('--expected-manifest-sha256',required=True)
    args=parser.parse_args()
    def progress(event):print(json.dumps(event,ensure_ascii=False),flush=True)
    if args.command=='build':lock=build_full_reader(args.target,source_root=args.source_root,progress=progress)
    else:
        target=Path(args.target).resolve();manifest=read(target/'manifest.json');root=Path(args.source_root).resolve()
        sealed=root/'outputs/FinRisk_知识组织增强_交付_20261018_v2'
        lock=verify_full_reader(target,dict(manifest_sha256=args.expected_manifest_sha256,versions=manifest['versions']),
                               legacy_readings=sealed/'regression/legacy_readings.jsonl',legacy_bundle=sealed/'case_reader/final',
                               legacy_lock=read(sealed/'case_reader/final_lock.json'),progress=progress)
    print(json.dumps(lock,ensure_ascii=False,indent=2))
