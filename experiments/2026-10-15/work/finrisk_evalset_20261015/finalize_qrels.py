"""排名未读前裁定全部计分分歧，保留完整双轮和证据来源。"""
from collections import Counter
from common import *
freeze_check()
corpus=rows(OUT/'corpus.jsonl');cm={d['file_id']:d for d in corpus}
first=rows(OUT/'qrels_initial.jsonl');second=rows(OUT/'qrels_second_blind_review.jsonl')
key=lambda r:(r['query_id'],r['file_id'])
im={key(r):r for r in first};sm={key(r):r for r in second}
material={key(r) for r in rows(OUT/'review_disagreements_material.jsonl')}
aa=[]
for name in ['adjudications_part12.json','adjudications_part3.json']:
 a=read(WORK/name);assert a['human_approved'] is False;aa+=a['decisions']
am={key(a):a for a in aa};assert len(am)==len(aa)==25 and set(am)==material
assert set(im)==set(sm) and len(im)==2000
result=[]
for k,a in sorted(im.items()):
 b=sm[k];decision=am.get(k)
 if decision:
  chosen=a if decision['selected_evidence']=='initial' else b
  r={**chosen,'grade':decision['final_grade'],'root_reason':decision['root_reason'],
     'review_status':'root_adjudicated','selected_evidence':decision['selected_evidence']}
 else:
  assert a['grade']==b['grade'] or max(a['grade'],b['grade'])<2
  r={**a,'review_status':'two_blind_reviews_agree' if a['grade']==b['grade'] else '0_vs_1_retained_initial_both_count_zero'}
 r.update(initial_grade=a['grade'],second_grade=b['grade'],initial_reviewer_id=a['reviewer_id'],
          second_reviewer_id=b['reviewer_id'],human_approved=False,reference_origin='two_blind_model_reads_with_root_adjudication')
 if r['grade']>=2:assert r['source_quote'] and r['source_quote'] in cm[r['file_id']]['text']
 assert r['source_text_sha256']==cm[r['file_id']]['text_sha256']
 result.append(r)
save('qrels.jsonl',result,True);save('adjudication_log.jsonl',aa,True)
for name,mapper in [('qrels_direct.txt',lambda g:int(g==3)),('qrels_graded_levels.txt',lambda g:2 if g==3 else 1 if g==2 else 0),('qrels_graded_gain.txt',lambda g:3 if g==3 else 1 if g==2 else 0)]:
 with (OUT/name).open('x',encoding='utf-8',newline='\n') as f:
  for r in result:f.write(f"{r['query_id']} 0 {r['file_id']} {mapper(r['grade'])}\n")
per=[]
for q in rows(OUT/'query_specs.jsonl'):
 gg=[r['grade'] for r in result if r['query_id']==q['query_id']]
 per.append({'query_id':q['query_id'],'group':q['group'],'input_type':q['input_type'],'direct_count':gg.count(3),'partial_count':gg.count(2)})
save('reference_summary.json',{'queries':20,'documents':100,'pairs':2000,'grade_counts':dict(Counter(r['grade'] for r in result)),
 'per_query':per,'material_adjudicated':25,'topic_only_0_vs_1_retained_initial':45,'human_approved':False,
 'all_labels_explicit_not_default_zero':True,'rankings_not_read_before_reference_freeze':True})
paths=[OUT/n for n in ['qrels.jsonl','adjudication_log.jsonl','qrels_direct.txt','qrels_graded_levels.txt','qrels_graded_gain.txt','reference_summary.json','qrels_initial.jsonl','qrels_second_blind_review.jsonl','review_disagreements_all.jsonl','blind_review_summary.json','corpus.jsonl','queries.jsonl','query_specs.jsonl','标注规则.md']]
paths +=[WORK/n for n in ['adjudications_part12.json','adjudications_part3.json','finalize_qrels.py']]
save('qrels_freeze.json',{'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'human_approved':False,
 'rankings_not_read_before_freeze':True,'sha256':{str(p):sha(p) for p in paths}})
print(json.dumps(read(OUT/'reference_summary.json'),ensure_ascii=False))
