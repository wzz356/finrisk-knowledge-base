"""Read-only reconciliation of the completed registration against its frozen plan."""
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/FinRisk_知识库V2_20261012/registration_final'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def rows(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def connect(path):
    db = sqlite3.connect('file:' + Path(path).resolve().as_posix() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db


def run():
    summary = json.loads((OUT / 'registration_summary.json').read_text(encoding='utf-8'))
    assert summary['executed'] and summary['phase'] == 'registered_complete'
    plan = rows(OUT / 'registration_plan.jsonl')
    receipts = rows(OUT / 'registration_receipts.jsonl')
    assert len(plan) == len(receipts) == summary['registered_current'] == 8509
    assert len({r['file_id'] for r in plan}) == 8509
    assert sha(OUT / 'registration_plan.jsonl') == summary['registration_plan_sha256']
    assert sha(OUT / 'registration_receipts.jsonl') == summary['receipt_sha256']
    receipt_map = {r['file_id']: r for r in receipts}
    backups = json.loads((OUT / 'before_sqlite/backups.json').read_text(encoding='utf-8'))
    assert len(backups) == summary['prior_database_backups'] == 47
    backup_map = {r['batch_id']: r for r in backups}
    by_batch = defaultdict(list)
    for record in plan:
        by_batch[record['batch_id']].append(record)
    counts = Counter()
    statuses = Counter()
    revisions = Counter()
    old_proposals = old_reviews = new_proposals = 0
    for bid, expected in sorted(by_batch.items()):
        run_dir = ROOT / 'outputs/FinRisk_剩余全量运行_v2_20261011/runs' / bid
        with connect(run_dir / 'workflow.sqlite3') as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', bid
            jobs = {r['file_id']: dict(r) for r in db.execute('SELECT * FROM jobs')}
            assert set(jobs) == {r['file_id'] for r in expected}, bid
            config_sha = db.execute("SELECT value FROM metadata WHERE key='config_sha256'").fetchone()[0]
            assert sha(run_dir / 'config.json') == config_sha, bid
            if bid in backup_map:
                saved = backup_map[bid]
                assert sha(saved['backup_path']) == saved['backup_sha256'], bid
                with connect(saved['backup_path']) as before:
                    for table in ('metadata', 'batches', 'proposals', 'reviews', 'failed_receipts'):
                        prior = {tuple(r) for r in before.execute('SELECT * FROM ' + table)}
                        current = {tuple(r) for r in db.execute('SELECT * FROM ' + table)}
                        assert prior <= current, (bid, table)
                        if table != 'proposals':
                            assert prior == current, (bid, table, 'unexpected mutation')
                        if table == 'proposals':
                            old_proposals += len(prior)
                        elif table == 'reviews':
                            old_reviews += len(prior)
                    prior_jobs = {r['file_id']: dict(r) for r in before.execute('SELECT * FROM jobs')}
            else:
                prior_jobs = {}
                assert db.execute('SELECT COUNT(*) FROM reviews').fetchone()[0] == 0
            new_proposals += db.execute('SELECT COUNT(*) FROM proposals').fetchone()[0]
            for record in expected:
                fid = record['file_id']
                job = jobs[fid]
                receipt = receipt_map[fid]
                revision = record['target_revision']
                assert job['proposal_sha256'] == record['target_sha256'] == receipt['current_sha256'], fid
                assert job['revision'] == receipt['current_revision'] <= 2, fid
                assert sha(job['proposal_path']) == record['target_sha256'], fid
                assert sha(job['input_path']) == job['input_sha256'], fid
                task = json.loads(Path(job['input_path']).read_text(encoding='utf-8'))
                assert task['source_sha256'] == record['source_sha256'], fid
                assert task['text_sha256'] == record['text_sha256'], fid
                assert hashlib.sha256(task['full_text'].encode('utf-8')).hexdigest() == record['text_sha256'], fid
                assert record['semantic_status'] == 'candidate' and record['human_review_status'] == 'pending', fid
                if revision is None:
                    assert job == prior_jobs[fid], (fid, 'unchanged job mutated')
                    counts['already_current'] += 1
                else:
                    assert job['revision'] == revision, fid
                    assert job['review_path'] is None and job['review_sha256'] is None, fid
                    assert job['model_second_review_completed'] == 0, fid
                    counts['new' if record['previous_sha256'] is None else 'update'] += 1
                    if record['previous_sha256'] is not None:
                        assert prior_jobs[fid]['proposal_sha256'] == record['previous_sha256'], fid
                        assert revision == prior_jobs[fid]['revision'] + 1, fid
                statuses[job['status']] += 1
                revisions[str(job['revision'])] += 1
            # Prior proposal and review files are still present with the same recorded bytes.
            for table, path_key, sha_key in (
                ('proposals', 'proposal_path', 'proposal_sha256'),
                ('reviews', 'review_path', 'review_sha256'),
            ):
                for item in db.execute('SELECT * FROM ' + table):
                    assert sha(item[path_key]) == item[sha_key], (bid, table, item['file_id'])
        print(json.dumps({'verified_batch': bid, 'files': sum(counts.values())}), flush=True)
    assert dict(counts) == summary['counts']
    assert new_proposals == old_proposals + counts['new'] + counts['update']
    report = {
        'passed': True, 'files': 8509, 'databases': len(by_batch), 'counts': dict(counts),
        'current_revision_counts': dict(revisions), 'job_status_counts': dict(statuses),
        'prior_proposals_preserved': old_proposals, 'prior_reviews_preserved': old_reviews,
        'proposal_history_rows': new_proposals, 'backup_files_verified': 47,
        'source_input_and_proposal_byte_hashes_verified': True,
        'unchanged_jobs_byte_values_preserved': counts['already_current'],
        'new_and_changed_current_review_bindings_cleared': counts['new'] + counts['update'],
        'human_approved': 0,
        'scope': '8509 schedule; other 1130 candidates included in normalized 9639 table, not inserted into this legacy schedule',
        'registration_summary_sha256': sha(OUT / 'registration_summary.json'),
        'code_sha256': sha(__file__),
    }
    (OUT / 'registration_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    run()
