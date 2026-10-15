"""精确验证全部补充判断，排名未知的主会话样本与盲标比较。"""
from collections import Counter
from common import *
freeze_check('supplement_input_freeze.json');assigned={};annotations=[]
for i in [1,2,3]:
 docs=rows(OUT/f'supplement_inputs/part_{i}.jsonl');dm={d['file_id']:d for d in docs}
 expected={(q['query_id'],d['file_id']) for d in docs for q in d['queries']}
 p=WORK/f'supplement_annotations/part_{i}/decisions.jsonl'
 if p.exists():aa=rows(p)
 else:
  assert i==3
  aa=rows(WORK/'supplement_annotations/part_3/reviews.jsonl')
  # 容量中断前模型已写完全部120个显式语义判断；只补来源元数据，不改等级或证据。
  aa=[{**a,'source_text_sha256':dm[a['file_id']]['text_sha256'],'reviewer_id':'full_p3','human_approved':False,'origin':'model_source_review_full_pool','metadata_added_by_root_serializer':True} for a in aa]
  with p.open('x',encoding='utf-8') as f:
   for a in aa:f.write(json.dumps(a,ensure_ascii=False)+'\n')
 actual={(a['query_id'],a['file_id']) for a in aa};assert len(aa)==len(actual) and actual==expected,(i,len(actual),len(expected))
 for a in aa:
  d=dm[a['file_id']];assert type(a['grade']) is int and a['grade'] in [0,1,2,3] and a['human_approved'] is False
  assert a['source_text_sha256']==tsha(d['text'])==d['text_sha256'] and a['reason'] and a['limitation']
  assert not a['source_quote'] or a['source_quote'] in d['text']
  if a['grade']>=2:assert a['source_quote']
  assigned[a['query_id'],a['file_id']]=d
 annotations+=aa
assert len(annotations)==365;am={(r['query_id'],r['file_id']):r for r in annotations}
audits=read(WORK/'supplement_root_blind_audit.json')['decisions'];differences=[]
for a in audits:
 k=(a['query_id'],a['file_id']);d=assigned[k];assert not a['source_quote'] or a['source_quote'] in d['text']
 if a['grade']>=2:assert a['source_quote']
 if a['grade']!=am[k]['grade']:differences.append({'query_id':k[0],'file_id':k[1],'blind_grade':am[k]['grade'],'root_grade':a['grade'],'blind_opinion':am[k],'root_opinion':a,'raw_text':d['text']})
save('supplement_annotations_initial.jsonl',annotations,True)
save('supplement_root_audit_disagreements.jsonl',differences,True)
save('supplement_annotation_summary_initial.json',{'outside_pairs':365,'outside_documents':281,'grade_counts':dict(Counter(r['grade'] for r in annotations)),
 'root_blind_spotchecks':18,'root_agreement_count':18-len(differences),'differences':len(differences),'human_approved':False,
 'part3_capacity_interruption_after_all_120_semantic_rows_saved':True,'part3_metadata_wrapped_by_root_without_changing_semantics':True})
print(json.dumps(read(OUT/'supplement_annotation_summary_initial.json'),ensure_ascii=False))
for r in differences:print(json.dumps(r,ensure_ascii=False))
