"""纯数值四指标。未知全文标签默认拒绝，不把未评文件补0。"""
import math
from fractions import Fraction

def frac(v):return {'value':float(v),'fraction':str(v)}

def score(files,effective_levels,ks=(5,10,20),mrr_cutoff=20,reference_membership=False):
 files=list(files);ks=list(ks)
 if len(set(files))!=len(files):raise ValueError('文件排名重复')
 if any(not isinstance(f,str) or not f for f in files):raise ValueError('非法文件ID')
 if any(type(k) is not int or k<1 for k in [*ks,mrr_cutoff]) or len(ks)!=len(set(ks)):raise ValueError('非法K')
 if any(type(g) is not int or g not in [0,1,2] for g in effective_levels.values()):raise ValueError('有效等级只允许整数0/1/2')
 consumed=max([*ks,mrr_cutoff])
 if not reference_membership and any(f not in effective_levels for f in files[:consumed]):raise ValueError('评测范围内缺失标签')
 levels=[effective_levels.get(f,0) for f in files[:consumed]]
 positive={f for f,g in effective_levels.items() if g>0};first=next((i for i,g in enumerate(levels[:mrr_cutoff],1) if g>0),None)
 ideal=sorted(effective_levels.values(),reverse=True)
 out={'top1_hit':bool(levels and levels[0]>0),'reciprocal_rank':frac(Fraction(1,first) if first else Fraction()),
  'first_relevant_rank_within_cutoff':first,'mrr_cutoff':mrr_cutoff,'positive_reference_count':len(positive),
  'max_grade_known_count':sum(g==2 for g in effective_levels.values())}
 for k in ks:
  n=sum(g>0 for g in levels[:k]);dcg=sum((2**g-1)/math.log2(i+1) for i,g in enumerate(levels[:k],1))
  idcg=sum((2**g-1)/math.log2(i+1) for i,g in enumerate(ideal[:k],1))
  out[f'relevant_count{k}']=n;out[f'recall{k}']=frac(Fraction(n,len(positive))) if positive else None
  out[f'dcg{k}']=dcg;out[f'idcg{k}']=idcg;out[f'ndcg{k}']=dcg/idcg if idcg else None
  out[f'ideal_max_grade_saturated{k}']=out['max_grade_known_count']>=k
 return out

def aggregate(per_query,ks=(5,10,20)):
 if not per_query:raise ValueError('没有查询')
 n=len(per_query);mrr=sum((Fraction(r['reciprocal_rank']['fraction']) for r in per_query),Fraction())/n
 out={'queries':n,'top1_hit_count':sum(r['top1_hit'] for r in per_query),
  'top1_hit_rate':frac(Fraction(sum(r['top1_hit'] for r in per_query),n)),'mrr20':frac(mrr)}
 for k in ks:
  rr=[Fraction(r[f'recall{k}']['fraction']) for r in per_query if r[f'recall{k}'] is not None]
  nd=[r[f'ndcg{k}'] for r in per_query if r[f'ndcg{k}'] is not None]
  out[f'recall{k}']=frac(sum(rr,Fraction())/len(rr)) if rr else None;out[f'recall_valid_queries{k}']=len(rr)
  out[f'ndcg{k}']=sum(nd)/len(nd) if nd else None;out[f'ndcg_valid_queries{k}']=len(nd)
  out[f'max_grade_saturated_queries{k}']=sum(r[f'ideal_max_grade_saturated{k}'] for r in per_query)
 return out
