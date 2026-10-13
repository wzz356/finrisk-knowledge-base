"""Trace the predeclared D013 retrieval gap without changing navigation/scoring."""
from e07 import OUT,demo


def main():
    leaves=demo.rows(OUT / 'leaves.jsonl');leaf=next(l for l in leaves if l['file_id']=='F000699')
    unit_map,approved=demo.load_scope(demo.source_map());unit=unit_map[leaf['unit_id']]
    result=[]
    for row in demo.rows(OUT / 'e05_results.jsonl'):
        if row['query_id']!='D013':continue
        stages=row['stages']
        trace={stage:[dict(rank=h['rank'],score=h['score']) for h in stages[stage] if h['unit_id']==leaf['unit_id']]
               for stage in ('bm25','dense','rrf_union','rrf_top100','rerank')}
        result.append(dict(arm=row['arm'],trace=trace,
            expansions=[{k:h[k] for k in ('node_id','unit_id','accepted','reason') if k in h}
                        for h in stages['expansion_provenance'] if h['unit_id']==leaf['unit_id']],
            file_top20=[dict(rank=h['rank'],unit_id=h['unit_id'],text=h['text']) for h in row['files'] if h['file_id']=='F000699']))
    value=dict(query_id='D013',leaf_unit_id=leaf['unit_id'],indexed_original_text=unit['text'],
        reviewed_leaf_text=leaf['text'],original_text_sha256=demo.sha_text(unit['text']),
        source_sha256=unit['source_sha256'],arms=result,
        diagnostic_only=True,no_inputs_or_scores_changed=True)
    demo.write_new(OUT / 'service_gap_diagnostic.json',value)
    print(value)


if __name__=='__main__':main()
