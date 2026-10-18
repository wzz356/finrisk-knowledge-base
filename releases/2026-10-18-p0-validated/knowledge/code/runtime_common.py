"""Small stdlib helpers for the new runtime; no original-workspace fallback."""
import gzip
import hashlib
import json
from pathlib import Path

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def textsha(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def canonical_sha(value):return textsha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')))
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def rows(path):
    path=Path(path);opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def save(path,value,jl=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        if jl:
            for r in value:f.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
        else:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
