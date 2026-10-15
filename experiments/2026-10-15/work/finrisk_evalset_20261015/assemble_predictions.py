"""绑定已完成的真实API评分，按原V2文书最大分聚合并封存。"""
import random
from common import *
for n in ['input_freeze.json','candidate_freeze.json','api_freeze.json','qrels_freeze.json']:freeze_check(n)
binding=module(ROOT/'work/finrisk_llm_rerank_20261014/scores.py','actual_score_binding')
bound=binding.bind_scores(rows(OUT/'score_inputs.jsonl'),rows(OUT/'scores.jsonl'))
for r in bound:r['origin']='actual_deepseek_flash_API'
save('bound_scores.jsonl',bound,True)
maps=rows(OUT/'candidate_map.jsonl');wanted={r['unit_id'] for r in maps}
um={u['unit_id']:u for u in iterrows(INDEX) if u['unit_id'] in wanted};assert set(um)==wanted
adapter=module(ROOT/'work/finrisk_v2_20261012/run_v2.py','final_V2_adapter')
results=rows(OUT/'local_results.jsonl');nd=[]
for scope in ['closed100','full9639']:
 scoped=[r for r in maps if r['scope']==scope]
 for q in rows(OUT/'queries.jsonl'):
  ranked=binding.rank_units(q['query_id'],scoped,bound)
  _,files=adapter.aggregate(ranked,um,100)
  results.append({'scope':scope,'query_id':q['query_id'],'stage':'ND','files':files,'file_ids':[r['file_id'] for r in files]})
  nd.append({'scope':scope,'query_id':q['query_id'],'ND':ranked})
assert len(results)==200 and len({(r['scope'],r['query_id'],r['stage']) for r in results})==200
save('all_results.jsonl',results,True);save('deepseek_routes.jsonl',nd,True)
for scope in ['closed100','full9639']:
 for stage in ['BM25','BGE','RRF','N0','ND']:
  rr=[{'query_id':r['query_id'],'file_ids':r['file_ids']} for r in results if r['scope']==scope and r['stage']==stage]
  assert len(rr)==20;save(f'rankings/{scope}_{stage}.jsonl',rr,True)
paths=[OUT/n for n in ['bound_scores.jsonl','all_results.jsonl','deepseek_routes.jsonl','scores.jsonl','requests.jsonl','responses.jsonl','api_completion.json']]
paths+=list((OUT/'rankings').glob('*.jsonl'))
save('prediction_freeze.json',{'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'before_metrics':True,
 'qrels_sha256':sha(OUT/'qrels.jsonl'),'sha256':{str(p):sha(p) for p in paths},
 'code_sha256':{str(p):sha(p) for p in [WORK/'assemble_predictions.py',ROOT/'work/finrisk_llm_rerank_20261014/scores.py']}})
# 全库实际ND Top20的库外文书单独逐对标注；不给标注者排名/得分。
closed={d['file_id'] for d in rows(OUT/'corpus.jsonl')};qm={q['query_id']:q for q in rows(OUT/'query_specs.jsonl')};pool={}
for r in results:
 if r['scope']=='full9639' and r['stage']=='ND':
  for fid in r['file_ids'][:20]:
   if fid not in closed:pool.setdefault(fid,set()).add(r['query_id'])
sources={d['official_file_id']:d for d in iterrows(SOURCE) if d['official_file_id'] in pool}
fids=sorted(pool);random.Random(2026101505).shuffle(fids)
for i in range(3):
 dd=[]
 for fid in sorted(fids[i::3]):
  d=sources[fid];dd.append({'file_id':fid,'text':d['full_text'],'text_sha256':d['text_sha256'],
    'queries':[qm[q] for q in sorted(pool[fid])]})
 save(f'supplement_inputs/part_{i+1}.jsonl',dd,True)
save('supplement_selection.json',{'stage':'ND','top_k':20,'outside_documents':len(pool),'outside_pairs':sum(len(v) for v in pool.values()),
 'no_ranks_shown_to_annotators':True,'closed_reference_not_modified':True,
 'pairs':[{'query_id':qid,'file_id':fid} for fid in sorted(pool) for qid in sorted(pool[fid])]})
save('supplement_input_freeze.json',{'sha256':{str(p):sha(p) for p in [OUT/'supplement_selection.json',*sorted((OUT/'supplement_inputs').glob('*.jsonl'))]}})
print(json.dumps({'prediction_rows':len(results),'actual_API_scores':len(bound),'full_ND_outside_documents':len(pool),'full_ND_outside_pairs':sum(len(v) for v in pool.values())},ensure_ascii=False))
