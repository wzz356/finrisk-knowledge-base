"""Offline ranking evaluator; complete closed Recall, no true full Recall."""
import argparse,json
from pathlib import Path
from evaluator_metrics import score,aggregate
KS=(1,5,10,20)
def rows(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]

def evaluate(scope,queries,corpus,qrels,rankings,risk_ids):
 qids={q['query_id'] for q in queries};qm={(r['query_id'],r['file_id']):r for r in qrels if r['query_id'] in qids}
 if len(qm)!=sum(r['query_id'] in qids for r in qrels):raise ValueError('重复相关性配对')
 if {r['query_id'] for r in rankings}!=qids or len(rankings)!=len(qids):raise ValueError('排名未完整唯一覆盖本视图')
 fids={d['file_id'] for d in corpus}
 if scope=='closed' and set(qm)!={(q,f) for q in qids for f in fids}:raise ValueError('闭集参考不完整')
 if any(type(r['grade']) is not int or r['grade'] not in [0,1,2,3] for r in qm.values()):raise ValueError('非法等级')
 per=[];aux=[]
 for r in rankings:
  qid=r['query_id'];ids=r['file_ids']
  if scope=='closed' and not set(ids)<=fids:raise ValueError('闭集排名有库外文件')
  grades={f:g['grade'] for (q,f),g in qm.items() if q==qid}
  primary=score(ids,{f:2 if g==3 else 0 for f,g in grades.items()},ks=KS)
  secondary=score(ids,{f:2 if g==3 else 1 if g==2 else 0 for f,g in grades.items()},ks=KS)
  for k in KS:primary[f'precision{k}']=primary[f'relevant_count{k}']/k;primary[f'success{k}']=primary[f'relevant_count{k}']>0
  per.append(dict(query_id=qid,**primary));aux.append(dict(query_id=qid,**{f'ndcg{k}':secondary[f'ndcg{k}'] for k in KS}))
 chosen=[r for r in per if r['query_id'] in risk_ids];summary=aggregate(chosen,ks=KS)
 for k in KS:
  summary[f'precision{k}']=sum(r[f'precision{k}'] for r in chosen)/len(chosen)
  summary[f'success{k}']=sum(r[f'success{k}'] for r in chosen)/len(chosen)
 if scope=='full':
  for obj in [summary,*per]:
   for key in list(obj):
    if key.startswith('recall'):del obj[key]
 return dict(scope=scope,queries=len(queries),scored_risk_queries=len(chosen),summary=summary,per_query=per,
  auxiliary_graded_ndcg=aux,zero_direct_positive_queries=[r['query_id'] for r in per if not r['positive_reference_count']],
  global_recall=None,recall_scope='fixed100 exhaustive' if scope=='closed' else 'not reported',
  ndcg_scope='complete fixed100' if scope=='closed' else 'common judged pool, global ideal unknown',
  reference_quality='model silver pending human',model_inference_performed=False)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--dataset',required=True,type=Path);ap.add_argument('--scope',choices=['closed','full'],required=True)
 ap.add_argument('--rankings',required=True,type=Path);ap.add_argument('--qrels',type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();d=a.dataset
 name='closed_queries.jsonl' if a.scope=='closed' else 'retrieval_queries.jsonl'
 relpath=a.qrels or d/('qrels_closed.jsonl' if a.scope=='closed' else 'qrels_full_pool.jsonl')
 if not relpath.exists():raise ValueError('缺该视图真实相关性参考；先运行检索并独立标注未知配对，不可用空标注填0')
 risk={q['query_id'] for q in rows(d/'master.jsonl') if q['expected_state']=='risk'}
 result=evaluate(a.scope,rows(d/name),rows(d/'corpus.jsonl') if a.scope=='closed' else [],rows(relpath),rows(a.rankings),risk)
 with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
 print(json.dumps(result['summary'],ensure_ascii=False))

if __name__=='__main__':main()
