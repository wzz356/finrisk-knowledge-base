"""合并显式矩阵；生成排名未知时的全文复核材料。"""
from collections import Counter
from common import *
from labels import validate_decisions
freeze_check();corpus=rows(OUT/'corpus.jsonl');qs=rows(OUT/'query_specs.jsonl');decisions=[]
for i in [1,2,3]:
 source=WORK/f'annotations/part_{i}/decisions.jsonl';shard=rows(OUT/f'annotation_inputs/part_{i}.jsonl')
 dd=rows(source);assert {d['file_id'] for d in dd}=={d['file_id'] for d in shard}
 validate_decisions(dd,shard,qs);decisions+=dd
assert len(decisions)==100
flat=validate_decisions(decisions,corpus,qs);assert len(flat)==2000
save('annotation_decisions_initial.jsonl',sorted(decisions,key=lambda d:d['file_id']),True)
save('qrels_initial.jsonl',flat,True)
counts=Counter(r['grade'] for r in flat)
save('initial_annotation_summary.json',{'documents':100,'queries':20,'pairs':2000,'grade_counts':dict(counts),
 'per_query_direct_counts':{q['query_id']:sum(r['query_id']==q['query_id'] and r['grade']==3 for r in flat) for q in qs},
 'model_generated_not_human_gold':True,'ranking_not_used_for_labels':True})
cm={d['file_id']:d for d in corpus};review=[]
for d in sorted(decisions,key=lambda d:d['file_id']):
 if any(g>=2 for g in d['grades']):review.append({'file_id':d['file_id'],'text':cm[d['file_id']]['text'],
  'summary':d['document_mechanism_summary'],'grades':d['grades'],'evidence':d['evidence']})
save('root_review_inputs.jsonl',review,True)
print(json.dumps({'status':'merged','pairs':2000,'grade_counts':dict(counts),'review_documents':len(review)},ensure_ascii=False))
