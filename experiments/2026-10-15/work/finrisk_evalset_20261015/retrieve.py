"""冻结问题后实际检索；与标注并行，排名不提供给标注者。"""
import argparse,random,sys,time,shutil
from common import *
from retrieval_case_ids import retrieval_case_ids

def run():
 freeze_check();start=time.perf_counter()
 source_manifest=read(V2/'indexes/all9639_final/manifest.json')
 assert source_manifest['status']=='complete' and source_manifest['source_files']==9639
 queries=rows(OUT/'queries.jsonl');closed_ids={d['file_id'] for d in rows(OUT/'corpus.jsonl')}
 units=rows(INDEX);assert len(units)==65475 and len({u['file_id'] for u in units})==9639
 closed=[u for u in units if u['file_id'] in closed_ids];assert {u['file_id'] for u in closed}==closed_ids
 if (OUT/'closed_index_units.jsonl').exists():assert rows(OUT/'closed_index_units.jsonl')==closed
 else:save('closed_index_units.jsonl',closed,True)
 runner=module(ROOT/'work/finrisk_retrieval_20261012/runner.py','benchmark_backend')
 adapter=module(ROOT/'work/finrisk_v2_20261012/run_v2.py','benchmark_v2_aggregation')
 cfg=read(ROOT/'outputs/FinRisk_召回率校准_20261013/retrieval_results.jsonl.run.json')['parameters']
 args=argparse.Namespace(**cfg);args.output=OUT/'retrieval';args.cache=WORK/'vector_cache'
 args.embedding_model=Path(args.embedding_model);args.reranker_model=Path(args.reranker_model)
 args.cache.mkdir(parents=True,exist_ok=True)
 # 相同原索引的实际文档向量缓存复制到新工作目录；旧缓存只读。
 prior=ROOT/'work/finrisk_recall_calibration_20261013/vector_cache'
 for p in prior.glob('*.json'):
  meta=read(p)
  if meta.get('shape')==[65475,512]:
   npy=p.with_suffix('.npy');assert sha(npy)==meta['npy_sha256']
   for orig in [p,npy]:shutil.copyfile(orig,args.cache/orig.name)
 model=runner.LocalModels(args);qv=model.encode(queries,'query','shared')
 fullv=model.encode(units,'document','structured');import numpy as np
 closed_positions=np.array([i for i,u in enumerate(units) if u['file_id'] in closed_ids],dtype=np.int64)
 cv=fullv[closed_positions]
 binding={'parent_index_sha256':sha(INDEX),'parent_vector_events':model.log['cache_events'],
  'selected_parent_positions':closed_positions.tolist(),'subset_ids':[u['unit_id'] for u in closed],
  'subset_ordered_text_sha256':runner.ordered_text_sha(closed),'not_new_embedding_values':True}
 if (OUT/'closed_vector_binding.json').exists():
  old=read(OUT/'closed_vector_binding.json')
  for k in ['parent_index_sha256','selected_parent_positions','subset_ids','subset_ordered_text_sha256']:assert old[k]==binding[k]
 else:save('closed_vector_binding.json',binding)
 sys.path.insert(0,cfg['project_src']);from retrieval.sparse import SparseRetrievalIndex,RetrievalDocument
 allresults=[];routes=[];packet_map={};mapping=[];scope_stats=[]
 for scope,current,vec in [('closed100',closed,cv),('full9639',units,fullv)]:
  st=time.perf_counter();um={u['unit_id']:u for u in current}
  sparse=SparseRetrievalIndex([RetrievalDocument(unit_id=u['unit_id'],case_ids=retrieval_case_ids(u),text=u['text'],source='structured',weight=1.) for u in current],k1=1.5,b=.75)
  for qi,q in enumerate(queries):
   bm=[{'unit_id':h.document.unit_id,'score':float(h.score),'rank':h.rank} for h in sparse.search(q['text'],top_k=100)]
   ds=vec@qv[qi];ix=np.lexsort((np.arange(len(ds)),-ds))
   dense=[{'unit_id':current[int(j)]['unit_id'],'score':float(ds[j]),'rank':r} for r,j in enumerate(ix[:100],1)]
   union=runner.rrf([bm,dense],60,200);cand=union[:100];assert len(cand)==100
   nr=model.rerank(q['text'],cand,um,scope,q['query_id'])
   routes.append({'scope':scope,'query_id':q['query_id'],'BM25':bm,'BGE':dense,'RRF_union':union,'RRF_top100':cand,'N0':nr})
   for stage,ranked in [('BM25',bm),('BGE',dense),('RRF',cand),('N0',nr)]:
    _,files=adapter.aggregate(ranked,um,top_k=100)
    allresults.append({'scope':scope,'query_id':q['query_id'],'stage':stage,'files':files,'file_ids':[h['file_id'] for h in files]})
   for h in cand:
    u=um[h['unit_id']];key=(q['query_id'],u['unit_id'],tsha(u['text']))
    if key not in packet_map:
     packet_map[key]={'query_id':q['query_id'],'query_key':f'Q{qi+1:02}','query_text':q['text'],'query_text_sha256':q['text_sha256'],
      'unit_id':u['unit_id'],'file_id':u['file_id'],'unit_text':u['text'],'unit_text_sha256':tsha(u['text'])}
    mapping.append({'scope':scope,'query_id':q['query_id'],'unit_id':u['unit_id'],'file_id':u['file_id'],'key':key})
   print(json.dumps({'retrieval_progress':scope,'query_complete':qi+1,'total':20,'candidate_units':100},ensure_ascii=False),flush=True)
  scope_stats.append({'scope':scope,'files':100 if scope=='closed100' else 9639,'units':len(current),'seconds':time.perf_counter()-st})
 model.token_handle.close();save('local_model_log.json',model.log)
 unique=list(packet_map.items());random.Random(2026101504).shuffle(unique);key_pid={k:f'KB{i:05}' for i,(k,p) in enumerate(unique,1)}
 packets=[{'pair_id':key_pid[k],**{kk:p[kk] for kk in ['query_key','query_text','query_text_sha256','unit_text','unit_text_sha256']}} for k,p in unique]
 for m in mapping:m['pair_id']=key_pid[tuple(m.pop('key'))]
 assert len(mapping)==4000 and len({p['pair_id'] for p in packets})==len(packets)
 save('score_inputs.jsonl',packets,True);save('candidate_map.jsonl',mapping,True)
 save('local_results.jsonl',allresults,True);save('routes.jsonl',routes,True)
 audit=rows(OUT/'retrieval.token_audit.jsonl')
 save('retrieval_completion.json',{'status':'complete','queries':20,'scopes':scope_stats,'unique_API_pairs':len(packets),
  'mapped_pairs':4000,'same_query_unit_text_reused_between_scopes':4000-len(packets),
  'total_seconds':time.perf_counter()-start,'truncated_by_stage':{s:sum(a['truncated'] for a in audit if a['stage']==s) for s in ['embedding','rerank']}})
 freeze_check();save('candidate_freeze.json',{'utc':datetime.now(timezone.utc).isoformat(),'before_API_and_metrics':True,
  'sha256':{str(OUT/n):sha(OUT/n) for n in ['closed_index_units.jsonl','closed_vector_binding.json','local_model_log.json',
   'score_inputs.jsonl','candidate_map.jsonl','local_results.jsonl','routes.jsonl','retrieval_completion.json','retrieval.token_audit.jsonl']},
  'code_sha256':{str(p):sha(p) for p in [WORK/'retrieve.py',WORK/'retrieval_case_ids.py',ROOT/'work/finrisk_retrieval_20261012/runner.py',ROOT/'work/finrisk_v2_20261012/run_v2.py',
   Path(cfg['project_src'])/'retrieval/sparse.py',Path(cfg['project_src'])/'retrieval/tokenization.py']}})
 print(json.dumps(read(OUT/'retrieval_completion.json'),ensure_ascii=False),flush=True)
if __name__=='__main__':run()
