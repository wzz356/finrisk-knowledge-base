"""Two static retrieval representations over the complete frozen corpus; no answers."""
import importlib.util
import json
import sys
import time
from collections import defaultdict
from common_night import *
from auxiliary import auxiliary_query, fuse, expanded_routes


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    started = time.perf_counter()
    freeze_check()
    freeze_check('pre_retrieval_freeze.json')
    if (OUT/'routes.jsonl').exists():
        raise FileExistsError('refuse to replace retrieval results')
    queries = rows(OUT/'queries_final.jsonl')
    if len(queries)!=24 or any(set(q)!={'query_id','text','text_sha256'} or tsha(q['text'])!=q['text_sha256'] for q in queries):
        raise ValueError('input-only queries required')
    lexicon = read(OUT/'auxiliary_lexicon.json')
    expressions = [auxiliary_query(q['text'],lexicon) for q in queries]
    cfg = read(ROOT/'outputs/FinRisk_召回率校准_20261013/retrieval_results.jsonl.run.json')
    law_work = ROOT/'work/finrisk_regulation_v1'
    sys.path.insert(0,str(law_work))
    from law_index import Encoder,PROJECT,MODEL
    runner_path = ROOT/'work/finrisk_retrieval_20261012/runner.py'
    if sha(runner_path)!=cfg['runner_sha256']:
        raise ValueError('validated runner changed')
    for filename,key in [('sparse.py','bm25_source_sha256'),('tokenization.py','tokenizer_source_sha256')]:
        if sha(PROJECT/'retrieval'/filename)!=cfg[key]:
            raise ValueError('validated sparse dependency changed')
    runner = module('night_validated_runner',runner_path)
    manifest = read(INDEX.parent/'manifest.json')
    if sha(INDEX)!=manifest['corpora']['structured']['sha256']:
        raise ValueError('index bytes changed')
    units=[]
    with INDEX.open(encoding='utf-8-sig') as f:
        for line in f:
            u=json.loads(line);units.append({k:u[k] for k in ['unit_id','file_id','case_id','text']})
    if len(units)!=65475 or len({u['file_id'] for u in units})!=9639:
        raise ValueError('full corpus count mismatch')
    ordered=runner.ordered_text_sha(units)
    cache_dir=ROOT/'work/finrisk_recall_calibration_20261013/vector_cache'
    caches=[(p,read(p)) for p in cache_dir.glob('*.json')]
    caches=[(p,m) for p,m in caches if m.get('shape')==[65475,512]]
    if len(caches)!=1:raise ValueError('ambiguous original document cache')
    cache,meta=caches[0];vector_path=cache.with_suffix('.npy')
    vector_hash=sha(vector_path)
    if meta['npy_sha256']!=vector_hash or meta['ordered_unit_text_sha256']!=ordered:
        raise ValueError('document vector cache mismatch')
    encoder=Encoder()
    if meta['binding']['model']!=runner.model_fingerprint(MODEL) or meta['binding']['torch']!=encoder.torch.__version__:
        raise ValueError('encoder model/runtime mismatch')
    import numpy as np
    vectors=np.load(vector_path,allow_pickle=False,mmap_mode='r')
    if vectors.flags.writeable or vectors.shape!=(65475,512):raise ValueError('read-only vectors required')
    values=[q['text'] for q in queries]+[e['text'] for e in expressions]
    qvectors=encoder.encode(values,'query',[q['query_id'] for q in queries]+['AUX_'+q['query_id'] for q in queries])
    np.save(OUT/'query_vectors.npy',qvectors,allow_pickle=False)
    sys.path.insert(0,str(PROJECT))
    from retrieval.sparse import SparseRetrievalIndex,RetrievalDocument
    sparse=SparseRetrievalIndex([RetrievalDocument(unit_id=u['unit_id'],case_ids=(u['case_id'],),text=u['text'],source='structured') for u in units],k1=1.5,b=.75)
    def route(text,vec):
        bm=[dict(unit_id=h.document.unit_id,score=float(h.score),rank=h.rank) for h in sparse.search(text,top_k=100)]
        scores=vectors@vec
        order=np.lexsort((np.arange(len(scores)),-scores))[:100]
        dense=[dict(unit_id=units[int(j)]['unit_id'],score=float(scores[j]),rank=k) for k,j in enumerate(order,1)]
        return bm,dense
    routes=[]
    for i,(q,extra) in enumerate(zip(queries,expressions)):
        bm,dense=route(q['text'],qvectors[i])
        baseline=fuse([bm,dense])
        if baseline!=runner.rrf([bm,dense],k=60,top_k=100):raise ValueError('baseline RRF changed')
        abm,adense=route(extra['text'],qvectors[len(queries)+i]) if extra['mechanism_ids'] else (None,None)
        expanded=expanded_routes(bm,dense,abm,adense)
        if len(baseline)!=100 or len(expanded)!=100:raise ValueError('candidate count differs')
        routes.append(dict(query_id=q['query_id'],original_BM25=bm,original_BGE=dense,
                           auxiliary_BM25=abm,auxiliary_BGE=adense,baseline=baseline,expanded=expanded,
                           auxiliary_text=extra['text'],hypothesis_mechanism_ids=extra['mechanism_ids']))
        print(json.dumps(dict(retrieved=i+1,total=24),ensure_ascii=False),flush=True)
    del sparse
    wanted={h['unit_id'] for r in routes for arm in ['baseline','expanded'] for h in r[arm]}
    file_ids={u['file_id'] for u in units if u['unit_id'] in wanted}
    del units
    source_units=[]
    with INDEX.open(encoding='utf-8-sig') as f:
        for line in f:
            u=json.loads(line)
            if u['file_id'] in file_ids:source_units.append(u)
    byid={u['unit_id']:u for u in source_units};byfile=defaultdict(list)
    for u in source_units:byfile[u['file_id']].append(u)
    old_work=ROOT/'work/finrisk_two_layer_validation_20261017'
    sys.path.insert(0,str(old_work))
    from context_builder import build_context
    contexts={};packets=[];mapping=[];pair_by_binding={}
    for q,r in zip(queries,routes):
        for arm in ['baseline','expanded']:
            for hit in r[arm]:
                uid=hit['unit_id'];u=byid[uid]
                if uid not in contexts:contexts[uid]=build_context(u,byfile[u['file_id']],limit=800)
                context=contexts[uid];text=context['unit_text']
                binding=(q['query_id'],uid,tsha(text))
                if binding not in pair_by_binding:
                    pair_id='NK_'+tsha('|'.join(binding))[:24]
                    pair_by_binding[binding]=pair_id
                    packets.append(dict(pair_id=pair_id,query_text=q['text'],query_text_sha256=q['text_sha256'],
                                        unit_text=text,unit_text_sha256=tsha(text)))
                mapping.append(dict(pair_id=pair_by_binding[binding],query_id=q['query_id'],arm=arm,
                                    unit_id=uid,file_id=u['file_id'],rrf_rank=hit['rank'],
                                    unit_text_sha256=tsha(text),segments=context['segments']))
    if len(mapping)!=4800 or len(packets)>4800:raise ValueError('task count mismatch')
    if sha(vector_path)!=vector_hash:raise ValueError('document vectors changed')
    save(OUT/'routes.jsonl',routes,True)
    save(OUT/'rerank_inputs.jsonl',packets,True)
    save(OUT/'candidate_map.jsonl',mapping,True)
    save(OUT/'query_token_audit.jsonl',encoder.audit,True)
    rules=ROOT/'outputs/FinRisk_机制与片段消融_20261016/mechanism_rules.md'
    (OUT/'rerank_rules.md').write_bytes(rules.read_bytes())
    save(OUT/'retrieval_receipt.json',dict(utc=utc(),seconds=time.perf_counter()-started,queries=24,
         files=9639,units=65475,logical_candidate_positions=4800,actual_unique_rerank_tasks=len(packets),
         original_and_auxiliary_query_vectors=len(qvectors),document_vectors_recomputed=0,
         original_index_sha256=sha(INDEX),document_vectors_sha256=vector_hash,
         auxiliary_table_sha256=sha(OUT/'auxiliary_lexicon.json'),input_answers_read=False,
         query_variants_balanced_within_modality=True,cross_modality_weights=[1,1],global_true_recall=False))
    paths=[OUT/n for n in ['routes.jsonl','rerank_inputs.jsonl','candidate_map.jsonl','rerank_rules.md','queries_final.jsonl','query_vectors.npy']]
    paths+=[WORK/'retrieve_experiment.py',rules,INDEX,vector_path,PROJECT/'retrieval/sparse.py',PROJECT/'retrieval/tokenization.py']
    save(OUT/'retrieval_freeze.json',dict(utc=utc(),sha256={str(p):sha(p) for p in paths}))
    print(json.dumps(dict(status='complete',unique_tasks=len(packets),new_paid_calls=0),ensure_ascii=False))


if __name__=='__main__':main()
