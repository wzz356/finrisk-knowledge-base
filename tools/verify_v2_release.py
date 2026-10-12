"""Verify the V2 public export, including restored original hashes; standard library."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
from v2_payloads import sha, safe_path, payload_chunks, verify_payload


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def plain_rows(path):
    with path.open(encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                yield number, json.loads(line)


def payload_rows(version, meta):
    remaining = b''
    for chunk in payload_chunks(version, meta):
        parts = (remaining + chunk).split(b'\n')
        remaining = parts.pop()
        for line in parts:
            if line.strip():
                yield json.loads(line)
    if remaining.strip():
        yield json.loads(remaining)


def main(repo):
    repo = Path(repo).resolve()
    version = repo / 'versions/v2-20261012'
    manifest = json.loads((version / 'publication_manifest.json').read_text(encoding='utf-8'))
    actual = {p.relative_to(version).as_posix() for p in version.rglob('*') if p.is_file()}
    assert actual == set(manifest['files']) | {'publication_manifest.json'}
    for name, meta in manifest['files'].items():
        path = safe_path(version, name)
        assert path.stat().st_size == meta['bytes'] and sha(path) == meta['sha256'], name
        assert path.stat().st_size <= 20 * 1024 * 1024, name
        assert path.suffix not in {'.sqlite3', '.sqlite', '.npy', '.pyc', '.safetensors', '.key', '.pem', '.pfx', '.p12'}, name
        assert not path.name.startswith('.env'), name
    maps = json.loads((version / 'payload_map.json').read_text(encoding='utf-8'))['payloads']
    payloads = {meta['path']: meta for meta in maps}
    assert len(payloads) == len(maps)
    for number, meta in enumerate(maps, 1):
        assert verify_payload(version, meta)
        if number % 25 == 0:
            print(json.dumps({'verified_original_payloads': number}), flush=True)
    print(json.dumps({'event': 'all_original_payload_hashes_verified', 'payloads': len(maps)}), flush=True)

    sources = {}
    for part in sorted((repo / 'data/sources').glob('part-*.jsonl')):
        for number, source in plain_rows(part):
            fid = source['file_id']
            assert fid not in sources
            assert hashlib.sha256(source['full_text'].encode('utf-8')).hexdigest() == source['text_sha256'], fid
            sources[fid] = {'text_sha256': source['text_sha256'], 'location': {'path': part.relative_to(repo).as_posix(), 'line': number}}
    bases = {}
    for part in sorted((repo / 'data/candidates').glob('part-*.jsonl')):
        for number, base in plain_rows(part):
            fid = base['file_id']
            assert fid not in bases
            assert hashlib.sha256(canonical(base['draft'])).hexdigest() == base['draft_json_sha256'], fid
            bases[fid] = {'draft_json_sha256': base['draft_json_sha256'], 'location': {'path': part.relative_to(repo).as_posix(), 'line': number}}
    with (repo / 'dictionary/risk_type_dictionary.csv').open(encoding='utf-8-sig', newline='') as stream:
        labels = {r['risk_tag'] for r in csv.DictReader(stream)}
    assert len(labels) == 27
    candidates, counts, changed = {}, collections.Counter(), 0
    for part in sorted((version / 'data/candidates').glob('part-*.jsonl')):
        for number, candidate in plain_rows(part):
            fid, draft = candidate['file_id'], candidate['draft']
            assert fid not in candidates and draft['file_id'] == fid
            digest = hashlib.sha256(canonical(draft)).hexdigest()
            assert digest == candidate['draft_json_sha256'], fid
            assert candidate['base_draft_json_sha256'] == bases[fid]['draft_json_sha256'], fid
            assert candidate['text_sha256'] == sources[fid]['text_sha256'], fid
            assert candidate['source'] == sources[fid]['location'] and candidate['base_candidate'] == bases[fid]['location'], fid
            assert candidate['semantic_status'] == 'candidate' and candidate['human_review_status'] == 'pending', fid
            assert candidate['overlay_applied'] == (digest != candidate['base_draft_json_sha256']), fid
            assert all(tag['tag'] in labels for b in draft['behaviors'] for tag in b.get('risk_tags', [])), fid
            changed += candidate['overlay_applied']
            counts.update(documents=1, cases=len(draft['cases']), behaviors=len(draft['behaviors']))
            candidates[fid] = {'digest': digest, 'location': {'path': part.relative_to(repo).as_posix(), 'line': number},
                               'text_sha256': candidate['text_sha256'], 'cases': len(draft['cases']), 'behaviors': len(draft['behaviors'])}
    assert set(candidates) == set(bases) == set(sources) and len(candidates) == 9639
    assert counts['cases'] == 15620 and counts['behaviors'] == 25186 and changed == 157
    index = [r for _, r in plain_rows(version / 'data/file_index.jsonl')]
    assert len(index) == len({r['file_id'] for r in index}) == 9639
    for entry in index:
        fid = entry['file_id']
        assert entry['candidate'] == candidates[fid]['location'] and entry['source'] == sources[fid]['location'], fid
        assert entry['draft_json_sha256'] == candidates[fid]['digest'], fid
        assert entry['cases'] == candidates[fid]['cases'] and entry['behaviors'] == candidates[fid]['behaviors'], fid
    snapshot_meta = payloads['normalized_final/extensions/candidate_snapshots.jsonl']
    for snapshot in payload_rows(version, snapshot_meta):
        assert snapshot['effective_draft_json_sha256'] == candidates[snapshot['file_id']]['digest']
    normal_manifest = json.loads((version / 'normalized_final/manifest.json').read_text(encoding='utf-8'))
    for relative, expected in normal_manifest['files'].items():
        packed = payloads['normalized_final/' + relative]
        assert packed['sha256'] == expected['sha256'] and packed['bytes'] == expected['bytes'], relative
    for prepared, expected_files, structured, raw, result in (
        ('same8509_final', 8509, 55686, 40170, 'same8509_final_results.jsonl'),
        ('all9639_final', 9639, 65475, 45403, 'all9639_results.jsonl'),
    ):
        pm = json.loads((version / 'indexes' / prepared / 'manifest.json').read_text(encoding='utf-8'))
        assert pm['source_files'] == expected_files and pm['status'] == 'complete'
        for name, count in (('structured', structured), ('raw', raw)):
            packed = payloads[f'indexes/{prepared}/{name}.jsonl']
            assert packed['sha256'] == pm['corpora'][name]['sha256'] and pm['corpora'][name]['count'] == count
        run = json.loads((version / 'retrieval' / (result + '.run.json')).read_text(encoding='utf-8'))
        assert run['status'] == 'complete' and run['output_sha256'] == payloads['retrieval/' + result]['sha256']
        results = list(payload_rows(version, payloads['retrieval/' + result]))
        assert len(results) == run['result_rows'] == 200
        assert len({r['query_id'] for r in results}) == 50
    metrics = json.loads((version / 'metrics/metrics.json').read_text(encoding='utf-8'))
    assert metrics['status'] == 'complete' and metrics['human_judgments'] == 0
    assert metrics['unique_query_file_pairs'] == 1000 and metrics['context_variants'] == 1670
    assert len(metrics['metrics']) == 14
    assertions = list(payload_rows(version, payloads['metrics/validated_judgments.jsonl']))
    assert len(assertions) == 1000 and sum(len(r['contexts']) for r in assertions) == 1670
    human = []
    for batch in ('batch_001', 'batch_002', 'batch_003'):
        human.extend(json.loads((version / 'human_acceptance' / batch / 'acceptance_records.json').read_text(encoding='utf-8'))['records'])
    assert len(human) == len({r['item_id'] for r in human}) == 9
    assert sum(r['decision'] == 'helpful' for r in human) == 2 and sum(r['decision'] == 'unrelated' for r in human) == 1
    for record in human:
        assert record['reviewer_kind'] == 'human' and record['full_document_approved'] is False
        if 'effective_draft_json_sha256' in record:
            assert record['effective_draft_json_sha256'] == candidates[record['file_id']]['digest']
    print(json.dumps({'status': 'passed', 'public_version_files': len(actual), 'original_payloads_verified': len(maps),
                      **dict(counts), 'changed_candidate_documents': changed, 'official_labels': 27,
                      'v2_result_records': 400, 'comparison_groups': 14, 'judged_pairs': 1000, 'judged_contexts': 1670,
                      'human_review_items': 9, 'human_approved_full_documents': 0}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    main(args.repo)
