"""Structural exposure/latency diagnostics; no semantic judgments."""
from collections import Counter
from e07 import OUT,demo


def main():
    records=demo.rows(OUT / 'e05_results.jsonl')
    baseline={r['query_id']:r for r in records if r['arm']=='B0'}
    rows=[]
    for r in records:
        row=dict(query_id=r['query_id'],arm=r['arm'],dose=r['dose'],
            newly_scored=r['timing']['newly_scored_units'],reused=r['timing']['reused_units'],
            nodes=[dict(node_id=n['node_id'],rank=n['rank'],score=n['score']) for n in r['stages']['navigation_node_hits']],
            before=[h['file_id'] for h in baseline[r['query_id']]['top5']],
            after=[h['file_id'] for h in r['top5']])
        row['new_contexts']=[dict(file_id=h['file_id'],unit_id=h['unit_id'],text=h['text']) for h in r['top5']
            if (h['file_id'],h['unit_id'],h['text']) not in {(v['file_id'],v['unit_id'],v['text']) for v in baseline[r['query_id']]['top5']}]
        rows.append(row)
    run=demo.read_json(OUT / 'e05_results.jsonl.run.json')
    out=dict(rows=rows,token_summary=run['models']['truncation'],
        model_load_seconds=run['models']['model_load_seconds'],bm25_index_seconds=run['bm25_index_seconds'],
        actual_gpu_seconds=run['elapsed_seconds'],node_token_preflight=run['node_token_preflight'],
        actual_retrieve_total_rerank_positions=4800,actual_new_rerank_pairs=sum(r['timing']['newly_scored_units'] for r in records),
        actual_shared_rerank_pairs=sum(r['timing']['reused_units'] for r in records))
    demo.write_new(OUT / 'e05_diagnostics.json',out)
    print(dict(arms={arm:dict(node_hits=sum(r['dose']['node_top100_hits'] for r in records if r['arm']==arm),
        accepted_expansions=sum(r['dose']['accepted_expansions'] for r in records if r['arm']==arm),
        changed=[r['query_id'] for r in rows if r['arm']==arm and r['before']!=r['after']]) for arm in ('B0','DIR','TREE')},
        new_contexts=[dict(query_id=r['query_id'],arm=r['arm'],new_files=[n['file_id'] for n in r['new_contexts']]) for r in rows if r['new_contexts']],
        actual_gpu_seconds=run['elapsed_seconds']))


if __name__=='__main__':main()
