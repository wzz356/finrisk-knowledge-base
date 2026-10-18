import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
OUT = ROOT / 'outputs/FinRisk_知识库增量改进_20261018'
INDEX = ROOT / 'outputs/FinRisk_知识库V2_20261012/indexes/all9639_final/structured.jsonl'
SOURCE = ROOT / 'outputs/FinRisk_知识库V2_20261012/normalized_final/data/documents.jsonl'
PYTHON = Path('C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')


def rows(path):
    with Path(path).open(encoding='utf-8-sig') as f:
        return [json.loads(line) for line in f if line.strip()]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def tsha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(path, value, jl=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        if jl:
            for row in value:
                f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
        else:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def freeze_check(name='design_freeze.json'):
    frozen = read(OUT / name)
    for filename, expected in frozen['sha256'].items():
        if sha(filename) != expected:
            raise ValueError('frozen input changed: ' + filename)
    return sha(OUT / name)
