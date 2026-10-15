"""补充全文标签固定后，评实际Top20帮助；不改变闭集或假设全库分母。"""
import math
from fractions import Fraction
from collections import Counter
from common import *
freeze_check('qrels_freeze.json');freeze_check('prediction_freeze.json');freeze_check('supplement_input_freeze.json')
initial=rows(OUT/'supplement_annotations_initial.jsonl');root={(r['query_id'],r['file_id']):r for r in read(WORK/'supplement_root_blind_audit.json')['decisions']}
outside=[]
for a in initial:
 k=(a['query_id'],a['file_id']);r=root.get(k)
 if r:
  a={**a,**r,'blind_grade':a['grade'],'review_status':'root_random_spotcheck_agrees' if a['grade']==r['grade'] else 'root_adjudicated_boundary',
     'origin':'model_source_review_full_pool_root_spotcheck','human_approved':False}
 else:a={**a,'blind_grade':a['grade'],'review_status':'single_blind_model_read_not_root_spotchecked'}
 outside.append(a)
known={(r['query_id'],r['file_id']):r for r in rows(OUT/'qrels.jsonl')};om={(r['query_id'],r['file_id']):r for r in outside}
results=[r for r in rows(OUT/'all_results.jsonl') if r['scope']=='full9639' and r['stage']=='ND'];combined=[]
for r in results:
 assert len(r['file_ids'])>=20
 for fid in r['file_ids'][:20]:
  k=(r['query_id'],fid)
  a=om[k] if k in om else known[k]
  combined.append({**a,'supplement_scope':'actual_full9639_ND_top20','closed_reference_reused':k in known})
assert len(combined)==len({(r['query_id'],r['file_id']) for r in combined})==400
save('supplement_qrels.jsonl',combined,True)
docs={}
for i in [1,2,3]:
 for d in rows(OUT/f'supplement_inputs/part_{i}.jsonl'):docs[d['file_id']]={k:d[k] for k in ['file_id','text','text_sha256']}
save('supplement_corpus.jsonl',[docs[f] for f in sorted(docs)],True)
save('supplement_annotation_summary.json',{'annotated_pairs':400,'outside_pairs':365,'closed_reference_reused_pairs':35,'outside_documents':281,
 'grade_counts':dict(Counter(r['grade'] for r in combined)),'root_blind_spotcheck_pairs':18,'root_blind_grade_agreement':17,
 'root_adjudicated_pairs':1,'human_approved':False,'single_blind_pool_with_sample_audit':True})
paths=[OUT/n for n in ['supplement_qrels.jsonl','supplement_corpus.jsonl','supplement_annotation_summary.json','supplement_annotations_initial.jsonl','supplement_root_blind_audit_inputs.jsonl']]
paths +=[WORK/'supplement_root_blind_audit.json',WORK/'finalize_supplement.py']
paths +=[WORK/f'supplement_annotations/part_{i}/decisions.jsonl' for i in [1,2,3]]
save('supplement_qrels_freeze.json',{'before_supplement_metrics':True,'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'sha256':{str(p):sha(p) for p in paths}})
gm={(r['query_id'],r['file_id']):r['grade'] for r in combined};per=[]
for r in results:
 grades=[gm[r['query_id'],f] for f in r['file_ids'][:20]];first=next((i for i,g in enumerate(grades,1) if g==3),None)
 d={'query_id':r['query_id'],'top1_hit':grades[0]==3,'first_direct_rank_within20':first,
  'reciprocal_rank':str(Fraction(1,first) if first else Fraction()),'success20':first is not None,
  'ranked_file_ids':r['file_ids'][:20],'ranked_grades':grades}
 for k in [5,10,20]:d[f'precision{k}']=sum(g==3 for g in grades[:k])/k;d[f'direct_count{k}']=sum(g==3 for g in grades[:k])
 per.append(d)
summary={'queries':20,'top1_hit_count':sum(r['top1_hit'] for r in per),'top1_hit_rate':sum(r['top1_hit'] for r in per)/20,
 'mrr20':float(sum((Fraction(r['reciprocal_rank']) for r in per),Fraction())/20),'success20':sum(r['success20'] for r in per)/20,
 **{f'precision{k}':sum(r[f'precision{k}'] for r in per)/20 for k in [5,10,20]}}
save('full_ND_actual_helpfulness.json',{'scope':'full9639_actual_ND_top20','relevant':'grade3 only','summary':summary,'per_query':per,
 'true_global_recall_reported':False,'complete_global_NDCG_reported':False,'reason':'All returned top20 judged; all 9639 documents per query not exhaustively judged.'})
print(json.dumps({'supplement_labels':read(OUT/'supplement_annotation_summary.json'),'actual_full_top20_helpfulness':summary},ensure_ascii=False))
