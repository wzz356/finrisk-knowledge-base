"""V2 preparation and a provenance-bound adapter around the frozen V1 GPU runner."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import sys
import time
from collections import Counter
from functools import lru_cache
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BACKEND=ROOT/'work/finrisk_retrieval_20261012/runner.py'
BACKEND_SHA='7a05001beb6e611e47743ec420f70763f61fd106932b02d54f73e24d772da4cb'
ADAPTER_SHA=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
TOKENIZER_SHA='5c53e4fe5ebb47657bb6e191b56074889b571b6a85941da516a314d657518465'


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def sha_json(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_rows(path):
    with Path(path).open(encoding='utf-8-sig') as f:
        return [json.loads(line) for line in f if line.strip()]


def save_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(json.dumps(value,ensure_ascii=False,indent=2).encode('utf-8')+b'\n')


def facts(draft):
    d=copy.deepcopy(draft)
    for k in ['label_policy_version','semantic_status','human_review_status']:d.pop(k,None)
    for b in d.get('behaviors',[]):
        b.pop('risk_tags',None);b.pop('zero_tag_reason',None)
    return d


def apply_overlays(candidates,sources,rows):
    effective={}
    for row in rows:
        fid=row['file_id']
        if fid in effective or fid not in candidates or fid not in sources:
            raise ValueError('duplicate or unknown overlay file_id: '+fid)
        base=candidates[fid]['draft'];source=sources[fid]
        if row['base_draft_json_sha256']!=sha_json(base) or row['base_text_sha256']!=source['text_sha256']:
            raise ValueError('stale overlay binding: '+fid)
        d=row['updated_draft']
        if d.get('file_id')!=fid or d.get('semantic_status')!='candidate' or d.get('human_review_status')!='pending':
            raise ValueError('overlay may not fake approval or alter identity: '+fid)
        kind=row.get('overlay_kind','label_migration')
        if kind=='label_migration' and facts(base)!=facts(d):
            raise ValueError('label migration changed facts: '+fid)
        if kind not in ['label_migration','content_repair']:
            raise ValueError('unknown overlay kind: '+kind)
        if kind=='content_repair' and not row.get('confirmed_findings'):
            raise ValueError('content repair lacks confirmed source-grounded findings: '+fid)
        for b in d.get('behaviors',[]):
            for tag in b.get('risk_tags',[]):
                if any(q not in source['full_text'] for q in tag.get('quotes',[])):
                    raise ValueError('overlay tag evidence is not exact original text: '+fid)
        effective[fid]=copy.deepcopy(d)
    return effective


def evidence_row(unit,score):
    row={k:unit.get(k) for k in ['file_id','unit_id','behavior_id','case_ids','behavior_ids','associations','qualifier_source_links']}
    row.update(text=unit.get('context_text',unit['text']),prefix='',
               source_text=unit.get('context_source_text',unit['source_text']),
               source_spans=unit.get('context_spans',unit['source_spans']),
               source_segments=unit.get('context_segments',[]),
               indexed_text=unit['text'],indexed_source_text=unit['source_text'],
               indexed_source_spans=unit['source_spans'],score=float(score),
               evidence_ambiguous=unit.get('evidence_ambiguous',False),
               prefix_evidence_ambiguous=unit.get('prefix_evidence_ambiguous',False),
               ambiguity_reason=unit.get('ambiguity_reason'),
               context_long=unit.get('context_long',False),context_ambiguous=unit.get('context_ambiguous',False),
               semantic_status='candidate',human_review_status='pending',event_id=unit.get('event_id'))
    return row


def aggregate(ranked,unit_map,top_k=20):
    case_map={};file_map={};seen=set()
    for hit in ranked:
        uid=hit['unit_id']
        if uid in seen:continue
        seen.add(uid);u=unit_map[uid];score=float(hit['score']);fid=u['file_id']
        cids=[c for c in u.get('case_ids',[u['case_id']]) if c!=fid+':SOURCE']
        for cid in cids:
            if cid not in case_map or score>case_map[cid]['score']:
                case_map[cid]={**evidence_row(u,score),'case_id':cid}
        existing=file_map.get(fid)
        all_cases=set(existing['case_ids'] if existing else [])|set(cids)
        if existing is None or score>existing['score']:
            file_map[fid]={**evidence_row(u,score),'case_ids':sorted(all_cases)}
        else:existing['case_ids']=sorted(all_cases)
    def rank(rows,key):
        return [{**r,'rank':i} for i,r in enumerate(sorted(rows,key=lambda x:(-x['score'],x[key]))[:top_k],1)]
    return rank(case_map.values(),'case_id'),rank(file_map.values(),'file_id')


def diversify_events(files,event_map):
    first=[];later=[];seen=set()
    for row in files:
        eid=event_map.get(row['file_id'],'unlinked:'+row['file_id'])
        (later if eid in seen else first).append(dict(row,event_id=eid))
        seen.add(eid)
    return [dict(r,rank=i) for i,r in enumerate(first+later,1)]


def backend():
    if sha_file(BACKEND)!=BACKEND_SHA:raise ValueError('frozen V1 backend SHA changed')
    spec=importlib.util.spec_from_file_location('finrisk_v1_gpu_backend',BACKEND)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def frozen_tokenizer():
    path=backend().DEFAULT_SRC/'retrieval/tokenization.py'
    if sha_file(path)!=TOKENIZER_SHA:raise ValueError('frozen baseline tokenizer changed')
    spec=importlib.util.spec_from_file_location('finrisk_frozen_tokenizer',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.chinese_unigram_bigram


def partition_searchable_units(units):
    tokenize=frozen_tokenizer();accepted=[];excluded=[]
    for unit in units:
        (accepted if tokenize(unit['text']) else excluded).append(unit)
    return accepted,excluded


def normalized_identity(fid,kind,key,source,version):
    descriptor={'namespace':version,'object_kind':kind,'file_id':fid,
                'source_sha256':source['source_sha256'],'text_sha256':source['text_sha256'],
                'text_version':source.get('text_version',1),'local_key':key}
    return 'FRV2-'+kind.upper()+'-'+fid+'-'+sha_json(descriptor)[:24]


def normalize_unit_links(u,case_ids,behavior_ids):
    # Projection may share immutable source-link objects across units.
    links=copy.deepcopy({'associations':u['associations'],
                         'qualifiers':u.get('qualifier_source_links',[])})
    u['associations']=links['associations'];u['qualifier_source_links']=links['qualifiers']
    u['original_case_ids']=list(u['case_ids']);u['original_behavior_ids']=list(u['behavior_ids'])
    u['case_ids']=[case_ids[x.split(':',1)[1]] for x in u['case_ids']]
    u['behavior_ids']=[behavior_ids[x.split(':',1)[1]] for x in u['behavior_ids']]
    u['case_id']=u['case_ids'][0] if u['case_ids'] else u['file_id']+':SOURCE'
    u['behavior_id']=u['behavior_ids'][0] if u['behavior_ids'] else None
    for a in u['associations']:
        a['original_case_id']=a['case_id'];a['original_behavior_id']=a['behavior_id']
        a['case_id']=case_ids[a['case_key']];a['behavior_id']=behavior_ids[a['behavior_key']]
    qualifiers=list(u['qualifier_source_links'])
    for a in u['associations']:qualifiers.extend(a.get('qualifier_source_links',[]))
    seen_links=set()
    for a in qualifiers:
        if id(a) in seen_links:continue
        seen_links.add(id(a))
        a['original_case_id']=a['case_id'];a['original_behavior_id']=a['behavior_id']
        a['case_id']=case_ids[a['case_id'].split(':',1)[1]]
        a['behavior_id']=behavior_ids[a['behavior_id'].split(':',1)[1]]


def prepare_dataset(repo,out,scope='all',overlay_rows=()):
    from normalize_v2 import load_records,VERSION
    from projection_v2 import project_document
    started=time.perf_counter();out=Path(out)
    if out.exists() and any(out.iterdir()):raise FileExistsError('prepared output must be empty: '+str(out))
    out.mkdir(parents=True,exist_ok=True)
    candidates,sources=load_records(repo)
    if set(candidates)!=set(sources) or len(candidates)!=9639:raise ValueError('source population must be exactly 9639 unique candidates')
    effective=apply_overlays(candidates,sources,list(overlay_rows));gpu=backend()
    counts=Counter();audits=Counter();bindings=[];all_events={}
    handles={c:(out/(c+'.jsonl')).open('wb') for c in ['structured','raw']}
    audit_sink=(out/'projection_audit.jsonl').open('wb')
    excluded_sink=(out/'non_searchable_units.jsonl').open('wb')
    save_json(out/'manifest.json',{'status':'preparing','scope':scope})
    try:
        for fid,wrapper in sorted(candidates.items()):
            if scope=='remaining8509' and wrapper['batch']!='remaining8509':continue
            source=sources[fid];d=effective.get(fid,wrapper['draft']);body=source['full_text']
            if sha_json(wrapper['draft'])!=wrapper['draft_json_sha256'] or hashlib.sha256(body.encode('utf-8')).hexdigest()!=source['text_sha256']:
                raise ValueError('source or candidate SHA mismatch: '+fid)
            dsha=sha_json(d)
            units,audit=project_document(fid,body,d,dsha)
            case_ids={c['local_key']:normalized_identity(fid,'case',c['local_key'],source,VERSION) for c in d.get('cases',[])}
            behavior_ids={b['local_key']:normalized_identity(fid,'behavior',b['local_key'],source,VERSION) for b in d.get('behaviors',[])}
            # Explicit, narrow same-event links; no global entity or event inference.
            eid=None
            if fid in ['F009408','F009411','F009412']:
                compact=''.join(body.split())
                if all(q in compact for q in ['2022年5月12日','新华保险昌吉中心支公司','金享盛世惠泽万家']):
                    eid='event-xinhua-changji-20220512-jinxiangshengshi'
                    all_events[fid]=eid
            for u in units:
                normalize_unit_links(u,case_ids,behavior_ids)
                u['candidate_sha256_kind']='canonical_json_content';u['event_id']=eid
                u['quality_status']='pending_human_acceptance'
                if not frozen_tokenizer()(u['text']):
                    excluded_sink.write(canonical(u)+b'\n');counts[u['corpus']+':non_searchable']+=1
                    audit.append({'file_id':fid,'unit_id':u['unit_id'],'reason':'no_BM25_tokens',
                                  'retained_in':'non_searchable_units.jsonl','source_spans':u['source_spans']})
                    continue
                handles[u['corpus']].write(canonical(u)+b'\n');counts[u['corpus']]+=1
                counts[u['corpus']+':context_long']+=bool(u.get('context_long'))
                counts[u['corpus']+':context_ambiguous']+=bool(u.get('context_ambiguous'))
            for a in audit:
                audit_sink.write(canonical(a)+b'\n');audits[a['reason']]+=1
            bindings.append({'file_id':fid,'batch':wrapper['batch'],'original_candidate_sha256':wrapper['original_candidate_sha256'],
                             'effective_draft_json_sha256':dsha,'text_sha256':source['text_sha256'],
                             'source_location':source.get('_export_location'),
                             'candidate_location':wrapper.get('_export_location')})
            if len(bindings)%500==0:
                print(json.dumps({'event':'prepare_progress','files':len(bindings),'counts':dict(counts)}),flush=True)
    finally:
        for h in handles.values():h.close()
        audit_sink.close()
        excluded_sink.close()
    expected=8509 if scope=='remaining8509' else 9639
    if len(bindings)!=expected:raise ValueError('incomplete scope')
    corpora={c:{'path':str((out/(c+'.jsonl')).resolve()),'sha256':sha_file(out/(c+'.jsonl')),
                'count':counts[c],'ordered_unit_text_sha256':gpu.ordered_text_sha(read_rows(out/(c+'.jsonl')))} for c in handles}
    save_json(out/'event_links.json',{'event_map':all_events,'scope':'only explicitly checked three same-event documents',
                                     'metadata_is_not_a_global_event_gold_standard':True})
    manifest={'status':'complete','scope':scope,'source_files':expected,'source_manifest':bindings,'corpora':corpora,
              'projection':{'chunk_chars':300,'overlap_chars':40,'model_input':'short original only; prefix empty',
                            'returned_context':'full parent/qualifier/response blocks; noncontinuous blocks visibly separated',
                            'counts':dict(counts),'audit_counts':dict(audits)},
              'projection_sha256':sha_file(HERE/'projection_v2.py'),'normalization_sha256':sha_file(HERE/'normalize_v2.py'),
              'adapter_sha256':sha_file(__file__),'backend_sha256':BACKEND_SHA,'repo_manifest_sha256':sha_file(Path(repo)/'manifest.json'),
              'overlay_bindings':[{'file_id':r['file_id'],'base_draft_json_sha256':r['base_draft_json_sha256'],
                                   'effective_draft_json_sha256':sha_json(r['updated_draft'])} for r in overlay_rows],
              'tokenizer_source_sha256':TOKENIZER_SHA,
              'excluded_non_searchable':{'path':str((out/'non_searchable_units.jsonl').resolve()),
                                         'sha256':sha_file(out/'non_searchable_units.jsonl'),
                                         'count':sum(counts[c+':non_searchable'] for c in handles)},
              'prepare_seconds':time.perf_counter()-started,'human_approved':False}
    save_json(out/'manifest.json',manifest)
    print(json.dumps({'event':'prepare_complete','scope':scope,'files':expected,'counts':dict(counts),
                      'audit_counts':dict(audits),'seconds':manifest['prepare_seconds']}),flush=True)
    return manifest


def validate_run_scope(args,manifest):
    expected={'remaining8509':8509,'all':9639}
    if args.scope!=manifest.get('scope') or args.expected_files!=expected[args.scope] or manifest['source_files']!=expected[args.scope]:
        raise ValueError('requested scope and prepared source population differ')


def run_gpu(args):
    gpu=backend();gpu.aggregate=aggregate
    manifest=json.loads((args.prepared/'manifest.json').read_text(encoding='utf-8'))
    if manifest['adapter_sha256']!=ADAPTER_SHA or manifest['projection_sha256']!=sha_file(HERE/'projection_v2.py'):
        raise ValueError('V2 code differs from prepared binding')
    validate_run_scope(args,manifest)
    if manifest.get('tokenizer_source_sha256')!=TOKENIZER_SHA or sha_file(gpu.DEFAULT_SRC/'retrieval/tokenization.py')!=TOKENIZER_SHA:
        raise ValueError('prepared tokenizer binding differs')
    args.corpora=['structured'];args.project_src=gpu.DEFAULT_SRC
    args.embedding_model=gpu.DEFAULT_EMBEDDING;args.reranker_model=gpu.DEFAULT_RERANKER
    gpu.run(args)
    log_path=Path(str(args.output)+'.run.json');log=json.loads(log_path.read_text(encoding='utf-8'))
    log['v2_adapter']={'sha256':ADAPTER_SHA,'projection_sha256':manifest['projection_sha256'],
                       'scope':manifest['scope'],'full_parent_returned_separately':True,
                       'aggregation':'all preserved case IDs; file max; explicit source fallback'}
    if sha_file(__file__)!=ADAPTER_SHA:
        log['status']='failed';log['error']='V2 adapter changed during run';save_json(log_path,log)
        raise RuntimeError(log['error'])
    save_json(log_path,log)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    m=p.add_mutually_exclusive_group(required=True);m.add_argument('--prepare',action='store_true');m.add_argument('--run',action='store_true')
    p.add_argument('--repo',type=Path,default=ROOT/'finrisk-knowledge-base')
    p.add_argument('--prepared',type=Path,required=True);p.add_argument('--scope',choices=['remaining8509','all'],default='all')
    p.add_argument('--overlays',type=Path,nargs='*',default=[])
    p.add_argument('--queries',type=Path,default=ROOT/'outputs/FinRisk_召回实验_20261012/queries.jsonl')
    p.add_argument('--output',type=Path,default=HERE/'results.jsonl')
    p.add_argument('--cache',type=Path,default=ROOT/'work/finrisk_retrieval_20261012/vector_cache')
    p.add_argument('--expected-files',type=int,default=9639);p.add_argument('--device',choices=['cpu','cuda'],default='cuda')
    p.add_argument('--precision',choices=['float32','float16'],default='float16');p.add_argument('--batch-size',type=int,default=16)
    p.add_argument('--max-length',type=int,default=512);p.add_argument('--arms',nargs='+',choices=['bm25','dense','rrf','rrf_rerank'],default=['bm25','dense','rrf','rrf_rerank'])
    args=p.parse_args()
    if args.prepare:prepare_dataset(args.repo,args.prepared,args.scope,[r for f in args.overlays for r in read_rows(f)])
    else:run_gpu(args)


if __name__=='__main__':main()
