"""Static knowledge-side retrieval aids; no predicted label or state is produced."""


def auxiliary_query(text, lexicon, max_mechanisms=2):
    hits = []
    for entry in lexicon:
        matched = [term for term in entry['trigger_any'] if term in text]
        if matched:
            hits.append((sum(len(term) for term in matched), entry['mechanism_id'], entry))
    chosen = [r[2] for r in sorted(hits, key=lambda r: (-r[0], r[1]))[:max_mechanisms]]
    extra = '；'.join(r['canonical_search_text'] for r in chosen)
    return dict(original_text=text, text=extra if extra else text,
                mechanism_ids=[r['mechanism_id'] for r in chosen], hypotheses_only=True)


def fuse(routes, k=60, top=100):
    scores = {}
    for route in routes:
        ids = [r['unit_id'] for r in route]
        if len(set(ids)) != len(ids):
            raise ValueError('duplicate unit within one route')
        for rank, row in enumerate(route, 1):
            scores[row['unit_id']] = scores.get(row['unit_id'], 0.) + 1 / (k + rank)
    return [dict(unit_id=uid, rank=i, score=score)
            for i, (uid, score) in enumerate(sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:top], 1)]


def expanded_routes(bm, dense, aux_bm, aux_dense):
    if aux_bm is None or aux_dense is None:
        return fuse([bm, dense])
    # Query variants receive equal weight inside each modality; modalities remain 1:1.
    return fuse([fuse([bm, aux_bm]), fuse([dense, aux_dense])])
