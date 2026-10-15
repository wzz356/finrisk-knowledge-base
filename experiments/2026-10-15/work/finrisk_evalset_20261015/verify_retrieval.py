"""只回放已有向量和排名；不重复请求模型或API。"""
import math,hashlib
import numpy as np
from collections import defaultdict
from common import *
for n in ['input_freeze.json','candidate_freeze.json','prediction_freeze.json']:freeze_check(n)
units=rows(INDEX);closed_ids={d['file_id'] for d in rows(OUT/'corpus.jsonl')};closed=[u for u in units if u['file_id'] in closed_ids]
queries=rows(OUT/'queries.jsonl');cfg=read(ROOT/'outputs/FinRisk_召回率校准_20261013/retrieval_results.jsonl.run.json')['parameters']
sys.path.insert(0,cfg['project_src']);from retrieval.sparse import SparseRetrievalIndex,RetrievalDocument
def ordered_sha(items,key):
 h=hashlib.sha256()
 for i in items:h.update((json.dumps([i[key],i['text']],ensure_ascii=False,separators=(',',':'))+'\n').encode())
 return h.hexdigest()
cache={}
for p in (WORK/'vector_cache').glob('*.json'):
 m=read(p);a=np.load(p.with_suffix('.npy'),mmap_mode='r');assert sha(p.with_suffix('.npy'))==m['npy_sha256'] and list(a.shape)==m['shape']
 assert np.isfinite(a).all() and np.allclose(np.linalg.norm(a,axis=1),1,atol=2e-5)
 encoded_inputs=[dict(q,text=m['binding']['query_instruction']+q['text']) for q in queries] if m['binding']['kind']=='query' else units
 assert m['ordered_unit_text_sha256']==ordered_sha(encoded_inputs,'query_id' if m['binding']['kind']=='query' else 'unit_id')
 assert m['binding']['model']==read(OUT/'local_model_log.json')['embedding'];cache[m['binding']['kind']]=a
v=cache['document'];qv=cache['query'];positions=np.array([i for i,u in enumerate(units) if u['file_id'] in closed_ids]);cv=v[positions]
b=read(OUT/'closed_vector_binding.json');assert b['selected_parent_positions']==positions.tolist() and b['subset_ids']==[u['unit_id'] for u in closed] and b['subset_ordered_text_sha256']==ordered_sha(closed,'unit_id')
routes={(r['scope'],r['query_id']):r for r in rows(OUT/'routes.jsonl')};nd={(r['scope'],r['query_id']):r['ND'] for r in rows(OUT/'deepseek_routes.jsonl')}
results={(r['scope'],r['query_id'],r['stage']):r for r in rows(OUT/'all_results.jsonl')};scores={r['pair_id']:r for r in rows(OUT/'scores.jsonl')};maps=rows(OUT/'candidate_map.jsonl')
verified=0
for scope,current,vectors in [('closed100',closed,cv),('full9639',units,v)]:
 um={u['unit_id']:u for u in current}
 sparse=SparseRetrievalIndex([RetrievalDocument(unit_id=u['unit_id'],case_ids=(u['case_id'],),text=u['text'],source='structured',weight=1.) for u in current],k1=1.5,b=.75)
 for qi,q in enumerate(queries):
  r=routes[scope,q['query_id']];bm=sparse.search(q['text'],top_k=100)
  assert [h.document.unit_id for h in bm]==[h['unit_id'] for h in r['BM25']]
  assert all(math.isclose(h.score,g['score'],abs_tol=1e-10) for h,g in zip(bm,r['BM25']))
  ds=vectors@qv[qi];ix=np.lexsort((np.arange(len(ds)),-ds))[:100]
  assert [current[int(i)]['unit_id'] for i in ix]==[h['unit_id'] for h in r['BGE']]
  assert all(math.isclose(float(ds[i]),g['score'],abs_tol=2e-6) for i,g in zip(ix,r['BGE']))
  fused=defaultdict(float)
  for route in [r['BM25'],r['BGE']]:
   for rank,h in enumerate(route,1):fused[h['unit_id']]+=1/(60+rank)
  fused_order=sorted(fused,key=lambda uid:(-fused[uid],uid))
  assert fused_order==[h['unit_id'] for h in r['RRF_union']]
  assert all(math.isclose(fused[h['unit_id']],h['score'],abs_tol=1e-12) for h in r['RRF_union'])
  assert r['RRF_top100']==r['RRF_union'][:100]
  wanted={h['unit_id'] for h in r['RRF_top100']}
  assert {h['unit_id'] for h in r['N0']}==wanted and {h['unit_id'] for h in nd[scope,q['query_id']]}==wanted
  assert r['N0']==sorted(r['N0'],key=lambda h:(-h['score'],h['unit_id']))
  mm={m['unit_id']:m for m in maps if m['scope']==scope and m['query_id']==q['query_id']}
  assert set(mm)==wanted
  assert all(h['score']==scores[mm[h['unit_id']]['pair_id']]['score'] for h in nd[scope,q['query_id']])
  for stage,ranked in [('BM25',r['BM25']),('BGE',r['BGE']),('RRF',r['RRF_top100']),('N0',r['N0']),('ND',nd[scope,q['query_id']])]:
   mx={}
   for h in ranked:
    f=um[h['unit_id']]['file_id'];mx[f]=max(mx.get(f,-math.inf),h['score'])
   order=sorted(mx,key=lambda f:(-mx[f],f));actual=results[scope,q['query_id'],stage]
   assert order==actual['file_ids']
   assert all(math.isclose(mx[h['file_id']],h['score'],abs_tol=1e-12) for h in actual['files'])
  verified+=1
 print(json.dumps({'scope_verified':scope,'queries':20},ensure_ascii=False),flush=True)
audit=rows(OUT/'retrieval.token_audit.jsonl');assert all(a['truncated'] is False for a in audit)
assert sum(a['stage']=='rerank' for a in audit)==4000
log=read(OUT/'local_model_log.json')
for model in ['embedding','reranker']:
 for f in log[model]['files']:
  p=Path(log[model]['path'])/f['path'];assert p.stat().st_size==f['size'] and sha(p)==f['sha256']
save('retrieval_verification.json',{'status':'passed','scope_queries_replayed':verified,'dense_vectors_shapes':{'document':list(v.shape),'query':list(qv.shape)},
 'closed_vectors_exact_subset':True,'BM25_replayed':True,'dense_rank_recomputed':True,'RRF_equal_weight_recomputed':True,
 'all_200_file_rankings_max_aggregation_verified':True,'rerank_candidates_and_actual_API_bindings_verified':True,
 'truncated_inputs':0,'local_model_file_hashes_verified':True,'no_new_model_API_requests':True})
print(json.dumps(read(OUT/'retrieval_verification.json'),ensure_ascii=False))
