"""Freeze only successful V2 artifacts and verify their saved dependency hashes."""
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/FinRisk_知识库V2_20261012'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rows(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run():
    inputs = load(OUT / 'quality/input_freeze.json')
    assert inputs['candidate_files'] == inputs['counts']['pass'] == 9639
    assert sha(OUT / 'quality/effective_overlays.jsonl') == inputs['overlay_file_sha256']
    assert sha(OUT / 'quality/mechanical_checks_final.jsonl') == inputs['final_checks_sha256']
    assert len(rows(OUT / 'quality/mechanical_checks_final.jsonl')) == 9639
    for path in ('normalized_final/verification.json', 'recovery/recovery_report.json',
                 'registration_final/registration_verification.json'):
        assert load(OUT / path)['passed'], path
    metrics = load(OUT / 'metrics/metrics.json')
    assert metrics['status'] == 'complete' and metrics['human_judgments'] == 0
    assert len(metrics['metrics']) == 14 and all(r['queries'] == 50 for r in metrics['metrics'])
    groups = Counter((r['variant'], r['corpus'], r['arm']) for r in rows(OUT / 'metrics/per_query_metrics.jsonl'))
    assert len(groups) == 14 and set(groups.values()) == {50}
    merged = rows(OUT / 'metrics/validated_judgments.jsonl')
    assert len(merged) == 1000 and sum(len(r['contexts']) for r in merged) == 1670
    # SHA checks saved inputs, frozen V1 score caches, and both completed V2 results.
    bindings = load(OUT / 'metrics/judgment_merge_manifest.json')['input_sha256']
    for path, digest in bindings.items():
        assert sha(path) == digest, path
    print(json.dumps({'stage': 'metric_dependencies_verified', 'files': len(bindings)}), flush=True)
    for prepared, name in (('same8509_final', 'same8509_final_results.jsonl'),
                           ('all9639_final', 'all9639_results.jsonl')):
        manifest = load(OUT / 'indexes' / prepared / 'manifest.json')
        runlog = load(OUT / 'retrieval' / (name + '.run.json'))
        assert manifest['status'] == runlog['status'] == 'complete'
        assert runlog['result_rows'] == len(rows(OUT / 'retrieval' / name)) == 200
        assert sha(OUT / 'retrieval' / name) == runlog['output_sha256']
        assert sha(OUT / 'indexes' / prepared / 'manifest.json') == runlog['manifest_sha256']
        for corpus in manifest['corpora'].values():
            assert sha(corpus['path']) == corpus['sha256'], corpus['path']
    repository = ROOT / 'finrisk-knowledge-base'
    commit = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', 'HEAD'], text=True).strip()
    status = subprocess.check_output(['git', '-C', str(repository), 'status', '--porcelain'], text=True).strip()
    assert commit == '1c39e3fdc30281022b8c6216ce463f4ffc46eefc' and not status
    # These are the only selected deliverable trees; failed/partial runs are audit references.
    directories = ['normalized_final', 'indexes/same8509_final', 'indexes/all9639_final',
                   'metrics', 'registration_final', 'evaluation/all_pool', 'quality/人工验收材料']
    selected = set()
    for directory in directories:
        selected.update(p for p in (OUT / directory).rglob('*') if p.is_file())
    for relative in ['quality/input_freeze.json', 'quality/effective_overlays.jsonl',
                     'quality/mechanical_checks_final.jsonl', 'evaluation/new_judgments.jsonl',
                     'evaluation/new_judgments.provenance.json', 'recovery/recovery_report.json',
                     'V2重建与召回复测报告.md', '人工验收入口.md', '任务清单状态_V2.md']:
        selected.add(OUT / relative)
    for name in ('same8509_final_results.jsonl', 'all9639_results.jsonl'):
        selected.update(OUT / 'retrieval' / (name + suffix) for suffix in ('', '.run.json', '.token_audit.jsonl'))
    # Exact sources and specification/quality audit notes are frozen alongside the data.
    implementation = ROOT / 'work/finrisk_v2_20261012'
    selected.update(p for p in implementation.glob('*') if p.suffix in ('.py', '.md'))
    selected.update(p for p in (ROOT / 'work/finrisk_v2_frozen8509_gpu').glob('*.py'))
    selected.update(p for p in (implementation / 'judgments').rglob('*') if p.is_file() and p.suffix in ('.py', '.json', '.jsonl', '.md'))
    selected.update(p for p in (implementation / 'quality').rglob('*') if p.is_file() and p.suffix in ('.py', '.json', '.jsonl', '.md'))
    files = []
    for path in sorted(selected):
        assert path.is_file(), path
        files.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)})
    # Check local Markdown links in the delivered user-facing reports.
    links = 0
    for name in ('V2重建与召回复测报告.md', '人工验收入口.md', '任务清单状态_V2.md'):
        path = OUT / name
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if target.startswith(('https://', 'http://', '#')):
                continue
            assert (path.parent / target).is_file(), (name, target)
            links += 1
    save(OUT / 'delivery_manifest.json', {
        'version': 'FinRisk-offline-candidate-v2-20261012',
        'status': 'offline_candidate_delivery', 'source_files': 9639,
        'human_approved': 0, 'human_review_status': 'pending', 'approved_scope': [],
        'application_default_switched': False, 'v2_published_to_github': False,
        'v1_commit_preserved': commit, 'v1_repository_worktree_clean': True,
        'registration_scope': 'remaining8509', 'registration_source_files': 8509,
        'other_1130_included_in_normalized_tables': True,
        'retrieval_quality': 'BM25 improved on model-reviewed development set; RRF/rerank regressed',
        'files': files, 'file_count': len(files), 'total_bytes': sum(r['bytes'] for r in files),
        'code_and_metadata_use_workspace_relative_paths': True,
        'audit_not_success': ['registration/', 'normalized/', 'indexes/same8509/', 'indexes/all9639/',
                              'retrieval/same8509_results.jsonl.partial'],
        'external_dependencies': 'Local frozen Python/GPU environments, tokenizer, BGE/reranker weights and V1 baseline dependencies; paths and hashes saved in run manifests. Not an independent-machine installer.',
        'semantic_limits': ['mechanical PASS is not semantic approval', 'old attention queue not fully source-reviewed',
                            'model judgments are not human gold', '50 development queries only',
                            'responsibility_relations table empty', 'no global event gold set',
                            '16 useful-context / non-useful-file threshold disagreements preserved'],
    })
    report = {'passed': True, 'frozen_files': len(files), 'total_bytes': sum(r['bytes'] for r in files),
              'metric_dependency_files_checked': len(bindings), 'metric_groups': 14, 'result_records': 700,
              'judged_query_file_pairs': 1000, 'judged_contexts': 1670,
              'v2_successful_result_records': 400, 'local_report_links_checked': links,
              'v1_clean_and_commit_unchanged': True, 'human_approved': 0,
              'delivery_manifest_sha256': sha(OUT / 'delivery_manifest.json'), 'code_sha256': sha(__file__)}
    save(OUT / 'delivery_verification.json', report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    run()
