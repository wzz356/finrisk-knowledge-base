"""E05 local spherical clustering and full-population dense navigation experiment.

Summary text/claims must be authored and reviewed outside this program. Nodes
are navigation only; every reranker input and returned evidence is a corpus unit.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "outputs/FinRisk_E07_E06_E05探索_20261013"
E04_CODE = ROOT / "work/finrisk_e04_pilot_20261012/experiment.py"
DEMO_CODE = ROOT / "work/finrisk_demo_v3_20261013/demo.py"
FIVEH_CODE = ROOT / "work/finrisk_e01_e04_5h_20261013/experiment.py"
DISPLAY_CODE = FIVEH_CODE.with_name("display_experiment.py")
PRIOR = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"
COHORT = ROOT / "outputs/FinRisk_E02小批量实验_20261013/cohort.json"
CODE_SHA = {
    E04_CODE: "dc2269e588af38966be1e2675fb7c86f1caab60f0e11e88e535574cd3a07c46e",
    DEMO_CODE: "90da39ef2e9e32ea4614d8ae193dc15b268b8a6dd90951d137cb935fdea6dc32",
    FIVEH_CODE: "e34f0f978ed731e29e9e1bf47df4ef2c67d3553d999c788c8a20b401234914e9",
    DISPLAY_CODE: "a0b5f50410938beb886d3188004cbb7b7320f764d5941fe42ef640db1a4e196d",
}
ARMS = ("B0", "DIR", "TREE")
SIDECARS = ("", ".partial", ".run.json", ".failure.json", ".token_audit.jsonl", ".score_pool.jsonl")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_sha(path, expected):
    if sha_file(path) != expected:
        raise ValueError("SHA256 drift: " + str(path))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path, value, *, new=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if new else "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def emit(event, **fields):
    print(json.dumps(dict(event=event, **fields), ensure_ascii=True, allow_nan=False), flush=True)


def ranked(rows):
    return [dict(row, rank=i) for i, row in enumerate(rows, 1)]


def assert_new_output(output):
    for suffix in SIDECARS:
        path = Path(str(output) + suffix)
        if path.exists():
            raise FileExistsError("refusing output/sidecar overwrite: " + str(path))


def validate_new_cache(cache):
    path = Path(cache).resolve()
    if path == HERE or not path.is_relative_to(HERE):
        raise ValueError("cache must be a new child of E07/E06/E05 work directory")
    if path.exists():
        raise FileExistsError("cache must not already exist: " + str(path))
    return path


def validate_freeze(path, required):
    hashes = read_json(path).get("files_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("freeze requires files_sha256")
    normalized = {}
    for name, digest in hashes.items():
        target = Path(name)
        if not target.is_absolute() or not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("freeze requires absolute paths and lowercase SHA256")
        key = str(target.resolve())
        if key in normalized:
            raise ValueError("duplicate normalized freeze path")
        check_sha(target, digest)
        normalized[key] = digest
    if not {str(Path(p).resolve()) for p in required}.issubset(normalized):
        raise ValueError("required dependency missing from freeze")
    normalized[str(Path(path).resolve())] = sha_file(path)
    return normalized


def modules():
    result = []
    for path, name in [(E04_CODE, "e05_frozen_e04"), (DEMO_CODE, "e05_frozen_demo")]:
        check_sha(path, CODE_SHA[path])
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result.append(module)
    for path in (FIVEH_CODE, DISPLAY_CODE):
        check_sha(path, CODE_SHA[path])
    return result


def spherical_kmeans(vectors, clusters, seed=17, max_iter=100):
    """Hard cosine Lloyd clustering with deterministic nonempty repair."""
    import numpy as np
    vectors = np.asarray(vectors, dtype="float64")
    if vectors.ndim != 2 or not len(vectors) or not vectors.shape[1] or not np.isfinite(vectors).all():
        raise ValueError("finite nonempty 2D vectors required")
    if type(clusters) is not int or not 1 <= clusters <= len(vectors) or max_iter <= 0:
        raise ValueError("invalid cluster count/iteration limit")
    norms = np.linalg.norm(vectors, axis=1)
    if (norms <= 0).any():
        raise ValueError("zero vectors cannot be cosine clustered")
    vectors = vectors / norms[:, None]
    initial = np.random.default_rng(seed).choice(len(vectors), clusters, replace=False)
    centers = vectors[initial].copy()
    previous = None
    repairs = 0
    for iteration in range(1, max_iter + 1):
        similarity = vectors @ centers.T
        labels = similarity.argmax(axis=1)
        counts = np.bincount(labels, minlength=clusters)
        for empty in np.flatnonzero(counts == 0):
            movable = [i for i in range(len(labels)) if counts[labels[i]] > 1]
            chosen = min(movable, key=lambda i: (float(similarity[i, labels[i]]), i))
            counts[labels[chosen]] -= 1
            labels[chosen] = empty
            counts[empty] += 1
            repairs += 1
        for ci in range(clusters):
            members = vectors[labels == ci]
            mean = members.mean(axis=0)
            norm = np.linalg.norm(mean)
            centers[ci] = mean / norm if norm > 1e-12 else members[0]
        if previous is not None and np.array_equal(labels, previous):
            break
        previous = labels.copy()
    return labels, centers.astype("float32"), dict(seed=seed, iterations=iteration,
        max_iter=max_iter, converged=iteration < max_iter, empty_cluster_repairs=repairs,
        objective=float((vectors * centers[labels]).sum()), initial_row_indices=initial.tolist(),
        method="numpy_hard_spherical_kmeans_not_UMAP_GMM")


def validate_nodes(nodes, whitelist):
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("navigation nodes cannot be empty")
    seen = set()
    for node in nodes:
        nid, text, descendants = node.get("node_id"), node.get("text"), node.get("descendant_unit_ids")
        if not isinstance(nid, str) or not nid or nid in seen or not isinstance(text, str) or not text.strip():
            raise ValueError("node ID/text empty or duplicated")
        seen.add(nid)
        if type(node.get("level")) is not int or node["level"] < 0:
            raise ValueError("node level must be nonnegative integer")
        if not isinstance(descendants, list) or not descendants or any(not isinstance(uid, str) or not uid for uid in descendants):
            raise ValueError("node descendants cannot be empty")
        if len(set(descendants)) != len(descendants) or not set(descendants).issubset(whitelist):
            raise ValueError("node descendants duplicate/outside 21-leaf whitelist")
    return {n["node_id"]: n for n in nodes}


def validate_layer(nodes, whitelist):
    validate_nodes(nodes, whitelist)
    descendants = [uid for n in nodes for uid in n["descendant_unit_ids"]]
    if len(descendants) != len(set(descendants)) or set(descendants) != set(whitelist):
        raise ValueError("cluster input layer must partition all reviewed leaves")


def validate_leaves(leaves, unit_map, approved, *, expected_count=21):
    whitelist = set(approved)
    validate_nodes(leaves, whitelist)
    if len(leaves) != expected_count or len(approved) != expected_count:
        raise ValueError("requires exact reviewed leaf population")
    actual = set()
    for leaf in leaves:
        uid = leaf.get("unit_id")
        if leaf["level"] != 0 or leaf["descendant_unit_ids"] != [uid] or uid in actual or uid not in unit_map:
            raise ValueError("leaf requires exactly one distinct original unit")
        unit, scope = unit_map[uid], approved[uid]
        if leaf.get("file_id") != unit["file_id"] or leaf.get("source_sha256") != unit["source_sha256"]:
            raise ValueError("leaf source/unit SHA binding differs")
        if leaf["text"] != scope["indexed_text"] or canonical(leaf.get("segments")) != canonical(scope["segments"]):
            raise ValueError("leaf text/segments differ from reviewed source scope")
        # The original short unit can be ambiguous while its reviewed scope
        # preserves every relevant occurrence. Do not erase or reinterpret it.
        if scope.get("scope_status") == "ambiguous_unchanged":
            raise ValueError("ambiguous leaf cannot navigate")
        actual.add(uid)
    if actual != whitelist:
        raise ValueError("leaf whitelist differs from approved scope")
    return actual


def validate_tree(tree, leaves):
    whitelist = {u for leaf in leaves for u in leaf["descendant_unit_ids"]}
    nodes = validate_nodes(tree, whitelist)
    if len(tree) != 7 or {level: sum(n["level"] == level for n in tree) for level in (1, 2, 3)} != {1: 4, 2: 2, 3: 1}:
        raise ValueError("TREE requires exactly 4/2/1 summary nodes")
    lower = {leaf["node_id"]: leaf for leaf in leaves}
    for level in (1, 2, 3):
        current = [n for n in tree if n["level"] == level]
        consumed = []
        for node in current:
            children = node.get("child_node_ids")
            if not isinstance(children, list) or not children or len(children) != len(set(children)) or not set(children).issubset(lower):
                raise ValueError("TREE requires valid child_node_ids at immediately lower level")
            descendants = {u for cid in children for u in lower[cid]["descendant_unit_ids"]}
            if set(node["descendant_unit_ids"]) != descendants:
                raise ValueError("TREE parent descendant union differs from children")
            consumed.extend(children)
        if len(consumed) != len(set(consumed)) or set(consumed) != set(lower):
            raise ValueError("TREE hard cluster layer must partition all lower nodes")
        lower = {n["node_id"]: n for n in current}
    return nodes


def navigation_route(units, original_scores, nodes, node_scores, whitelist, *, top_k=100):
    """Rank corpus rows and nodes together, expand after TopK competition."""
    import numpy as np
    original_scores, node_scores = np.asarray(original_scores), np.asarray(node_scores)
    if original_scores.shape != (len(units),) or node_scores.shape != (len(nodes),) or not np.isfinite(original_scores).all() or not np.isfinite(node_scores).all():
        raise ValueError("dense score population/nonfinite mismatch")
    unit_ids = [u["unit_id"] for u in units]
    if len(unit_ids) != len(set(unit_ids)) or top_k <= 0:
        raise ValueError("dense unit IDs duplicate/top_k invalid")
    if nodes:
        validate_nodes(nodes, whitelist)
        if any(not set(n["descendant_unit_ids"]).issubset(unit_ids) for n in nodes):
            raise ValueError("node descendants absent from full corpus")
    # Original row index is the frozen dense tie breaker; nodes follow originals
    # on exact ties and have stable node-ID order among themselves.
    node_order = sorted(range(len(nodes)), key=lambda i: nodes[i]["node_id"])
    scores = np.concatenate([original_scores, node_scores[node_order]])
    order = np.lexsort((np.arange(len(scores)), -scores))[:top_k]
    if not nodes:
        return ranked([dict(unit_id=unit_ids[int(i)], score=float(scores[i])) for i in order]), [], []
    emitted, route, hits, expansion = set(), [], [], []
    for combined_rank, index in enumerate(order, 1):
        score = float(scores[index])
        if index < len(units):
            uid = unit_ids[int(index)]
            if uid not in emitted and len(route) < top_k:
                emitted.add(uid)
                route.append(dict(unit_id=uid, score=score, score_origin="original_unit_cosine", combined_rank=combined_rank))
        else:
            node = nodes[node_order[int(index) - len(units)]]
            hits.append(dict(node_id=node["node_id"], level=node["level"], score=score,
                rank=combined_rank, text_sha256=sha_text(node["text"]), descendant_unit_ids=node["descendant_unit_ids"]))
            for uid in sorted(node["descendant_unit_ids"]):
                reason = "already_emitted" if uid in emitted else ("expanded_top_k_full" if len(route) >= top_k else "accepted")
                accepted = reason == "accepted"
                expansion.append(dict(node_id=node["node_id"], unit_id=uid, navigation_rank=combined_rank,
                    score=score, score_origin="navigation_node_cosine_not_leaf_cosine", accepted=accepted, reason=reason))
                if accepted:
                    emitted.add(uid)
                    route.append(dict(unit_id=uid, score=score, combined_rank=combined_rank, node_id=node["node_id"],
                        score_origin="navigation_node_cosine_not_leaf_cosine"))
    return ranked(route), hits, expansion


def score_binding(query, unit, manifest_sha, runtime, inputs, run_id):
    return dict(query_id=query["query_id"], query_text_sha256=sha_text(query["text"]),
        unit_id=unit["unit_id"], file_id=unit["file_id"], indexed_text_sha256=sha_text(unit["text"]),
        source_sha256=unit["source_sha256"], manifest_sha256=manifest_sha, runtime=runtime,
        experiment_inputs=inputs, run_id=run_id)


def validate_score_binding(actual, expected):
    if canonical(actual) != canonical(expected):
        raise ValueError("rerank score binding differs: query/text/source/runtime/run")


def score_candidates(models, query, candidates, unit_map, arm, *, manifest_sha, runtime, inputs, run_id, pool, pool_handle):
    ids = [r["unit_id"] for r in candidates]
    if len(ids) != len(set(ids)) or not set(ids).issubset(unit_map):
        raise ValueError("invalid rerank candidate population")
    bindings = {uid: score_binding(query, unit_map[uid], manifest_sha, runtime, inputs, run_id) for uid in ids}
    keys = {uid: hashlib.sha256(canonical(bindings[uid])).hexdigest() for uid in ids}
    missing = [r for r in candidates if keys[r["unit_id"]] not in pool]
    for uid in ids:
        if keys[uid] in pool:
            validate_score_binding(pool[keys[uid]]["binding"], bindings[uid])
    start = time.perf_counter()
    if missing:
        actual = models.rerank(query["text"], missing, unit_map, "E05_" + arm, query["query_id"])
        if len(actual) != len(missing) or {r["unit_id"] for r in actual} != {r["unit_id"] for r in missing}:
            raise ValueError("actual rerank returned incomplete/duplicate population")
        for row in actual:
            if isinstance(row["score"], bool) or not isinstance(row["score"], (int, float)) or not math.isfinite(row["score"]):
                raise ValueError("nonfinite rerank score")
            uid = row["unit_id"]
            pool[keys[uid]] = dict(score=float(row["score"]), binding=bindings[uid], first_arm=arm)
    missing_ids = {r["unit_id"] for r in missing}
    scores = {}
    for uid in ids:
        entry = pool[keys[uid]]
        scores[uid] = entry["score"]
        pool_handle.write(canonical(dict(query_id=query["query_id"], arm=arm, unit_id=uid, score=entry["score"],
            pool_key=keys[uid], binding=bindings[uid], provenance=dict(first_arm=entry["first_arm"],
                kind="actual_local_gpu_rerank" if uid in missing_ids else "same_round_exact_input_shared",
                old_rerank_scores_used=False))).decode("utf-8") + "\n")
    pool_handle.flush()
    return scores, dict(newly_scored_units=len(missing), reused_units=len(ids) - len(missing), rerank_seconds=time.perf_counter() - start)


def dependencies(e04, demo, old_log):
    params = old_log["parameters"]
    event = [r for r in old_log["models"]["cache_events"] if r.get("kind") == "document" and r.get("corpus") == "structured"]
    if len(event) != 1:
        raise ValueError("expected one frozen document cache event")
    return [Path(__file__), *CODE_SHA, e04.BACKEND, e04.ADAPTER, e04.PREPARED / "manifest.json",
        e04.PREPARED / "structured.jsonl", e04.LEGACY_RUN, e04.LEGACY_RESULTS,
        Path(params["project_src"]) / "retrieval/sparse.py", Path(params["project_src"]) / "retrieval/tokenization.py",
        demo.SOURCE_FILE, PRIOR / "scope_units.jsonl", PRIOR / "scope_review.jsonl", COHORT,
        e04.LEGACY_CACHE / (event[0]["key"] + ".json"), e04.LEGACY_CACHE / (event[0]["key"] + ".npy")]


def scope_bindings(unit_map, approved):
    return {uid: dict(file_id=unit_map[uid]["file_id"], source_sha256=unit_map[uid]["source_sha256"],
        indexed_text_sha256=sha_text(unit_map[uid]["text"]), reviewed_scope_text_sha256=sha_text(scope["indexed_text"]),
        original_evidence_ambiguous=unit_map[uid].get("evidence_ambiguous", False),
        reviewed_scope_occurrence_ambiguity=scope.get("occurrence_ambiguity", False),
        reviewed_scope_attribution_ambiguity=scope.get("attribution_ambiguity", False),
        scope_status=scope.get("scope_status")) for uid, scope in sorted(approved.items())}


def navigation_token_preflight(models, rows, stage):
    texts = [r["text"] for r in rows]
    lengths = [len(ids) for ids in models.embed_tokenizer(texts, truncation=False, padding=False)["input_ids"]]
    if len(lengths) != len(rows):
        raise ValueError("navigation tokenizer input count mismatch")
    for row, length in zip(rows, lengths):
        models.token_handle.write(canonical(dict(stage="E05_preflight_" + stage, id=row["unit_id"],
            input_text_sha256=sha_text(row["text"]), input_tokens=length, max_length=models.args.max_length,
            rejected=length > models.args.max_length, truncation_allowed=False)).decode("utf-8") + "\n")
    models.token_handle.flush()
    if any(n > models.args.max_length for n in lengths):
        raise ValueError("navigation text exceeds token limit; revise/freeze summary before GPU encoding")
    return dict(inputs=len(rows), max_input_tokens=max(lengths, default=0), max_length=models.args.max_length,
                truncated_inputs=0, truncation_allowed=False)


def load_scope(demo, leaves_path):
    sources = demo.source_map()
    unit_map, approved = demo.load_scope(sources)
    leaves = read_jsonl(leaves_path)
    whitelist = validate_leaves(leaves, unit_map, approved)
    return sources, unit_map, approved, leaves, whitelist


def cluster(args):
    assert_new_output(args.output)
    args.cache = validate_new_cache(args.cache)
    e04, demo = modules()
    check_sha(e04.LEGACY_RUN, e04.LEGACY_RUN_SHA)
    check_sha(e04.PREPARED / "manifest.json", e04.MANIFEST_SHA)
    check_sha(e04.LEGACY_RESULTS, e04.LEGACY_RESULTS_SHA)
    old_log = read_json(e04.LEGACY_RUN)
    required = dependencies(e04, demo, old_log) + [args.nodes, args.leaves]
    inputs = validate_freeze(args.freeze, required) if args.freeze else {str(Path(p).resolve()): sha_file(p) for p in required}
    _, unit_map, approved, leaves, whitelist = load_scope(demo, args.leaves)
    nodes = read_jsonl(args.nodes)
    validate_layer(nodes, whitelist)
    levels = {n["level"] for n in nodes}
    if len(levels) != 1 or (len(nodes), args.clusters, next(iter(levels))) not in {(21, 4, 0), (4, 2, 1), (2, 1, 2)}:
        raise ValueError("cluster requires exact 21/0→4, 4/1→2 or 2/2→1 phase")
    if next(iter(levels)) == 0 and canonical(nodes) != canonical(leaves):
        raise ValueError("leaf clustering input must equal reviewed leaves")
    models, started = None, time.perf_counter()
    log = dict(status="running", command="cluster", inputs=inputs, formal_gpu_experiment=True,
               nodes=len(nodes), clusters=args.clusters, seed=17)
    write_json(Path(str(args.output) + ".run.json"), log, new=True)
    try:
        model_args = e04.make_model_args(args.output, old_log)
        model_args.cache = args.cache
        models = e04.frozen_modules()[0].LocalModels(model_args)
        e04.validate_models(models, old_log)
        encoded_rows = [dict(unit_id=n["node_id"], text=n["text"]) for n in nodes]
        log["node_token_preflight"] = navigation_token_preflight(models, encoded_rows, "cluster_nodes")
        emit("cluster_encode_start", nodes=len(nodes), clusters=args.clusters)
        vectors = models.encode(encoded_rows, "document", "E05_cluster_nodes")
        if models.log["cache_events"][-1]["hit"]:
            raise ValueError("cluster nodes require new actual BGE encoding")
        labels, centers, algorithm = spherical_kmeans(vectors, args.clusters)
        result_clusters = []
        for ci in range(args.clusters):
            members = [n for i, n in enumerate(nodes) if int(labels[i]) == ci]
            result_clusters.append(dict(cluster_id=ci, member_node_ids=[n["node_id"] for n in members],
                members=[dict(node_id=n["node_id"], level=n["level"], text=n["text"], text_sha256=sha_text(n["text"]),
                    descendant_unit_ids=n["descendant_unit_ids"]) for n in members],
                descendant_unit_ids=sorted({u for n in members for u in n["descendant_unit_ids"]}),
                centroid=centers[ci].tolist()))
        for path, digest in inputs.items():
            check_sha(path, digest)
        event = models.log["cache_events"][-1]
        metadata = read_json(args.cache / (event["key"] + ".json"))
        result = dict(version="E05-spherical-clusters-v1", algorithm=algorithm, input_nodes_sha256=sha_file(args.nodes),
            leaves_sha256=sha_file(args.leaves), inputs=inputs, embedding_model=models.embedding_info,
            runtime_binding=e04.runtime_binding(old_log), normalized_vector_path=str((args.cache / (event["key"] + ".npy")).resolve()),
            normalized_vectors_sha256=metadata["npy_sha256"], token_audit=metadata["token_audit"],
            token_summary=metadata["token_summary"], clusters=result_clusters,
            descendants_bindings=scope_bindings(unit_map, approved),
            summary_authoring="root_session_model_after_source_review; program_does_not_generate_summary")
        write_json(args.output, result, new=True)
        log.update(status="complete", output_sha256=sha_file(args.output), elapsed_seconds=time.perf_counter() - started)
    except BaseException as exc:
        log.update(status="failure", error=f"{type(exc).__name__}: {exc}")
        write_json(Path(str(args.output) + ".failure.json"), log, new=True)
        raise
    finally:
        if models is not None:
            models.token_handle.close()
            log["models"] = models.log
            log["token_audit_sha256"] = sha_file(Path(str(args.output) + ".token_audit.jsonl"))
        write_json(Path(str(args.output) + ".run.json"), log)
    emit("cluster_complete", output=str(args.output), seconds=log["elapsed_seconds"])


def retrieve(args):
    assert_new_output(args.output)
    args.cache = validate_new_cache(args.cache)
    e04, demo = modules()
    check_sha(e04.LEGACY_RUN, e04.LEGACY_RUN_SHA)
    old_log = read_json(e04.LEGACY_RUN)
    required = dependencies(e04, demo, old_log) + [args.queries, args.leaves, args.directory_nodes, args.tree_nodes,
        demo.OUT / "queries.jsonl", demo.OUT / "input_freeze.json"]
    inputs = validate_freeze(args.freeze, required)
    queries = read_jsonl(args.queries)
    if len(queries) != 16 or len({q.get("query_id") for q in queries}) != 16 or any(not isinstance(q.get("text"), str) or not q["text"].strip() for q in queries):
        raise ValueError("requires 16 unique nonempty frozen replay queries")
    demo.assert_freeze(demo.OUT / "input_freeze.json")
    if [(q["query_id"], q["text"]) for q in queries] != [(q["query_id"], q["text"]) for q in read_jsonl(demo.OUT / "queries.jsonl")]:
        raise ValueError("E05 replay query IDs/text/order differ from frozen V3 inputs")
    sources, displayed_units, approved, leaves, whitelist = load_scope(demo, args.leaves)
    directory, tree = read_jsonl(args.directory_nodes), read_jsonl(args.tree_nodes)
    validate_nodes(directory, whitelist)
    validate_tree(tree, leaves)
    if {u for n in directory for u in n["descendant_unit_ids"]} != whitelist:
        raise ValueError("DIR must cover all reviewed leaves")
    if set(n["node_id"] for n in directory) & set(n["node_id"] for n in tree):
        raise ValueError("DIR/TREE node IDs must be disjoint")
    models, start = None, time.perf_counter()
    log = dict(status="running", command="retrieve", run_id=str(uuid.uuid4()), inputs=inputs,
        actual_gpu_run=True, arms=list(ARMS), result_rows=0, completed_queries=0,
        full_unit_population=65475, file_population=9639, reviewed_leaf_population=21,
        bm25=dict(k1=1.5, b=0.75, weight=1.0), rrf=dict(k=60, weights=[1, 1], route_top_k=100, union_max=200, rerank_top_k=100),
        navigation="full original rows + navigation nodes cosine Top100, then sorted-unit expansion/dedup Top100",
        old_query_vectors_used=False, old_rerank_scores_used=False, summaries_are_evidence=False)
    log["reviewed_leaf_bindings"] = scope_bindings(displayed_units, approved)
    log_path = Path(str(args.output) + ".run.json")
    write_json(log_path, log, new=True)
    try:
        backend, adapter, old_log, manifest, units, unit_map, _, source_audit = e04.prepare_inputs([], "dev")
        if len(units) != 65475 or len({u["file_id"] for u in units}) != 9639 or unit_map != displayed_units:
            raise ValueError("original full population differs from source-reviewed display baseline")
        del displayed_units
        log["source_audit"] = source_audit
        adapter.frozen_tokenizer()
        model_args = e04.make_model_args(args.output, old_log)
        model_args.cache = args.cache
        emit("model_load_start", command="E05_retrieve")
        models = backend.LocalModels(model_args)
        e04.validate_models(models, old_log)
        runtime = e04.runtime_binding(old_log)
        log.update(runtime_binding=runtime, parameters={k: str(v) if isinstance(v, Path) else v for k, v in vars(model_args).items()})
        log["document_cache_seed"] = e04.seed_document_cache(old_log, manifest, units, models, backend)
        doc_vectors = models.encode(units, "document", "structured")
        if not models.log["cache_events"][-1]["hit"]:
            raise ValueError("base document vectors must come from verified copied cache")
        query_vectors = models.encode(queries, "query", "E05_shared_16_replay_queries")
        if models.log["cache_events"][-1]["hit"]:
            raise ValueError("queries must be freshly encoded once")
        all_nodes = directory + tree
        node_rows = [dict(unit_id=n["node_id"], text=n["text"]) for n in all_nodes]
        log["node_token_preflight"] = navigation_token_preflight(models, node_rows, "navigation_nodes")
        node_vectors = models.encode(node_rows, "document", "E05_navigation_nodes")
        if models.log["cache_events"][-1]["hit"]:
            raise ValueError("navigation nodes must be freshly encoded")
        if not models.np.isfinite(doc_vectors).all() or not models.np.isfinite(query_vectors).all() or not models.np.isfinite(node_vectors).all():
            raise ValueError("nonfinite embedding vectors")
        log["vector_operation"] = dict(query_encoding_calls=1, actual_query_encoding_rows=16,
            actual_node_encoding_rows=len(all_nodes), original_document_reencoding_rows=0,
            original_documents_origin="SHA/runtime/source-bound_old_cache_copy", normalized=True,
            original_array_sha256=hashlib.sha256(doc_vectors.tobytes()).hexdigest())
        sys.path.insert(0, str(model_args.project_src.resolve()))
        from retrieval.sparse import RetrievalDocument, SparseRetrievalIndex
        index_start = time.perf_counter()
        sparse = SparseRetrievalIndex([RetrievalDocument(unit_id=u["unit_id"], case_ids=(u["case_id"],), text=u["text"], source="structured", weight=1.0) for u in units], k1=1.5, b=0.75)
        log["bm25_index_seconds"] = time.perf_counter() - index_start
        write_json(log_path, log)
        pool_path, partial = Path(str(args.output) + ".score_pool.jsonl"), Path(str(args.output) + ".partial")
        with partial.open("x", encoding="utf-8") as handle, pool_path.open("x", encoding="utf-8") as pool_handle:
            for qi, query in enumerate(queries):
                emit("query_start", query_id=query["query_id"], index=qi + 1, total=16)
                qstart = time.perf_counter()
                stage_start = time.perf_counter()
                bm25 = [dict(unit_id=h.document.unit_id, score=float(h.score), rank=h.rank) for h in sparse.search(query["text"], top_k=100)]
                bm25_seconds = time.perf_counter() - stage_start
                stage_start = time.perf_counter()
                original_scores = doc_vectors @ query_vectors[qi]
                nav_scores = node_vectors @ query_vectors[qi]
                cosine_seconds = time.perf_counter() - stage_start
                pool = {}
                for arm in ARMS:
                    stage_start = time.perf_counter()
                    nodes = [] if arm == "B0" else (directory if arm == "DIR" else tree)
                    node_scores = models.np.empty(0) if arm == "B0" else (nav_scores[:len(directory)] if arm == "DIR" else nav_scores[len(directory):])
                    dense, node_hits, expansion = navigation_route(units, original_scores, nodes, node_scores, whitelist)
                    route_seconds = time.perf_counter() - stage_start
                    e04.validate_ranked(bm25, unit_map, 100)
                    e04.validate_ranked(dense, unit_map, 100)
                    stage_start = time.perf_counter()
                    union = backend.rrf([bm25, dense], k=60, top_k=200)
                    candidates = union[:100]
                    if len(candidates) != 100:
                        raise ValueError("each arm must rerank exactly 100 full-corpus candidates")
                    rrf_seconds = time.perf_counter() - stage_start
                    scores, stats = score_candidates(models, query, candidates, unit_map, arm, manifest_sha=e04.MANIFEST_SHA,
                        runtime=runtime, inputs=inputs, run_id=log["run_id"], pool=pool, pool_handle=pool_handle)
                    reranked = ranked(sorted([dict(unit_id=uid, score=score, binding=score_binding(query, unit_map[uid], e04.MANIFEST_SHA, runtime, inputs, log["run_id"])) for uid, score in scores.items()], key=lambda r: (-r["score"], r["unit_id"])))
                    cases, files = adapter.aggregate(reranked, unit_map, top_k=20)
                    cases = [demo.scoped_hit(h, unit_map, approved, sources) for h in cases]
                    files = [demo.scoped_hit(h, unit_map, approved, sources) for h in files]
                    stage_binding = dict(query_id=query["query_id"], query_text_sha256=sha_text(query["text"]),
                        manifest_sha256=e04.MANIFEST_SHA, runtime=runtime, inputs=inputs, run_id=log["run_id"])
                    for rows in (bm25, dense, union, candidates):
                        for row in rows:
                            row["binding"] = dict(stage_binding, unit_id=row["unit_id"],
                                indexed_text_sha256=sha_text(unit_map[row["unit_id"]]["text"]), source_sha256=unit_map[row["unit_id"]]["source_sha256"])
                    for hit in node_hits:
                        hit["binding"] = dict(stage_binding, node_id=hit["node_id"], node_text_sha256=hit["text_sha256"], leaves_sha256=sha_file(args.leaves))
                    node_by_id = {n["node_id"]: n for n in nodes}
                    for expanded in expansion:
                        unit = unit_map[expanded["unit_id"]]
                        expanded["binding"] = dict(stage_binding, unit_id=unit["unit_id"],
                            source_sha256=unit["source_sha256"], indexed_text_sha256=sha_text(unit["text"]),
                            node_id=expanded["node_id"], node_text_sha256=sha_text(node_by_id[expanded["node_id"]]["text"]),
                            leaves_sha256=sha_file(args.leaves))
                    record = dict(corpus="structured", arm=arm, query_id=query["query_id"], text=query["text"],
                        files=files, cases=cases, top5=files[:5],
                        stages=dict(bm25=bm25, dense=dense, navigation_node_hits=node_hits, expansion_provenance=expansion,
                            rrf_union=union, rrf_top100=candidates, rerank=reranked),
                        timing=dict(bm25_seconds=bm25_seconds, shared_cosine_seconds=cosine_seconds,
                            navigation_route_seconds=route_seconds, rrf_seconds=rrf_seconds, **stats,
                            shared_query_elapsed_seconds=time.perf_counter() - qstart),
                        provenance=dict(stage_binding, routes_origin="same_round_actual_full_population_BM25_BGE",
                            rerank_origin="same_round_actual_original_text_rerank_and_exact_shared_inputs",
                            old_query_vectors_used=False, old_rerank_scores_used=False, summaries_are_evidence=False,
                            navigation_leaf_score="node_score_not_independent_leaf_cosine", full_top20_retained=True,
                            returned_context="frozen_V2_with_21_source_reviewed_V3_display_only"),
                        dose=dict(node_top100_hits=len(node_hits), accepted_expansions=sum(r["accepted"] for r in expansion),
                            leaf_rerank_candidates=sum(r["unit_id"] in whitelist for r in candidates),
                            leaf_top5_units=[r["unit_id"] for r in files[:5] if r["unit_id"] in whitelist]))
                    handle.write(canonical(record).decode("utf-8") + "\n")
                    log["result_rows"] += 1
                handle.flush()
                log.update(completed_queries=qi + 1, elapsed_seconds=time.perf_counter() - start, models=models.log)
                write_json(log_path, log)
                emit("query_complete", query_id=query["query_id"], actual_unique_rerank_units=len(pool), seconds=time.perf_counter() - qstart)
        if log["result_rows"] != 48 or log["completed_queries"] != 16:
            raise ValueError("incomplete 16x3 experiment")
        for path, digest in inputs.items():
            check_sha(path, digest)
        if args.output.exists():
            raise FileExistsError("output appeared during run")
        partial.rename(args.output)
        log.update(status="complete", output_sha256=sha_file(args.output), score_pool_sha256=sha_file(pool_path),
                   elapsed_seconds=time.perf_counter() - start)
    except BaseException as exc:
        log.update(status="failure", error=f"{type(exc).__name__}: {exc}", elapsed_seconds=time.perf_counter() - start)
        write_json(Path(str(args.output) + ".failure.json"), log, new=True)
        raise
    finally:
        if models is not None:
            models.token_handle.close()
            log["models"] = models.log
            log["token_audit_sha256"] = sha_file(Path(str(args.output) + ".token_audit.jsonl"))
        write_json(log_path, log)
    emit("retrieve_complete", rows=48, seconds=log["elapsed_seconds"], output=str(args.output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    c = commands.add_parser("cluster", help="fresh local BGE encoding and seed17 spherical KMeans; no summary generation")
    for name in ("nodes", "output", "cache"):
        c.add_argument("--" + name, type=Path, required=True)
    c.add_argument("--clusters", type=int, required=True)
    c.add_argument("--leaves", type=Path, default=OUT / "leaves.jsonl")
    c.add_argument("--freeze", type=Path)
    r = commands.add_parser("retrieve", help="same-round B0/DIR/TREE full-population real GPU experiment")
    for name in ("queries", "leaves", "directory-nodes", "tree-nodes", "freeze", "output", "cache"):
        r.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    (cluster if args.command == "cluster" else retrieve)(args)


if __name__ == "__main__":
    main()
