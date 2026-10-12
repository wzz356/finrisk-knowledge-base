"""Check actual run artifacts without changing retrieval or judgments."""
import collections
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/FinRisk_召回实验_20261012'
WORK = ROOT / 'work/finrisk_retrieval_20261012'


def read_lines(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    results = read_lines(OUT / 'retrieval_results.jsonl')
    queries = {q['query_id']: q for q in read_lines(OUT / 'queries.jsonl')}
    log = json.loads((OUT / 'retrieval_results.jsonl.run.json').read_text(encoding='utf-8'))
    manifest = json.loads((WORK / 'prepared_v2/manifest.json').read_text(encoding='utf-8'))
    assert log['status'] == 'complete' and log['result_rows'] == 300
    assert log['output_sha256'] == sha(OUT / 'retrieval_results.jsonl')
    assert log['queries_sha256'] == sha(OUT / 'queries.jsonl')
    assert log['runner_sha256'] == sha(WORK / 'runner.py')
    assert log['manifest_sha256'] == sha(WORK / 'prepared_v2/manifest.json')
    groups = {('structured', a) for a in ['bm25', 'dense', 'rrf', 'rrf_rerank']} | {('raw', a) for a in ['bm25', 'rrf_rerank']}
    assert len(results) == 300
    assert {(r['corpus'], r['arm'], r['query_id']) for r in results} == {(c, a, q) for c, a in groups for q in queries}
    units = {}
    for corpus in ['structured', 'raw']:
        path = WORK / f'prepared_v2/{corpus}.jsonl'
        assert sha(path) == manifest['corpora'][corpus]['sha256']
        units[corpus] = {u['unit_id']: u for u in read_lines(path)}
    sources, checks, short, aux, stage_counts = {}, 0, [], [], []
    for r in results:
        assert r['text'] == queries[r['query_id']]['text']
        stage_name = {'bm25': 'bm25', 'dense': 'dense', 'rrf': 'rrf_top100', 'rrf_rerank': 'rerank'}[r['arm']]
        stage = r['stages'][stage_name]
        for rows in r['stages'].values():
            assert len({h['unit_id'] for h in rows}) == len(rows)
            assert all(math.isfinite(h['score']) for h in rows)
            assert [h['rank'] for h in rows] == list(range(1, len(rows) + 1))
            assert all(a['score'] >= b['score'] for a, b in zip(rows, rows[1:]))
        stage_counts.append({'corpus': r['corpus'], 'arm': r['arm'], 'query_id': r['query_id'],
                             'units': len(stage), 'unique_files_in_final_units': len({units[r['corpus']][h['unit_id']]['file_id'] for h in stage}),
                             'returned_files': len(r['files']), 'returned_cases': len(r['cases'])})
        if 'rrf_union' in r['stages']:
            scores = collections.defaultdict(float)
            for route in ['bm25', 'dense']:
                for h in r['stages'][route]:
                    scores[h['unit_id']] += 1 / (60 + h['rank'])
            assert set(scores) == {h['unit_id'] for h in r['stages']['rrf_union']}
            for h in r['stages']['rrf_union']:
                assert abs(h['score'] - scores[h['unit_id']]) < 1e-12
        expected = collections.defaultdict(list)
        for h in stage:
            expected[units[r['corpus']][h['unit_id']]['file_id']].append(h['score'])
        assert len(r['files']) == min(20, len(expected))
        assert len({h['file_id'] for h in r['files']}) == len(r['files'])
        for h in r['files']:
            assert h['score'] == max(expected[h['file_id']])
            fid = h['file_id']
            if fid not in sources:
                task = json.loads((ROOT / 'outputs/FinRisk_剩余全量准备_20261011/tasks' / (fid + '.json')).read_text(encoding='utf-8-sig'))
                text = task['full_text']
                assert hashlib.sha256(text.encode()).hexdigest() == task['text_sha256']
                sources[fid] = text
            assert h['source_spans']
            for span in h['source_spans']:
                assert sources[fid][span['start']:span['end']] == h['source_text']
                checks += 1
            assert h['text'] == (h['prefix'] + '\n' if h['prefix'] else '') + h['source_text']
        assert all(not h['case_id'].endswith(':SOURCE') for h in r['cases'])
        if len(r['files']) < 5:
            short.append(stage_counts[-1])
    for c, a in sorted(groups):
        rows = [r for r in results if r['corpus'] == c and r['arm'] == a]
        eligible = [r for r in rows if queries[r['query_id']]['known_positive_file_ids']]
        summary = {'corpus': c, 'arm': a, 'queries': len(rows), 'known_source_queries': len(eligible),
                   'mean_returned_top20_files': statistics.mean(len(r['files']) for r in rows)}
        for k in [5, 10, 20]:
            summary[f'known_source_hit_at{k}'] = statistics.mean(bool(set(queries[r['query_id']]['known_positive_file_ids']) & {h['file_id'] for h in r['files'][:k]}) for r in eligible)
        aux.append(summary)
    audit = read_lines(OUT / 'retrieval_results.jsonl.token_audit.jsonl')
    assert len(audit) == 64109 + 20148 + 50 + 10000
    for a in audit:
        assert 0 < a['used_tokens'] <= a['max_length'] == 512
        assert a['truncated'] == (a['input_tokens'] > 512)
        assert a['input_tokens'] >= a['used_tokens']
        if a['stage'] == 'embedding':
            assert a['truncated_tokens'] == max(0, a['input_tokens'] - a['used_tokens'])
    token_groups = collections.defaultdict(list)
    for a in audit:
        token_groups[(a['stage'], a['corpus'], a.get('kind', 'pair'))].append(a)
    token_summary = [{'stage': k[0], 'corpus': k[1], 'kind': k[2], 'inputs': len(rows),
                      'truncated_inputs': sum(a['truncated'] for a in rows), 'max_input_tokens': max(a['input_tokens'] for a in rows)} for k, rows in sorted(token_groups.items())]
    vectors = []
    for event in log['models']['cache_events']:
        meta = json.loads((WORK / 'vector_cache' / (event['key'] + '.json')).read_text(encoding='utf-8'))
        path = WORK / 'vector_cache' / (event['key'] + '.npy')
        assert sha(path) == meta['npy_sha256']
        arr = np.load(path, allow_pickle=False)
        assert np.isfinite(arr).all() and arr.shape[1] == 512
        err = float(np.abs(np.linalg.norm(arr, axis=1) - 1).max())
        assert err < 1e-5
        vectors.append({'kind': event['kind'], 'corpus': event['corpus'], 'shape': list(arr.shape), 'max_l2_norm_error': err, 'cache_hit': event['hit'], 'seconds': event['seconds']})
    output = {'status': 'passed', 'result_rows': len(results), 'groups': len(groups), 'queries': len(queries),
              'source_files_checked': len(sources), 'exact_source_spans_checked': checks, 'token_inputs_checked': len(audit),
              'short_top5': short, 'token_summary': token_summary, 'vector_checks': vectors,
              'auxiliary_known_source_metrics': aux, 'stage_counts': stage_counts,
              'note': '完整性、来源和算法计算检查；不替代帮助度判断或人工验收。'}
    (OUT / '运行完整性检查.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in output.items() if k != 'stage_counts'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
