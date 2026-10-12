"""Validate source-grounded judgments and compute help metrics over frozen Top5 pools."""
import argparse
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from build_review import load_lines, write_lines


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dcg(grades):
    return sum((2 ** grade - 1) / math.log2(rank + 2) for rank, grade in enumerate(grades))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--results', required=True)
    p.add_argument('--queries', required=True)
    p.add_argument('--review', required=True)
    p.add_argument('--judgments', nargs='+', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    pool_manifest = json.loads((Path(args.review)/'judgment_pool_manifest.json').read_text(encoding='utf-8'))
    for input_path in [args.results, args.queries]:
        assert pool_manifest['input_sha256'][str(Path(input_path).resolve())] == sha(input_path), input_path
    pool = {r['pair_id']: r for r in load_lines(Path(args.review) / 'blind_judgment_pool.jsonl')}
    judgments = {}
    quote_checks = 0
    for path in args.judgments:
        for row in load_lines(path):
            pid = row['pair_id']
            assert pid in pool and pid not in judgments, pid
            source = pool[pid]['full_source_text']
            assert type(row['help_grade']) is int and 0 <= row['help_grade'] <= 3, pid
            assert row['reason'].strip(), pid
            assert row['help_type'] in ['support', 'boundary', 'irrelevant'], pid
            assert row['mechanism_match'] in ['same','partial','different'], pid
            assert row['conditions_match'] in ['compatible','partial','conflict','unknown'], pid
            assert isinstance(row['limitations'], list) and all(isinstance(x,str) for x in row['limitations']), pid
            assert type(row['misleading_risk']) is bool, pid
            quote = row.get('source_quote', '')
            assert isinstance(quote, str) and (not quote or quote in source), (pid, quote)
            if row['help_grade'] >= 2:
                assert quote.strip(), pid
            quote_checks += bool(quote)
            contexts = {x['context_id']: x for x in pool[pid]['contexts']}
            context_judgments = {x['context_id']: x for x in row['contexts']}
            assert len(context_judgments) == len(row['contexts'])
            assert set(contexts) == set(context_judgments), pid
            for cid, j in context_judgments.items():
                assert type(j['help_grade']) is int and 0 <= j['help_grade'] <= 3, (pid, cid)
                assert j['reason'].strip(), (pid, cid)
                assert type(j['misleading_risk']) is bool, (pid, cid)
                q = j.get('evidence_quote', '')
                assert isinstance(q, str) and (not q or q in contexts[cid]['text']), (pid, cid, q)
                if j['help_grade'] >= 2:
                    assert q.strip(), (pid, cid)
                    assert q in source, (pid, cid, 'positive context evidence must occur in original source')
                quote_checks += bool(q)
            row['context_map'] = context_judgments
            judgments[pid] = row
    assert set(pool) == set(judgments), {'missing': sorted(set(pool)-set(judgments))[:20], 'counts': [len(pool), len(judgments)]}
    write_lines(out / 'validated_judgments.jsonl', [{k:v for k,v in r.items() if k != 'context_map'} for r in judgments.values()])
    queries = {q['query_id']: q for q in load_lines(args.queries)}
    lookup = {(p['query_id'], p['file_id']): pid for pid, p in pool.items()}
    provenance = load_lines(Path(args.review) / 'judgment_provenance.jsonl')
    contexts_for_slot = {(p['corpus'],p['arm'],p['query_id'],p['rank']):p['context_id'] for p in provenance}
    units_for_slot = {(p['corpus'],p['arm'],p['query_id'],p['rank']):p['unit_id'] for p in provenance}
    ideal = defaultdict(list)
    for pid, row in pool.items():
        ideal[row['query_id']].append(judgments[pid]['help_grade'])
    per_query, groups = [], defaultdict(list)
    results = load_lines(args.results)
    counts = Counter((r['corpus'], r['arm']) for r in results)
    assert len(queries) == 50
    assert len(results) == 300 and len(counts) == 6 and all(n == 50 for n in counts.values()), counts
    expected_groups = {('structured',a) for a in ['bm25','dense','rrf','rrf_rerank']} | {('raw',a) for a in ['bm25','rrf_rerank']}
    assert set(counts) == expected_groups, counts
    for identity in expected_groups:
        ids = [r['query_id'] for r in results if (r['corpus'],r['arm']) == identity]
        assert len(set(ids)) == 50 and set(ids) == set(queries), identity
    for result in results:
        corpus, arm, qid = result['corpus'], result['arm'], result['query_id']
        assert result['text'] == queries[qid]['text'], qid
        assert len({x['file_id'] for x in result['files']}) == len(result['files'])
        grades, context_grades, risky, context_risky = [], [], [], []
        details = []
        for rank, hit in enumerate(result['files'][:5], 1):
            pid = lookup[(qid, hit['file_id'])]
            j = judgments[pid]
            cid = contexts_for_slot[(corpus, arm, qid, rank)]
            assert units_for_slot[(corpus, arm, qid, rank)] == hit['unit_id']
            c = j['context_map'][cid]
            grades.append(j['help_grade'])
            context_grades.append(c['help_grade'])
            risky.append(int(j['misleading_risk']))
            context_risky.append(int(c['misleading_risk']))
            details.append({'rank':rank,'file_id':hit['file_id'],'pair_id':pid,'context_id':cid,
                            'help_grade':j['help_grade'],'context_help_grade':c['help_grade'],
                            'reason':j['reason'],'context_reason':c['reason'],
                            'source_quote':j.get('source_quote',''),'limitations':j.get('limitations',[])})
        grades += [0] * (5-len(grades))
        context_grades += [0] * (5-len(context_grades))
        denominator = dcg(sorted(ideal[qid],reverse=True)[:5])
        row = {'corpus':corpus,'arm':arm,'query_id':qid,'query_text':queries[qid]['text'],
               'group':queries[qid]['group'],'returned_files':len(result['files'][:5]),
               'useful_at5':sum(g>=2 for g in grades)/5,'support_coverage_at5':int(any(g>=2 for g in grades)),
               'strong_coverage_at5':int(any(g==3 for g in grades)),'mean_help_at5':sum(grades)/5,
               'pool_ndcg_at5':dcg(grades)/denominator if denominator else None,
               'context_useful_at5':sum(g>=2 for g in context_grades)/5,
               'context_coverage_at5':int(any(g>=2 for g in context_grades)),
               'mean_context_help_at5':sum(context_grades)/5,'misleading_at5':sum(risky)/5,
               'context_misleading_at5':sum(context_risky)/5,'top5':details,'timing':result.get('timing',{})}
        positives = set(queries[qid]['known_positive_file_ids'])
        if positives:
            hits = [h['file_id'] for h in result['files'][:20]]
            for k in [5,10,20]:
                row[f'known_source_hit_at{k}'] = int(bool(positives.intersection(hits[:k])))
            first = next((i+1 for i,h in enumerate(hits) if h in positives),None)
            row['known_source_rr_at20'] = 1/first if first else 0
        per_query.append(row)
        groups[(corpus,arm)].append(row)
    main_metrics = ['useful_at5','support_coverage_at5','strong_coverage_at5','mean_help_at5','pool_ndcg_at5',
                    'context_useful_at5','context_coverage_at5','mean_context_help_at5','misleading_at5','context_misleading_at5']
    aux_metrics = ['known_source_hit_at5','known_source_hit_at10','known_source_hit_at20','known_source_rr_at20']
    aggregate = []
    for (corpus,arm),rows in sorted(groups.items()):
        summary = {'corpus':corpus,'arm':arm,'queries':len(rows),'actual_top5_slots':sum(r['returned_files'] for r in rows)}
        for key in main_metrics+aux_metrics:
            values = [r[key] for r in rows if r.get(key) is not None]
            summary[key] = statistics.mean(values) if values else None
            summary[key+'_n'] = len(values)
        summary['by_group'] = {}
        for group in sorted(set(r['group'] for r in rows)):
            sub = [r for r in rows if r['group']==group]
            summary['by_group'][group] = {'n':len(sub),**{m:statistics.mean(r[m] for r in sub) for m in main_metrics if m!='pool_ndcg_at5'}}
        for stage in ['bm25_seconds','dense_seconds','rrf_seconds','rerank_seconds']:
            values = [r['timing'][stage] for r in rows if stage in r['timing']]
            summary['mean_'+stage] = statistics.mean(values) if values else None
        aggregate.append(summary)
    summary = {'status':'complete','evaluation':'model_assisted_algorithm_blind_pool_judgments',
               'human_approved':False,'queries':len(queries),'unique_query_file_pairs':len(pool),
               'context_variants':sum(len(p['contexts']) for p in pool.values()),'exact_quote_checks':quote_checks,
               'metrics':aggregate,'input_sha256':{str(Path(p).resolve()):sha(p) for p in [args.results,args.queries,*args.judgments]}}
    (out/'metrics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write_lines(out/'per_query_metrics.jsonl',per_query)
    print(json.dumps({'status':'complete','pairs':len(pool),'queries':len(queries),'metrics':aggregate},ensure_ascii=False))


if __name__ == '__main__':
    main()
