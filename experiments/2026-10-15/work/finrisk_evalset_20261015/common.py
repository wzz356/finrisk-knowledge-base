import hashlib,importlib.util,json,sys
from pathlib import Path
from datetime import datetime,timezone
WORK=Path(__file__).resolve().parent;ROOT=WORK.parents[1]
OUT=ROOT/'outputs/FinRisk_可用测试集_v1_20261015'
V2=ROOT/'outputs/FinRisk_知识库V2_20261012'
SOURCE=V2/'normalized_final/data/documents.jsonl'
INDEX=V2/'indexes/all9639_final/structured.jsonl'
sys.stdout.reconfigure(encoding='utf-8')
def rows(p):return list(iterrows(p))
def iterrows(p):
 with Path(p).open(encoding='utf-8-sig') as f:
  for line in f:
   if line.strip():yield json.loads(line)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def tsha(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def save(name,obj,jsonl=False):
 path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8',newline='\n') as f:
  if jsonl:
   for r in obj:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n')
  else:f.write(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def module(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def freeze_check(name='input_freeze.json'):
 for p,h in read(OUT/name)['sha256'].items():assert sha(p)==h,p
