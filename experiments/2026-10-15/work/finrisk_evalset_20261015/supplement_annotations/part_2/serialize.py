import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INPUT = ROOT / 'outputs/FinRisk_可用测试集_v1_20261015/supplement_inputs/part_2.jsonl'
OUT = Path(__file__).resolve().parent
rows = [json.loads(s) for s in INPUT.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
sources = {r['file_id']: r for r in rows}
assigned = {(r['file_id'], q['query_id']) for r in rows for q in r['queries']}
decisions = []
for batch in sorted(OUT.glob('batch_*.json')):
    for d in json.loads(batch.read_text(encoding='utf-8')):
        fid, qid, grade, quote, reason, limitation = d
        source = sources[fid]
        assert (fid, qid) in assigned, (fid, qid)
        assert type(grade) is int and 0 <= grade <= 3
        assert reason and limitation
        assert grade < 2 or quote
        assert not quote or quote in source['text'], (fid, qid, quote)
        sha = hashlib.sha256(source['text'].encode('utf-8')).hexdigest()
        assert sha == source['text_sha256'], fid
        decisions.append(dict(query_id=qid, file_id=fid, grade=grade,
                              source_quote=quote, reason=reason, limitation=limitation,
                              source_text_sha256=sha, reviewer_id='full_p2',
                              human_approved=False, origin='model_source_review_full_pool'))
seen = [(d['file_id'], d['query_id']) for d in decisions]
assert len(seen) == len(set(seen)), 'duplicate pairs'
missing = assigned - set(seen)
with (OUT / 'decisions.jsonl').open('w', encoding='utf-8', newline='\n') as f:
    for d in decisions:
        f.write(json.dumps(d, ensure_ascii=False) + '\n')
report = dict(assigned_documents=len(rows), assigned_pairs=len(assigned),
              annotated_pairs=len(decisions), grade_distribution=dict(collections.Counter(d['grade'] for d in decisions)),
              exact_coverage=not missing, missing_pairs=sorted(missing),
              duplicate_pairs=0, all_quotes_are_source_substrings=True,
              all_text_sha256_match=True, reviewer_id='full_p2', human_approved=False)
(OUT / 'validation_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='missing_pairs'}, ensure_ascii=False))
