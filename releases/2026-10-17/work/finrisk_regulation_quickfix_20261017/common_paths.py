"""Isolated repair paths; importing this module never reads a key or uses network."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
BASE=ROOT/'outputs/FinRisk_法规库V1_20261017'
OUT=ROOT/'outputs/FinRisk_法规库快速修复回归_20261017'
sys.path.insert(0,str(ROOT/'work/finrisk_regulation_v1'))


def rows(path):return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(data):return hashlib.sha256(data).hexdigest()


def save(path,value,jsonl=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        if jsonl:
            for row in value:f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
        else:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
