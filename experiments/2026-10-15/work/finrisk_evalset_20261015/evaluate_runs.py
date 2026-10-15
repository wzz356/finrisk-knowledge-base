"""完整闭集指标和全库已知参考覆盖严格分开。"""
from common import *
from scoring import direct_score,graded_score,base
for n in ['input_freeze.json','qrels_freeze.json','prediction_freeze.json']:freeze_check(n)
sys.path.insert(0,str(OUT))
evaluate=module(OUT/'evaluate.py','standalone_eval')
qs=rows(OUT/'query_specs.jsonl');qrels=rows(OUT/'qrels.jsonl');gm={q['query_id']:{r['file_id']:r['grade'] for r in qrels if r['query_id']==q['query_id']} for q in qs}
results=rows(OUT/'all_results.jsonl');closed=[];full=[]
for stage in ['BM25','BGE','RRF','N0','ND']:
 rr=rows(OUT/f'rankings/closed100_{stage}.jsonl');ev=evaluate.evaluate(OUT,rr)
 save(f'metrics/closed100_{stage}.json',ev)
 grouped=[]
 for group in sorted({q['group'] for q in qs}):
  ids={q['query_id'] for q in qs if q['group']==group}
  grouped.append({'group':group,**base.aggregate([r for r in ev['primary_per_query'] if r['query_id'] in ids])})
 closed.append({'stage':stage,'primary':ev['primary_summary'],'auxiliary_graded_ndcg':{f'ndcg{k}':ev['auxiliary_graded_summary'][f'ndcg{k}'] for k in [5,10,20]},'groups':grouped,
  'group_macro':{key:sum((g[key]['value'] if isinstance(g[key],dict) else g[key]) for g in grouped)/len(grouped) for key in ['recall5','recall10','recall20','mrr20','top1_hit_rate','ndcg5','ndcg10','ndcg20']}})
 known=[]
 for r in results:
  if r['scope']=='full9639' and r['stage']==stage:
   positives={fid for fid,g in gm[r['query_id']].items() if g==3}
   known.append({'query_id':r['query_id'],'known_direct_count':len(positives),
    **{f'known_reference_coverage{k}':len(set(r['file_ids'][:k])&positives)/len(positives) for k in [5,10,20,100]},
    'unjudged_outside_closed_top20':len(set(r['file_ids'][:20])-set(gm[r['query_id']]))})
 full.append({'stage':stage,'metric_name':'known_closed_reference_coverage_not_full_corpus_recall','per_query':known,
  'macro':{f'known_reference_coverage{k}':sum(r[f'known_reference_coverage{k}'] for r in known)/20 for k in [5,10,20,100]}})
save('closed_metrics_summary.json',{'scope':'closed100','primary_relevant':'grade3','stages':closed,'zero_positive_queries':[]})
save('full_known_reference_coverage.json',{'scope':'full9639','denominator':'all grade3 documents inside the 100-document closed corpus only',
 'not_true_full_corpus_recall':True,'unjudged_files_not_marked_nonrelevant':True,'stages':full})
print(json.dumps({'closed':[{k:r[k] for k in ['stage','primary']} for r in closed],'full_known_coverage':[{k:r[k] for k in ['stage','macro']} for r in full]},ensure_ascii=False))
