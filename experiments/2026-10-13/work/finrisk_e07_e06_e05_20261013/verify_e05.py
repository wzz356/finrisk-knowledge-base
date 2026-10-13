"""Read-only checks of complete actual retrieval, source spans and stage arithmetic."""
from collections import Counter, defaultdict
import math
import e05_runner as e
from e07 import OUT,demo


def main():
    run=demo.read_json(OUT / 'e05_results.jsonl.run.json')
    result=demo.rows(OUT / 'e05_results.jsonl')
    pool=demo.rows(OUT / 'e05_results.jsonl.score_pool.jsonl')
    assert run['status']=='complete' and run['completed_queries']==16 and run['result_rows']==48
    assert len(result)==48 and len(pool)==4800
    assert demo.sha_file(OUT / 'e05_results.jsonl')==run['output_sha256']
    assert demo.sha_file(OUT / 'e05_results.jsonl.score_pool.jsonl')==run['score_pool_sha256']
    assert demo.sha_file(OUT / 'e05_results.jsonl.token_audit.jsonl')==run['token_audit_sha256']
    for path,digest in run['inputs'].items():assert demo.sha_file(path)==digest
    sources=demo.source_map()
    e04,_=e.modules()
    unit_map,approved=demo.load_scope(sources)
    leaves=demo.rows(OUT / 'leaves.jsonl')
    tree=demo.rows(OUT / 'tree_nodes.jsonl')
    e.validate_leaves(leaves,unit_map,approved);e.validate_tree(tree,leaves)
    groups=defaultdict(list)
    for r in result:groups[r['query_id']].append(r)
    assert len(groups)==16 and all({r['arm'] for r in rows}=={'B0','DIR','TREE'} for rows in groups.values())
    scores={(p['query_id'],p['arm'],p['unit_id']):p for p in pool}
    assert len(scores)==4800
    provenance_counts=Counter(p['provenance']['kind'] for p in pool)
    shared_score_keys={}
    for p in pool:
        key=p['pool_key']
        if key in shared_score_keys:assert p['score']==shared_score_keys[key]['score'] and p['binding']==shared_score_keys[key]['binding']
        else:
            assert p['provenance']['kind']=='actual_local_gpu_rerank'
            shared_score_keys[key]=p
    assert len(shared_score_keys)==provenance_counts['actual_local_gpu_rerank']
    for qid,records in groups.items():
        baseline=next(r for r in records if r['arm']=='B0')
        for record in records:
            arm=record['arm'];stages=record['stages']
            assert stages['bm25']==baseline['stages']['bm25']
            rrfs=defaultdict(float)
            for stage in ('bm25','dense'):
                route=stages[stage]
                assert len(route)==100 and len({r['unit_id'] for r in route})==100
                assert [r['rank'] for r in route]==list(range(1,101))
                for row in route:rrfs[row['unit_id']]+=1/(60+row['rank'])
            expected=sorted(rrfs.items(),key=lambda p:(-p[1],p[0]))
            assert [(r['unit_id'],r['score']) for r in stages['rrf_union']]==expected
            assert stages['rrf_top100']==stages['rrf_union'][:100]
            candidates={r['unit_id'] for r in stages['rrf_top100']}
            assert len(stages['rerank'])==100 and {r['unit_id'] for r in stages['rerank']}==candidates
            for row in stages['rerank']:
                p=scores[(qid,arm,row['unit_id'])]
                assert p['score']==row['score'] and p['binding']==row['binding']
                assert row['binding']==e.score_binding({'query_id':qid,'text':record['text']},unit_map[row['unit_id']],
                    e04.MANIFEST_SHA,
                    run['runtime_binding'],run['inputs'],run['run_id'])
            assert [(r['unit_id'],r['score']) for r in stages['rerank']]==sorted(
                [(uid,scores[(qid,arm,uid)]['score']) for uid in candidates],key=lambda p:(-p[1],p[0]))
            first_files=[];seen=set()
            for row in stages['rerank']:
                file_id=unit_map[row['unit_id']]['file_id']
                if file_id not in seen:first_files.append((file_id,row['unit_id'],row['score']));seen.add(file_id)
            first_files.sort(key=lambda h:(-h[2],h[0]))
            assert [(h['file_id'],h['unit_id'],h['score']) for h in record['files']]==first_files[:20]
            assert record['top5']==record['files'][:5] and len(record['top5'])==5
            demo.make_packet({'query_id':qid,'text':record['text']},record['files'],sources)
            assert record['dose']['node_top100_hits']==len(stages['navigation_node_hits'])
            assert record['dose']['accepted_expansions']==sum(r['accepted'] for r in stages['expansion_provenance'])
            assert record['timing']['newly_scored_units']+record['timing']['reused_units']==100
    assert sum(r['timing']['newly_scored_units'] for r in result)==provenance_counts['actual_local_gpu_rerank']
    assert sum(r['timing']['reused_units'] for r in result)==provenance_counts['same_round_exact_input_shared']
    audits=demo.rows(OUT / 'e05_results.jsonl.token_audit.jsonl')
    summary=dict(status='passed',queries=16,arms=3,positions=240,rerank_stage_positions=4800,
        actual_new_pairs=provenance_counts['actual_local_gpu_rerank'],exact_shared_pairs=provenance_counts['same_round_exact_input_shared'],
        all_stage_arithmetic_and_bindings=True,all_top20_display_segments_exact=True,
        all_frozen_dependencies_unchanged=True,summary_not_evidence=True,
        results_sha256=run['output_sha256'],run_sha256=demo.sha_file(OUT / 'e05_results.jsonl.run.json'),
        token_audit_records=len(audits))
    demo.write_new(OUT / 'e05_verification.json',summary)
    print(summary)


if __name__=='__main__':main()
