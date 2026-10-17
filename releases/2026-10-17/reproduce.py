"""Read-only standard-library replay of the minimal delivery. No model or network."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs'
DATA = OUT / 'FinRisk_正式测试集V2_20261017'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def subprocess_json(script, *args):
    run = subprocess.run([sys.executable, '-S', '-X', 'utf8', '-B', str(script), *args],
                         capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    return json.loads(run.stdout)


def main():
    provenance = read(ROOT / 'selection_provenance.json')
    for item in provenance['copied_files']:
        path = ROOT / item['path']
        content = path.read_bytes()
        assert len(content) == item['bytes'] and hashlib.sha256(content).hexdigest() == item['sha256'], item['path']

    kb = OUT / 'FinRisk_知识库V2.1轻量收尾_20261015'
    kb_check = subprocess_json(kb / 'verify_release.py', '--release', str(kb))
    assert kb_check['status'] == 'passed'
    repository_index = ROOT.parents[1] / 'data/file_index.jsonl'
    if repository_index.exists():
        source_index = {r['file_id']: r for r in rows(repository_index)}
        candidates = rows(kb / 'file_index.jsonl')
        assert len(source_index) == len(candidates) == 9639
        assert all(r['text_sha256'] == source_index[r['file_id']]['text_sha256'] for r in candidates)
        source_dependency = '9639 source text hashes match existing repository index'
    else:
        source_dependency = 'standalone copy: obtain repository data/sources and data/file_index.jsonl for full source access'

    sys.path.insert(0, str(DATA / 'scripts'))
    from evaluate_formal_retrieval import evaluate
    labels = {r['risk_tag'] for r in read(DATA / 'official_labels.json')}
    master = rows(DATA / 'master.jsonl')
    assert len(master) == len(rows(DATA / 'queries.jsonl')) == 90
    risk_ids = {r['query_id'] for r in master if r['expected_state'] == 'risk'}
    closed = OUT / 'FinRisk_正式测试集V2_闭集实测_20261017'
    saved = read(closed / 'metrics_final.json')
    assert rows(closed / 'closed_queries.jsonl') == rows(DATA / 'closed_queries.jsonl')
    for method in ['BM25', 'BGE', 'RRF', 'DeepSeek']:
        actual = evaluate('closed', rows(DATA / 'closed_queries.jsonl'), rows(DATA / 'corpus.jsonl'),
                          rows(DATA / 'qrels_closed.jsonl'), rows(closed / f'rankings_{method}.jsonl'), risk_ids)
        assert actual == saved['methods'][method], method

    full = OUT / 'FinRisk_两层验证_20261017'
    assert rows(full / 'evaluation_reference/master.jsonl') == master
    full_check = subprocess_json(full / 'scripts/recompute_metrics.py')
    assert full_check['status'] == 'passed' and full_check['network_or_api_used'] is False

    sys.path.insert(0, str(ROOT / 'work/finrisk_regulation_quickfix_20261017'))
    from repair_pipeline import assemble
    from score_experiment import classification_metrics
    law = OUT / 'FinRisk_法规库V1_20261017'
    fix = OUT / 'FinRisk_法规库快速修复回归_20261017'
    refs = rows(fix / 'evaluation/references_unchanged.jsonl')
    assert refs == rows(law / 'experiment/confirm_references.jsonl') and len(refs) == 36
    metrics = read(fix / 'evaluation/metrics.json')
    for name, arm in [('old_case_A', 'A'), ('old_cards_C', 'C')]:
        predictions = {r['prediction']['query_id']: r['prediction']
                       for r in rows(law / f'experiment/resolved_predictions_{arm}.jsonl')}
        assert classification_metrics(refs, predictions, labels) == metrics[name]
    for phase in ['analysis', 'review']:
        models = rows(fix / f'model_outputs_{phase}.jsonl')
        assert len(models) == len({r['query_id'] for r in models}) == 36
        derived = [assemble(r['parsed']) for r in models]
        assert derived == rows(fix / f'predictions_{phase}.jsonl')
        raw = {r['query_id']: dict(state=r['parsed']['proposed_state'], risk_labels=r['parsed']['risk_labels']) for r in models}
        assert classification_metrics(refs, raw, labels) == metrics[phase + '_model_raw']
        assert classification_metrics(refs, {r['query_id']: r for r in derived}, labels) == metrics[phase + '_gated_normalized']

    print(json.dumps(dict(status='PASS', selected_original_payloads=len(provenance['copied_files']),
                         candidate_documents=9639, source_dependency=source_dependency,
                         formal_queries=90, closed_query_document_pairs=2400, closed_methods=4,
                         full_pool_methods=4, risk_predictions=180, regression_questions=36,
                         regression_metric_configurations=6, new_API_calls=0,
                         global_true_recall_claimed=False), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
