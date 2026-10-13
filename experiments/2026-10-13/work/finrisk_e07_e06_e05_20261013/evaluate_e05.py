"""Build configuration-hidden reading packs; validate manually authored judgments."""
import argparse
from collections import Counter, defaultdict
from e07 import OUT, demo


def pool():
    records = demo.rows(OUT / 'e05_results.jsonl')
    if len(records) != 48 or len({(r['query_id'], r['arm']) for r in records}) != 48:
        raise ValueError('Requires complete 16 x 3 results')
    sources = demo.source_map()
    items, assignments = {}, []
    for record in records:
        packet = demo.make_packet({'query_id':record['query_id'],'text':record['text']},record['top5'],sources)
        for position, hit in enumerate(packet['evidence'],1):
            item = dict(query_id=record['query_id'], query_text=record['text'], file_id=hit['file_id'],
                unit_id=hit['unit_id'], displayed_text=hit['text'],
                source_segments=hit['source_segments'], source_sha256=hit['source_text_sha256'],
                displayed_text_sha256=hit['displayed_text_sha256'])
            item_id = 'J:' + demo.sha_json(item)
            item['item_id'] = item_id
            items[item_id] = item
            assignments.append(dict(arm=record['arm'],query_id=record['query_id'],position=position,
                                    item_id=item_id,file_id=hit['file_id'],unit_id=hit['unit_id']))
    ordered = sorted(items.values(),key=lambda i:(i['query_id'],i['item_id']))
    demo.write_new(OUT / 'e05_reading_pool.jsonl',ordered,True)
    demo.write_new(OUT / 'e05_reading_assignments.jsonl',assignments,True)
    for part,lo,hi in ((1,1,8),(2,9,16)):
        demo.write_new(OUT / f'e05_reading_part{part}.jsonl',
            [i for i in ordered if lo <= int(i['query_id'][1:]) <= hi],True)
    contract = ('本轮统一新判读；只评实际显示片段对输入风险判别有无具体帮助。direct为机制直接匹配，'
        'partial可为具体条件/相反边界核查，需说明差异；泛泛案由、仅证据清单、无具体机制的邻近主题不算有用。'
        'helpful=true必须有显示中连续逐字引文，且在一个实际原文segment内。不得由处罚反推本输入违规，'
        '不得跨主体/产品/历史条件无条件外推。看不出事实就保留限制。'
        '不得读取配置映射、原V3判断、E05结果/成绩或导航节点；作者与评者均为模型，输入已曝光，不能称独立人工盲测。'
        '输出每item一条item_id/item_sha256/helpful/relation/quote/reason/warnings/origin/human_approved。\n')
    with (OUT / 'e05_reading_contract.md').open('x',encoding='utf-8') as handle:handle.write(contract)
    print({'positions':len(assignments),'unique_contexts':len(items),'part_counts':[
        sum(1 for i in ordered if 1<=int(i['query_id'][1:])<=8),
        sum(1 for i in ordered if 9<=int(i['query_id'][1:])<=16)]})


def finish():
    items={i['item_id']:i for i in demo.rows(OUT / 'e05_reading_pool.jsonl')}
    judged=[]
    for p in (1,2):judged+=demo.rows(OUT / f'e05_judgments_part{p}.jsonl')
    if len(judged)!=len(items) or len({j['item_id'] for j in judged})!=len(items) or set(j['item_id'] for j in judged)!=set(items):
        raise ValueError('Missing/duplicate/extra judgment')
    for j in judged:
        item=items[j['item_id']]
        if j['item_sha256']!=demo.sha_json(item) or type(j['helpful']) is not bool or j['human_approved'] is not False:
            raise ValueError('Judgment binding/approval mismatch')
        if j['relation'] not in ('direct','partial','irrelevant') or not j['reason'] or not isinstance(j['warnings'],list):
            raise ValueError('Invalid judgment fields')
        if j['origin']!='current_session_model':raise ValueError('Invalid author provenance')
        if j['helpful'] and (not j['quote'] or j['quote'] not in item['displayed_text'] or not any(j['quote'] in s['text'] for s in item['source_segments'])):
            raise ValueError('Helpful quote not a continuous displayed source quote: '+j['item_id'])
        if j['relation']=='irrelevant' and j['helpful']:raise ValueError('Contradictory helpful relation')
    by_id={j['item_id']:j for j in judged}
    assignments=demo.rows(OUT / 'e05_reading_assignments.jsonl')
    groups=defaultdict(list)
    for a in assignments:groups[a['arm']].append((a,by_id[a['item_id']]))
    metrics={}
    for arm,pairs in groups.items():
        qs=defaultdict(list)
        for a,j in pairs:qs[a['query_id']].append(j)
        metrics[arm]=dict(positions=len(pairs),helpful=sum(j['helpful'] for _,j in pairs),
            covered_queries=sum(any(j['helpful'] for j in js) for js in qs.values()),
            direct_helpful=sum(j['helpful'] and j['relation']=='direct' for _,j in pairs),
            partial_helpful=sum(j['helpful'] and j['relation']=='partial' for _,j in pairs),
            per_query={qid:sum(j['helpful'] for j in js) for qid,js in sorted(qs.items())})
    results=demo.rows(OUT / 'e05_results.jsonl')
    base={r['query_id']:r for r in results if r['arm']=='B0'}
    doses={}
    for arm in ('B0','DIR','TREE'):
        rows=[r for r in results if r['arm']==arm]
        doses[arm]=dict(queries_with_node_hits=sum(r['dose']['node_top100_hits']>0 for r in rows),
            total_node_hits=sum(r['dose']['node_top100_hits'] for r in rows),
            accepted_expansions=sum(r['dose']['accepted_expansions'] for r in rows),
            leaf_rerank_candidates=sum(r['dose']['leaf_rerank_candidates'] for r in rows),
            leaf_top5_positions=sum(len(r['dose']['leaf_top5_units']) for r in rows),
            changed_file_lists=[r['query_id'] for r in rows if [h['file_id'] for h in r['top5']]!=[h['file_id'] for h in base[r['query_id']]['top5']]],
            changed_context_lists=[r['query_id'] for r in rows if [(h['file_id'],h['unit_id'],h['text']) for h in r['top5']]!=[(h['file_id'],h['unit_id'],h['text']) for h in base[r['query_id']]['top5']]])
    run=demo.read_json(OUT / 'e05_results.jsonl.run.json')
    score_pool=demo.rows(OUT / 'e05_results.jsonl.score_pool.jsonl')
    demo.write_new(OUT / 'e05_all_judgments.jsonl',judged,True)
    demo.write_new(OUT / 'e05_metrics.json',dict(status='complete_exploratory_replay',human_approved=False,
        queries=16,arms=metrics,navigation_dose=doses,unique_judgments=len(judged),positions=len(assignments),
        actual_gpu_seconds=run['elapsed_seconds'],
        actual_new_rerank_pairs=sum(p['provenance']['kind']=='actual_local_gpu_rerank' for p in score_pool),
        exact_shared_rerank_pairs=sum(r['timing']['reused_units'] for r in results),
        results_sha256=demo.sha_file(OUT / 'e05_results.jsonl'),judgments_sha256=demo.sha_json(judged),
        limitations=['16 inputs exposed before experiment','model review, not independent human gold',
            '21 reviewed leaves, full corpus competition','DIR6 versus TREE7 differs in content and count',
            'hard spherical clustering variant, not UMAP/GMM soft clustering','navigation summaries not final evidence']))
    print(metrics)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['pool','finish']);args=p.parse_args()
    (pool if args.mode=='pool' else finish)()
