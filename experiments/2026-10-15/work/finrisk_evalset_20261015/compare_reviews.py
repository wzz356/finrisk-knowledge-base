"""与独立复读比较，只有分歧进入主会话裁定；不读取检索排名。"""
from collections import Counter
import sys
from common import *
from labels import validate_decisions
freeze_check();corpus=rows(OUT/'corpus.jsonl');qs=rows(OUT/'query_specs.jsonl');cm={d['file_id']:d for d in corpus}
partial=len(sys.argv)>1 and sys.argv[1]=='partial12';suffix='_part12' if partial else ''
initial=rows(OUT/'annotation_decisions_initial.jsonl');im={d['file_id']:d for d in initial};reviews=[]
for i in ([1,2] if partial else [1,2,3]):
 dd=rows(WORK/f'reviews/part_{i}/decisions.jsonl');validate_decisions(dd,rows(OUT/f'annotation_inputs/part_{i}.jsonl'),qs);reviews+=dd
rm={d['file_id']:d for d in reviews};flat=validate_decisions(reviews,[c for c in corpus if c['file_id'] in rm],qs)
save('qrels_second_blind_review'+suffix+'.jsonl',flat,True)
conflicts=[];all_disagree=[]
for fid,first in im.items():
 if fid not in rm:continue
 second=rm[fid]
 for qi,q in enumerate(qs):
  a,b=first['grades'][qi],second['grades'][qi]
  if a!=b:
   entry={'query_id':q['query_id'],'file_id':fid,'text':q['text'],'focus':q['focus'],
    'grade_initial':a,'grade_second':b,'initial_evidence':first['evidence'].get(q['query_id']),
    'second_evidence':second['evidence'].get(q['query_id']),
    'initial_summary':first['document_mechanism_summary'],'second_summary':second['document_mechanism_summary'],
    'raw_text':cm[fid]['text']}
   all_disagree.append(entry)
   if max(a,b)>=2:conflicts.append(entry)
save('review_disagreements_all'+suffix+'.jsonl',all_disagree,True);save('review_disagreements_material'+suffix+'.jsonl',conflicts,True)
total=len(flat)
save('blind_review_summary'+suffix+'.json',{'pairs':total,'exact_agreement_count':total-len(all_disagree),
 'exact_agreement_rate':(total-len(all_disagree))/total,'material_disagreements':len(conflicts),
 'non_direct_topic_only_disagreements':len(all_disagree)-len(conflicts),
 'second_grade_counts':dict(Counter(r['grade'] for r in flat)),'both_model_not_human':True,
 'rankings_not_opened_for_adjudication':True})
print(json.dumps(read(OUT/('blind_review_summary'+suffix+'.json')),ensure_ascii=False))
