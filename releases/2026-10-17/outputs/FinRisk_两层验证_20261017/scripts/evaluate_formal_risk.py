"""Offline risk scoring; semantic quality remains explicitly unscored."""
import argparse,json
from pathlib import Path
from collections import Counter
STATES={'risk','no_clear_risk','insufficient'}
def rows(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def ratio(a,b):return a/b if b else None
def prf(tp,fp,fn):return dict(tp=tp,fp=fp,fn=fn,precision=ratio(tp,tp+fp),recall=ratio(tp,tp+fn),f1=ratio(2*tp,2*tp+fp+fn))

def score_predictions(master,predictions,labels):
 gm={q['query_id']:q for q in master};pm={p['query_id']:p for p in predictions}
 if len(gm)!=len(master) or len(pm)!=len(predictions) or set(gm)!=set(pm):raise ValueError('预测必须完整唯一覆盖参考题号')
 correct=tp=fp=fn=ltp=lfp=lfn=gtp=gfp=gfn=exact=0;states=Counter();per=[]
 for qid,q in gm.items():
  p=pm[qid]
  if p['state'] not in STATES:raise ValueError('未知状态')
  for k in ['risk_labels','candidate_labels']:
   if not isinstance(p.get(k),list) or any(not isinstance(l,str) for l in p[k]) or len(set(p[k]))!=len(p[k]) or set(p[k])-set(labels):raise ValueError('非法预测标签')
  required=set(q['required_labels']);optional=set(q['optional_labels']);given=set(p['risk_labels'])
  a=len(required&given);b=len(given-required-optional);c=len(required-given)
  groups=[set(g) for g in q.get('required_label_groups',[[l] for l in q['required_labels']])]
  if any(not g or g-set(labels) for g in groups) or any(groups[i]&groups[j] for i in range(len(groups)) for j in range(i)):raise ValueError('核心组非法或重叠')
  group_members=set().union(*groups) if groups else set()
  ga=sum(bool(g&given) for g in groups);gb=len(given-group_members-optional);gc=len(groups)-ga
  gtp+=ga;gfp+=gb;gfn+=gc
  ltp+=a;lfp+=b;lfn+=c;exact+=given==required
  gold=q['expected_state'];pred=p['state'];correct+=gold==pred;states[gold+'->'+pred]+=1
  tp+=gold=='risk' and pred=='risk';fp+=gold!='risk' and pred=='risk';fn+=gold=='risk' and pred!='risk'
  per.append(dict(query_id=qid,state_correct=gold==pred,reference_state=gold,predicted_state=pred,label_tp=a,label_fp=b,label_fn=c,
   strict_core_set_match=given==required,missing_required=sorted(required-given),unexpected_labels=sorted(given-required-optional),
   optional_predicted=sorted(given&optional),candidate_labels_not_scored=p['candidate_labels'],state_label_inconsistent=(pred!='risk' and bool(given)),
   core_group_tp=ga,core_group_fp=gb,core_group_fn=gc,mechanism_semantic_correct=None))
 n=len(master)
 return dict(n=n,state_accuracy=ratio(correct,n),risk_binary=prf(tp,fp,fn),labels=prf(ltp,lfp,lfn),core_label_groups=prf(gtp,gfp,gfn),
  strict_core_set_match_rate=ratio(exact,n),confusion=dict(states),per_query=per,semantic_mechanism_correctness=None,
  reference_status='frozen_model_silver_pending_human',candidate_labels_counted_as_definite=False,
  optional_labels_reward_tp=False,optional_labels_penalize_fp=False)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--dataset',type=Path,required=True);ap.add_argument('--predictions',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 master=rows(a.dataset/'master.jsonl');pred=rows(a.predictions);labels={r['risk_tag'] for r in json.loads((a.dataset/'official_labels.json').read_text(encoding='utf-8-sig'))}
 assert len(master)==90
 for p in pred:
  for key in ['trigger_quotes','needed_facts','citations']:
   if not isinstance(p.get(key),list):raise ValueError('缺完整输出字段'+key)
  for key in ['mechanism','explanation']:
   if not isinstance(p.get(key),str) or not p[key].strip():raise ValueError('缺解释字段'+key)
 report=score_predictions(master,pred,labels)
 docs={}
 for name in ['corpus.jsonl','reference_corpus.jsonl']:
  path=a.dataset/name
  if path.exists():
   for d in rows(path):
    if d['file_id'] in docs and docs[d['file_id']]!=d['text']:raise ValueError('来源同ID不同文本')
    docs[d['file_id']]=d['text']
 qm={q['query_id']:q for q in master};quotes=Counter();triggers=Counter()
 for p in pred:
  for t in p['trigger_quotes']:
   if not isinstance(t,str) or not t:raise ValueError('非法触发原文')
   triggers['present' if t in qm[p['query_id']]['text'] else 'absent']+=1
  for citation in p['citations']:
   if any(not isinstance(citation.get(k),str) or not citation[k].strip() for k in ['file_id','source_quote','claim','relation']) or citation['relation'] not in ['支持','对照']:raise ValueError('非法引用')
   if citation['file_id'] not in docs:quotes['unknown_source']+=1
   elif citation['source_quote'] in docs[citation['file_id']]:quotes['present']+=1
   else:quotes['absent']+=1
 report.update(trigger_literal_counts=dict(triggers),citation_literal_counts=dict(quotes),
  known_source_quote_exact_rate=ratio(quotes['present'],quotes['present']+quotes['absent']),
  citation_entailment=None,semantic_faithfulness=None,semantic_review_status='pending_independent_semantic_review',
  risk_model_inference_performed_by_this_tool=False)
 with a.output.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
 print(json.dumps({k:v for k,v in report.items() if k!='per_query'},ensure_ascii=False))

if __name__=='__main__':main()
