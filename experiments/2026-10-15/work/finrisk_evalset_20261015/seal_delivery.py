"""最终不可变清单；不覆盖旧成果，不封入凭据及重复解压目录。"""
import re
from common import *
for n in ['core_verification.json','retrieval_verification.json','final_verification.json','portable_verification.json']:assert read(OUT/n)['status']=='passed'
for n in ['input_freeze.json','candidate_freeze.json','api_freeze.json','qrels_freeze.json','prediction_freeze.json','supplement_input_freeze.json','supplement_qrels_freeze.json']:freeze_check(n)
portable=read(OUT/'portable_verification.json');assert sha(portable['zip_path'])==portable['zip_sha256']
for f in read(OUT/'dataset_manifest.json')['files']:
 p=OUT/f['path'];assert p.stat().st_size==f['bytes'] and sha(p)==f['sha256']
files=[]
for parent in [OUT,WORK]:
 for p in sorted(parent.rglob('*')):
  if not p.is_file() or '__pycache__' in p.parts or 'portable_verification' in p.parts or p.name=='delivery_manifest.json':continue
  files.append({'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)})
assert len(files)==len({f['path'] for f in files})
utc=datetime.now(timezone.utc);start=datetime(2026,10,14,18,2,tzinfo=timezone.utc)
save('delivery_manifest.json',{'schema_version':1,'status':'complete_verified','closed_queries':20,'closed_documents':100,'closed_qrels':2000,
 'full_ND_top20_judgments':400,'human_approved':False,'true_full_corpus_recall_available':False,
 'sealed_at_utc':utc.isoformat(),'elapsed_minutes_from_18_02_utc':(utc-start).total_seconds()/60,'deadline_met':utc<datetime(2026,10,14,23,2,tzinfo=timezone.utc),
 'portable_zip_sha256':portable['zip_sha256'],'excluded':['__pycache__','runtime duplicate portable_verification extraction directory'],
 'source_knowledge_base_unchanged':True,'GitHub_push_performed':False,'files':files})
for f in read(OUT/'delivery_manifest.json')['files']:
 p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and sha(p)==f['sha256']
assert read(OUT/'delivery_manifest.json')['deadline_met']
print(json.dumps({'status':'sealed_and_reverified','files':len(files),'bytes':sum(f['bytes'] for f in files),
 'elapsed_minutes':read(OUT/'delivery_manifest.json')['elapsed_minutes_from_18_02_utc'],'deadline_met':True,'manifest_sha256':sha(OUT/'delivery_manifest.json')},ensure_ascii=False))
