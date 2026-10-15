"""主会话固定随机补充池抽查：暂不展示分片标签或排名。"""
import random
from common import *
freeze_check('supplement_input_freeze.json')
allpairs=[]
for i in [1,2,3]:
 for d in rows(OUT/f'supplement_inputs/part_{i}.jsonl'):
  for q in d['queries']:allpairs.append({'query_id':q['query_id'],'file_id':d['file_id'],'query_text':q['text'],'focus':q['focus'],'raw_text':d['text'],'text_sha256':d['text_sha256']})
assert len(allpairs)==365
rng=random.Random(2026101506);chosen=rng.sample(sorted(allpairs,key=lambda r:(r['query_id'],r['file_id'])),18)
save('supplement_root_blind_audit_inputs.jsonl',chosen,True)
print(json.dumps({'blind_audit_pairs':len(chosen)},ensure_ascii=False))
