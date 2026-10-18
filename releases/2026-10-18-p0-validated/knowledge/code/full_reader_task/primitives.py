import gzip
import hashlib
import json
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def textsha(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def canonical_sha(value):return textsha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False))
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    path=Path(path)
    with (gzip.open if path.suffix=='.gz' else open)(path,'rt',encoding='utf-8-sig') as stream:
        for line in stream:
            if line.strip():yield json.loads(line)


def save(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
