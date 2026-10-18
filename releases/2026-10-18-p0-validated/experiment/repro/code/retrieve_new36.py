"""Reuse verified corpus vectors; retrieve anonymous inputs without references."""
import importlib.util
import sys
import time
from collections import defaultdict
from effect_common import *

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    start=time.perf_counter();qs=input_queries();cfg=read(ROOT/'outputs/FinRisk_召回率校准_20261013/retrieval_results.jsonl.run.json')
    sys.path.insert(0,str(ROOT/'work/finrisk_regulation_v1'))
    from law_index import Encoder,PROJECT,MODEL
    runner_path=ROOT/'work/finrisk_retrieval_20261012/runner.py'
    if sha(runner_path)!=cfg['runner_sha256']:raise ValueError('validated retrieval implementation changed')
    for name,key in [('sparse.py','bm25_source_sha256'),('tokenization.py','tokenizer_source_sha256')]:
        if sha(PROJECT/'retrieval'/name)!=cfg[key]:raise ValueError('validated sparse implementation changed')
    runner=module('frozen_new36_retrieval',runner_path);index=V2/'indexes/all9639_final/structured.jsonl'
    if sha(index)!=read(index.parent/'manifest.json')['corpora']['structured']['sha256']:raise ValueError('corpus fingerprint mismatch')
    units=[{k:r[k] for k in ['unit_id','file_id','case_id','text']} for r in rows(index)]
    if len(units)!=65475 or len({r['file_id'] for r in units})!=9639:raise ValueError('full structured corpus required')
    caches=[(p,read(p)) for p in (ROOT/'work/finrisk_recall_calibration_20261013/vector_cache').glob('*.json')]
    caches=[(p,m) for p,m in caches if m.get('shape')==[65475,512]]
    if len(caches)!=1:raise ValueError('unique frozen vector cache required')
    cache,meta=caches[0];vector_path=cache.with_suffix('.npy')
    if sha(vector_path)!=meta['npy_sha256'] or meta['ordered_unit_text_sha256']!=runner.ordered_text_sha(units):raise ValueError('vectors not bound to corpus text')
    encoder=Encoder()
    if meta['binding']['model']!=runner.model_fingerprint(MODEL) or meta['binding']['torch']!=encoder.torch.__version__:raise ValueError('embedding model/runtime mismatch')
    import numpy as np
    vectors=np.load(vector_path,allow_pickle=False,mmap_mode='r')
    if vectors.flags.writeable or vectors.shape!=(65475,512):raise ValueError('frozen read-only matrix required')
    query_vectors=encoder.encode([q['text'] for q in qs],'query',[q['opaque_id'] for q in qs]);np.save(OUT/'retrieval/query_vectors.npy',query_vectors,allow_pickle=False)
    sys.path.insert(0,str(PROJECT));from retrieval.sparse import SparseRetrievalIndex,RetrievalDocument
    sparse=SparseRetrievalIndex([RetrievalDocument(unit_id=r['unit_id'],case_ids=(r['case_id'],),text=r['text'],source='structured') for r in units],k1=1.5,b=.75)
    routes=[]
    for i,q in enumerate(qs):
        bm=[dict(unit_id=h.document.unit_id,score=float(h.score),rank=h.rank) for h in sparse.search(q['text'],top_k=100)]
        scores=vectors@query_vectors[i];order=np.lexsort((np.arange(len(scores)),-scores))[:100]
        dense=[dict(unit_id=units[int(j)]['unit_id'],score=float(scores[j]),rank=k) for k,j in enumerate(order,1)]
        fused=runner.rrf([bm,dense],k=60,top_k=100)
        if len(fused)!=100:raise ValueError('100 unique fused candidates required')
        routes.append(dict(opaque_id=q['opaque_id'],BM25=bm,BGE=dense,RRF=fused));print(json.dumps(dict(retrieved=i+1,total=36)),flush=True)
    del sparse
    wanted={h['unit_id'] for r in routes for h in r['RRF']};files={r['file_id'] for r in units if r['unit_id'] in wanted};del units
    source_units=[r for r in rows(index) if r['file_id'] in files];byid={r['unit_id']:r for r in source_units};byfile=defaultdict(list)
    for r in source_units:byfile[r['file_id']].append(r)
    sys.path.insert(0,str(ROOT/'work/finrisk_two_layer_validation_20261017'));from context_builder import build_context
    contexts={};packets=[];mapping=[]
    for q,route in zip(qs,routes):
        for hit in route['RRF']:
            uid=hit['unit_id'];unit=byid[uid]
            if uid not in contexts:contexts[uid]=build_context(unit,byfile[unit['file_id']],limit=800)
            context=contexts[uid];text=context['unit_text'];pid='FXR_'+canonical_sha([q['text'],uid,textsha(text)])[:24]
            packets.append(dict(pair_id=pid,query_text=q['text'],unit_text=text))
            mapping.append(dict(pair_id=pid,opaque_id=q['opaque_id'],unit_id=uid,file_id=unit['file_id'],rrf_rank=hit['rank'],unit_text_sha256=textsha(text),segments=context['segments']))
    if len(packets)!=3600 or len({p['pair_id'] for p in packets})!=3600:raise ValueError('rerank task collision')
    save(OUT/'retrieval/routes.jsonl',routes,True);save(OUT/'retrieval/rerank_packets.jsonl',packets,True);save(OUT/'retrieval/candidate_map.jsonl',mapping,True);save(OUT/'retrieval/query_token_audit.jsonl',encoder.audit,True)
    rules=ROOT/'outputs/FinRisk_机制与片段消融_20261016/mechanism_rules.md';(OUT/'retrieval/rerank_rules.md').write_bytes(rules.read_bytes())
    paths=[DATA/'model_inputs.jsonl',index,vector_path,runner_path,rules,PROJECT/'retrieval/sparse.py',PROJECT/'retrieval/tokenization.py',Path(__file__)]+list((OUT/'retrieval').glob('*'))
    save(OUT/'retrieval/freeze.json',dict(sha256={str(p):sha(p) for p in paths},created_utc=utc()))
    receipt=dict(passed=True,queries=36,documents=9639,units=65475,route_top_k=100,rrf_top_k=100,weights=[1,1],rrf_c=60,new_paid_calls=0,reference_answers_read=False,document_vectors_recomputed=0,seconds=time.perf_counter()-start,python=sys.executable,torch=encoder.torch.__version__)
    save(OUT/'retrieval/receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
