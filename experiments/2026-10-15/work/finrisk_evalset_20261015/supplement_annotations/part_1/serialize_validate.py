import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
source = ROOT / 'outputs/FinRisk_可用测试集_v1_20261015/supplement_inputs/part_1.jsonl'
docs = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
by_file = {doc['file_id']: doc for doc in docs}
expected = {(doc['file_id'], q['query_id']) for doc in docs for q in doc['queries']}
records = []
seen = set()
for path in sorted(HERE.glob('manual_*.json')):
    for file_id, query_id, grade, quote, reason, limitation in json.loads(path.read_text(encoding='utf-8')):
        pair = (file_id, query_id)
        assert pair in expected, pair
        assert pair not in seen, pair
        seen.add(pair)
        doc = by_file[file_id]
        sha = hashlib.sha256(doc['text'].encode('utf-8')).hexdigest()
        assert sha == doc['text_sha256'], file_id
        assert grade in (0, 1, 2, 3) and type(grade) is int, pair
        assert reason and limitation, pair
        assert (quote and quote in doc['text']) if grade >= 2 else (not quote or quote in doc['text']), pair
        records.append(dict(query_id=query_id, file_id=file_id, grade=grade, source_quote=quote, reason=reason, limitation=limitation, source_text_sha256=sha, reviewer_id='full_p1', human_approved=False, origin='model_source_review_full_pool'))
order = {(doc['file_id'], q['query_id']): (i, j) for i, doc in enumerate(docs) for j, q in enumerate(doc['queries'])}
records.sort(key=lambda r: order[(r['file_id'], r['query_id'])])
(HERE / 'decisions.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')
report = dict(assigned_documents=len(docs), assigned_pairs=len(expected), reviewed_pairs=len(records), grade_distribution=dict(sorted(collections.Counter(r['grade'] for r in records).items())), duplicate_pairs=0, unknown_pairs=0, missing_pairs=sorted(expected-seen), source_sha256_matches=True, quotes_are_exact_source_substrings=True, all_reasons_and_limitations_present=True, exact_coverage=seen==expected)
(HERE / 'validation_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='missing_pairs'}, ensure_ascii=False))
