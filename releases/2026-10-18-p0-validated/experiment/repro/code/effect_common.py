"""Explicit paths and stdlib helpers for the frozen new36 experiment."""
import gzip
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[1]
OUT=ROOT/'outputs/FinRisk_P0效果验证_20261018'
RUNTIME=ROOT/'outputs/FinRisk_知识库P0修复_20261018'
DATA=RUNTIME/'evaluation_new36'
SEALED=ROOT/'outputs/FinRisk_知识组织增强_交付_20261018_v2'
V2=ROOT/'outputs/FinRisk_知识库V2_20261012'
SCOPE='finrisk-p0-effect-new36-20261018-v1'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def textsha(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def canonical_sha(v):return textsha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False))
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rows(p):
    p=Path(p)
    with (gzip.open if p.suffix=='.gz' else open)(p,'rt',encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def save(p,value,jl=False):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:
        if jl:
            for r in value:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
        else:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
def utc():return datetime.now(timezone.utc).isoformat()
def verify(pins):
    for path,digest in pins.items():
        if sha(path)!=digest:raise ValueError('frozen input changed: '+str(path))

def input_queries():
    qs=list(rows(DATA/'model_inputs.jsonl'))
    if len(qs)!=36 or any(set(q)!={'opaque_id','text'} or not isinstance(q['text'],str) or not q['text'].strip() for q in qs) or len({q['opaque_id'] for q in qs})!=36 or len({textsha(q['text']) for q in qs})!=36:raise ValueError('exact input-only new36 required')
    return qs
