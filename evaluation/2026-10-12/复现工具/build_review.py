"""Create an algorithm-blind document/context judgment pool from final Top5."""
import argparse
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS = ROOT / 'outputs/FinRisk_剩余全量准备_20261011/tasks'


def load_lines(path):
    return [json.loads(x) for x in Path(path).read_text(encoding='utf-8-sig').splitlines() if x.strip()]


def write_lines(path, rows):
    Path(path).write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows), encoding='utf-8')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--results', required=True)
    p.add_argument('--queries', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    queries = {r['query_id']: r for r in load_lines(args.queries)}
    results = load_lines(args.results)
    pool, provenance = {}, []
    seen_results = set()
    for result in results:
        identity = (result['corpus'], result['arm'], result['query_id'])
        assert identity not in seen_results, identity
        seen_results.add(identity)
        qid = result['query_id']
        for rank, hit in enumerate(result['files'][:5], 1):
            fid = hit['file_id']
            key = (qid, fid)
            if key not in pool:
                task = json.loads((TASKS / (fid + '.json')).read_text(encoding='utf-8-sig'))
                text = task['full_text']
                assert hashlib.sha256(text.encode()).hexdigest() == task['text_sha256']
                pool[key] = {'pair_id': 'J' + hashlib.sha256((qid + ':' + fid).encode()).hexdigest()[:12],
                             'query_id': qid, 'query_text': queries[qid]['text'], 'file_id': fid,
                             'full_source_text': text, 'source_sha256': task['text_sha256'], 'contexts': {}}
            row = pool[key]
            # Exact text determines the context identity; no method/rank/score leaks to judgments.
            text = hit['text']
            context_id = 'C' + hashlib.sha256(text.encode()).hexdigest()[:12]
            context = {'context_id': context_id, 'text': text, 'prefix': hit.get('prefix', ''),
                       'source_text': hit['source_text'], 'source_spans': hit['source_spans'],
                       'evidence_ambiguous': hit.get('evidence_ambiguous', False),
                       'prefix_evidence_ambiguous': hit.get('prefix_evidence_ambiguous', False),
                       'ambiguity_reason': hit.get('ambiguity_reason')}
            assert context['source_text'].strip()
            assert context['source_spans'], (qid, fid, hit['unit_id'])
            expected_text = context['prefix'] + '\n' + context['source_text'] if context['prefix'] else context['source_text']
            assert context['text'] == expected_text, (qid, fid, hit['unit_id'])
            for span in context['source_spans']:
                assert row['full_source_text'][span['start']:span['end']] == context['source_text']
            if context_id in row['contexts']:
                previous = row['contexts'][context_id]
                assert all(previous[k] == context[k] for k in ['text','prefix','source_text'])
                context['source_spans'] = [dict(start=s,end=e) for s,e in sorted({(s['start'],s['end'])
                    for s in previous['source_spans'] + context['source_spans']})]
                context['evidence_ambiguous'] |= previous['evidence_ambiguous']
                context['prefix_evidence_ambiguous'] |= previous['prefix_evidence_ambiguous']
                context['ambiguity_reason'] = context['ambiguity_reason'] or previous['ambiguity_reason']
            row['contexts'][context_id] = context
            provenance.append({'pair_id': row['pair_id'], 'context_id': context_id, 'query_id': qid,
                               'file_id': fid, 'corpus': result['corpus'], 'arm': result['arm'], 'rank': rank,
                               'unit_id': hit['unit_id']})
    rows = list(pool.values())
    random.Random(20261012).shuffle(rows)
    for row in rows:
        row['contexts'] = sorted(row['contexts'].values(), key=lambda x: x['context_id'])
    write_lines(out / 'blind_judgment_pool.jsonl', rows)
    write_lines(out / 'judgment_provenance.jsonl', provenance)
    # Preserve complete query groups, interleaved to balance query styles.
    for part in range(3):
        selected = [r for r in rows if (int(r['query_id'][1:]) - 1) % 3 == part]
        write_lines(out / f'judgment_part_{part+1}.jsonl', selected)
    summary = {'queries': len(queries), 'retrieval_results': len(results), 'unique_query_file_pairs': len(rows),
               'context_variants': sum(len(r['contexts']) for r in rows), 'top5_slots': len(provenance),
               'parts': [sum((int(r['query_id'][1:]) - 1) % 3 == n for r in rows) for n in range(3)],
               'input_sha256': {str(Path(x).resolve()): hashlib.sha256(Path(x).read_bytes()).hexdigest()
                                for x in [args.results, args.queries]},
               'blind_to_algorithm_and_rank': True, 'human_approved': False}
    (out / 'judgment_pool_manifest.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
