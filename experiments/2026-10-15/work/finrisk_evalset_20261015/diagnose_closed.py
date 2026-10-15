"""固定参考和排名的机械漏召回归因，不修改语义标签。"""
from common import *
freeze_check('qrels_freeze.json');freeze_check('prediction_freeze.json')
refs=rows(OUT/'qrels.jsonl');qids=[q['query_id'] for q in rows(OUT/'queries.jsonl')]
gm={(r['query_id'],r['file_id']):r for r in refs};maps=rows(OUT/'candidate_map.jsonl')
rr={r['query_id']:r for r in rows(OUT/'all_results.jsonl') if r['scope']=='closed100' and r['stage']=='ND'}
bm={r['pair_id']:r for r in rows(OUT/'bound_scores.jsonl')};routes=rows(OUT/'deepseek_routes.jsonl')
ur={r['query_id']:r['ND'] for r in routes if r['scope']=='closed100'}
qs={q['query_id']:q for q in rows(OUT/'queries.jsonl')}
miss=[];top=[]
for qid in qids:
 ranks={fid:i for i,fid in enumerate(rr[qid]['file_ids'],1)}
 candidates={r['file_id'] for r in maps if r['scope']=='closed100' and r['query_id']==qid}
 for (q,f),g in gm.items():
  if q==qid and g['grade']==3 and (f not in ranks or ranks[f]>20):
   mapped=[r for r in maps if r['scope']=='closed100' and r['query_id']==qid and r['file_id']==f]
   best=max((bm[r['pair_id']]['score'] for r in mapped),default=None)
   miss.append({'query_id':qid,'file_id':f,'direct_quote':g['source_quote'],'rank':ranks.get(f),
    'in_100_unit_candidates':f in candidates,'best_unit_score':best,'structural_reason':'not_in_candidate_units' if f not in candidates else 'ranked_after_20'})
 if gm[qid,rr[qid]['file_ids'][0]]['grade']!=3:
  f=rr[qid]['file_ids'][0];mapped=[r for r in maps if r['scope']=='closed100' and r['query_id']==qid and r['file_id']==f]
  best=sorted(mapped,key=lambda m:(-bm[m['pair_id']]['score'],m['unit_id']))[0]
  top.append({'query_id':qid,'query_text':qs[qid]['text'],'file_id':f,'reference':gm[qid,f],
   'API_best_unit_opinion':bm[best['pair_id']]})
save('closed_miss_diagnostics.json',{'missing_direct_pairs_from_top20':len(miss),'candidate_absent':sum(not r['in_100_unit_candidates'] for r in miss),'rank_after20':sum(r['in_100_unit_candidates'] for r in miss),'misses':miss,'top1_non_direct':top})
print(json.dumps(read(OUT/'closed_miss_diagnostics.json'),ensure_ascii=False))
