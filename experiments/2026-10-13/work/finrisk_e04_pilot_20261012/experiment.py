"""E04 local pilot: frozen V2 inputs, weighted RRF and shared real rerank pools.

This module never alters the frozen runners, production application or knowledge
repository. Model calls are made only through the original LocalModels interface.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import sys
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BACKEND = ROOT / "work/finrisk_retrieval_20261012/runner.py"
ADAPTER = ROOT / "work/finrisk_v2_20261012/run_v2.py"
PREPARED = ROOT / "outputs/FinRisk_知识库V2_20261012/indexes/all9639_final"
LEGACY_RESULTS = ROOT / "outputs/FinRisk_知识库V2_20261012/retrieval/all9639_results.jsonl"
LEGACY_RUN = Path(str(LEGACY_RESULTS) + ".run.json")
REPO = ROOT / "finrisk-knowledge-base"
LEGACY_CACHE = ROOT / "work/finrisk_retrieval_20261012/vector_cache"
CACHE = HERE / "vector_cache"
BACKEND_SHA = "7a05001beb6e611e47743ec420f70763f61fd106932b02d54f73e24d772da4cb"
ADAPTER_SHA = "c846cac66071c7f83028d99fb5968332655d51bb550abe4047cf0505c5ad44d4"
MANIFEST_SHA = "9f7f2d8cdbc621cfa577d8c5ffac439be3aeeeccc2f0e487cd1210bd78487a8d"
LEGACY_RUN_SHA = "3e1fadd47983d9710ece824c0c050b7d304d0b2e34a69a599d1401a408fcd8f0"
LEGACY_RESULTS_SHA = "c76f196843d94b0e026baf8cd69f54f720d9fec278fb9518b5857a88ce3c04c1"
ARMS = {"A0": {"weights": [1, 1], "depth": 100},
        "A1": {"weights": [2, 1], "depth": 100},
        "A2": {"weights": [1, 1], "depth": 200},
        "A3": {"weights": [2, 1], "depth": 200}}
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


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def save_json(path, value):
    # The run's sidecars are new files. Only its own current log is updated.
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8") + b"\n")


def emit(event, **fields):
    print(json.dumps(dict(event=event, **fields), ensure_ascii=True, allow_nan=False), flush=True)


def ranked(rows):
    return [dict(row, rank=index) for index, row in enumerate(rows, 1)]


def weighted_rrf(routes, weights, k=60, top_k=200):
    if isinstance(k, bool) or not isinstance(k, (int, float)) or not math.isfinite(k) or k <= 0:
        raise ValueError("RRF k must be finite and positive")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("RRF depth must be a positive integer")
    if len(routes) != len(weights) or not routes:
        raise ValueError("one weight is required for every route")
    if any(isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or w <= 0 for w in weights):
        raise ValueError("RRF weights must be finite and positive")
    scores = {}
    for route, weight in zip(routes, weights):
        seen = set()
        rank = 0
        for row in route or []:
            uid = row["unit_id"]
            if not isinstance(uid, str) or not uid:
                raise ValueError("route unit_id must be a nonempty string")
            if uid in seen:
                continue
            seen.add(uid)
            rank += 1
            scores[uid] = scores.get(uid, 0.0) + weight / (k + rank)
    pairs = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))[:top_k]
    return ranked([dict(unit_id=uid, score=score) for uid, score in pairs])


def candidates_for_arm(routes, arm):
    if arm not in ARMS or len(routes) != 2:
        raise ValueError("unknown arm or wrong route count")
    config = ARMS[arm]
    return weighted_rrf([(route or [])[:100] for route in routes], config["weights"], k=60, top_k=config["depth"])


def missing_candidates(candidates, scores):
    return [dict(row) for row in candidates if row["unit_id"] not in scores]


def score_binding(query, unit, manifest_sha, runtime):
    return dict(query_id=query["query_id"], query_text_sha256=sha_text(query["text"]),
                unit_id=unit["unit_id"], indexed_text_sha256=sha_text(unit["text"]),
                source_sha256=unit["source_sha256"], manifest_sha256=manifest_sha, runtime=runtime)


def validate_score_binding(actual, expected):
    if canonical(actual) != canonical(expected):
        raise ValueError("stale rerank score binding; query/source/indexed text/runtime differ")


def validate_dev_query(query, frozen_queries):
    original = frozen_queries.get(query["query_id"])
    if original is None or query.get("text") != original.get("text"):
        raise ValueError("dev score reuse requires exact frozen query ID and text: " + query["query_id"])


def validate_unit_binding(unit, bindings):
    source = bindings.get(unit["file_id"])
    if source is None or unit.get("source_sha256") != source["text_sha256"] or unit.get("candidate_sha256") != source["effective_draft_json_sha256"]:
        raise ValueError("unit has stale or unknown source/candidate binding: " + unit["unit_id"])


@lru_cache(maxsize=1)
def frozen_modules():
    modules = []
    for name, path, expected in [("finrisk_e04_frozen_backend", BACKEND, BACKEND_SHA),
                                 ("finrisk_e04_frozen_adapter", ADAPTER, ADAPTER_SHA)]:
        if sha_file(path) != expected:
            raise ValueError("frozen module SHA changed: " + str(path))
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return tuple(modules)


def build_record(query, arm, routes, scores, unit_map, adapter, *, timing, provenance):
    if arm not in ARMS:
        raise ValueError("unknown arm: " + arm)
    bounded_routes = [(route or [])[:100] for route in routes]
    union = weighted_rrf(bounded_routes, ARMS[arm]["weights"], k=60, top_k=200)
    candidates = union[:ARMS[arm]["depth"]]
    hits = []
    for row in candidates:
        score = scores.get(row["unit_id"])
        if score is None or isinstance(score, bool) or not math.isfinite(score):
            raise ValueError("missing or nonfinite real rerank score: " + row["unit_id"])
        hits.append(dict(unit_id=row["unit_id"], score=float(score)))
    reranked = ranked(sorted(hits, key=lambda row: (-row["score"], row["unit_id"])))
    cases, files = adapter.aggregate(reranked, unit_map)
    stages = dict(bm25=bounded_routes[0], dense=bounded_routes[1], rrf_union=union,
                  rrf_top100=union[:100], rerank_candidates=candidates, rerank=reranked)
    return dict(query_id=query["query_id"], text=query["text"], corpus="structured", arm=arm,
                files=files, cases=cases, stages=stages, timing=timing,
                configuration=dict(rrf_k=60, route_top_k=100, **ARMS[arm]), provenance=provenance)


def fill_score_pool(query, candidates, unit_map, reused, models):
    scores = dict(reused)
    missing = missing_candidates(candidates, scores)
    if not missing:
        return scores, 0.0
    emit("scoring_start", query_id=query["query_id"], missing=len(missing), reused=len(reused))
    started = time.perf_counter()
    computed = models.rerank(query["text"], missing, unit_map, "structured", query["query_id"])
    elapsed = time.perf_counter() - started
    expected_ids = {row["unit_id"] for row in missing}
    if len(computed) != len(expected_ids) or {row["unit_id"] for row in computed} != expected_ids:
        raise ValueError("reranker returned incomplete or duplicate scores")
    for row in computed:
        score = row["score"]
        if isinstance(score, bool) or not math.isfinite(score):
            raise ValueError("reranker returned nonfinite score")
        scores[row["unit_id"]] = float(score)
    emit("scoring_complete", query_id=query["query_id"], computed=len(missing), seconds=elapsed)
    return scores, elapsed


def assert_a0_reproduction(record, original):
    if record["query_id"] != original["query_id"] or record["text"] != original["text"]:
        raise ValueError("A0 query differs from baseline")
    for key in ("files", "cases"):
        if canonical(record[key]) != canonical(original[key]):
            raise ValueError("A0 does not exactly reproduce original " + key)
    for key in ("bm25", "dense", "rrf_union", "rrf_top100", "rerank"):
        if canonical(record["stages"].get(key)) != canonical(original["stages"].get(key)):
            raise ValueError("A0 does not exactly reproduce original stage " + key)


def load_selection(path, expected_sha, arms):
    if path is None or not expected_sha or sha_file(path) != expected_sha:
        raise ValueError("confirmation requires selection file and its exact frozen SHA256")
    selection = read_json(path)
    configured = selection.get("confirmation_arms")
    if not isinstance(configured, list) or len(configured) != 2 or len(set(configured)) != 2 or configured[0] != "A0" or any(a not in ARMS for a in configured):
        raise ValueError("selection.confirmation_arms must be [A0, selected/comparison arm]")
    if list(arms) != configured:
        raise ValueError("requested confirmation arms differ from frozen selection")
    selected = selection.get("chosen_arm", selection.get("selected_arm"))
    if "chosen_arm" in selection and "selected_arm" in selection and selection["chosen_arm"] != selection["selected_arm"]:
        raise ValueError("selection chosen_arm and selected_arm disagree")
    if selected not in ARMS or (selected != "A0" and selected != configured[1]) or (selected == "A0" and configured[1] != "A3"):
        raise ValueError("selection selected_arm and confirmation_arms disagree")
    return dict(path=str(Path(path).resolve()), sha256=expected_sha, chosen_arm=selected, selected_arm=selected,
                confirmation_arms=configured)


def assert_new_output(output):
    for suffix in SIDECARS:
        path = Path(str(output) + suffix)
        if path.exists():
            raise FileExistsError("refusing to overwrite existing output/sidecar: " + str(path))


def check_sha(path, expected):
    actual = sha_file(path)
    if actual != expected:
        raise ValueError("SHA256 mismatch: " + str(path))
    return actual


def validate_preparation_dependencies(manifest):
    # Normalization was executed during historical preparation, not this read-only
    # rerun. Its historical SHA stays in provenance; a later compatible tool edit
    # does not alter the hash-bound prepared units used by retrieval.
    check_sha(ADAPTER.parent / "projection_v2.py", manifest["projection_sha256"])
    return dict(projection_sha256=manifest["projection_sha256"],
                historical_normalization_sha256=manifest["normalization_sha256"],
                normalization_executed_in_retrieval=False)


def validate_ranked(rows, unit_map, maximum):
    if not isinstance(rows, list) or len(rows) > maximum:
        raise ValueError("invalid route/candidate depth")
    seen = set()
    for i, row in enumerate(rows, 1):
        uid = row.get("unit_id")
        score = row.get("score")
        if uid not in unit_map or uid in seen or row.get("rank") != i or isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
            raise ValueError("invalid frozen ranked row")
        seen.add(uid)


def verify_sources(manifest):
    """Read only explicit reviewed export shards referenced by the frozen manifest."""
    repo_manifest_path = REPO / "manifest.json"
    check_sha(repo_manifest_path, manifest["repo_manifest_sha256"])
    repo_manifest = read_json(repo_manifest_path)
    source_root = (REPO / "data/sources").resolve()
    grouped = defaultdict(dict)
    for binding in manifest["source_manifest"]:
        location = binding["source_location"]
        path = Path(location["path"]).resolve()
        if path.parent != source_root or not path.name.startswith("part-") or path.suffix != ".jsonl":
            raise ValueError("source path leaves authorized reviewed export shards")
        line = location["line"]
        if not isinstance(line, int) or line <= 0 or line in grouped[path]:
            raise ValueError("invalid/duplicate source location")
        grouped[path][line] = binding
    count = 0
    for path, selected_lines in sorted(grouped.items()):
        relative = path.relative_to(REPO).as_posix()
        check_sha(path, repo_manifest["files"][relative]["sha256"])
        with path.open(encoding="utf-8-sig") as handle:
            for line_no, line in enumerate(handle, 1):
                binding = selected_lines.get(line_no)
                if binding is None:
                    continue
                row = json.loads(line)
                body = row.get("full_text")
                if row.get("file_id") != binding["file_id"] or not isinstance(body, str) or sha_text(body) != binding["text_sha256"] or row.get("text_sha256") != binding["text_sha256"]:
                    raise ValueError("source text binding differs: " + binding["file_id"])
                count += 1
        if count and count % 2000 < 100:
            emit("prepare_source_progress", verified_sources=count, expected=9639)
    if count != 9639:
        raise ValueError("incomplete reviewed source verification")
    return dict(source_files=count, source_shards=len(grouped), repo_manifest_sha256=manifest["repo_manifest_sha256"])


def prepare_inputs(queries, mode):
    started = time.perf_counter()
    backend, adapter = frozen_modules()
    emit("prepare_start", mode=mode, queries=len(queries), expected_sources=9639)
    check_sha(LEGACY_RUN, LEGACY_RUN_SHA)
    check_sha(LEGACY_RESULTS, LEGACY_RESULTS_SHA)
    check_sha(PREPARED / "manifest.json", MANIFEST_SHA)
    old_log, manifest = read_json(LEGACY_RUN), read_json(PREPARED / "manifest.json")
    if old_log.get("status") != "complete" or old_log.get("output_sha256") != LEGACY_RESULTS_SHA or old_log.get("manifest_sha256") != MANIFEST_SHA or old_log.get("runner_sha256") != BACKEND_SHA or old_log.get("v2_adapter", {}).get("sha256") != ADAPTER_SHA:
        raise ValueError("incomplete/stale legacy run provenance")
    if manifest.get("status") != "complete" or manifest.get("scope") != "all" or manifest.get("source_files") != 9639 or manifest.get("backend_sha256") != BACKEND_SHA or manifest.get("adapter_sha256") != ADAPTER_SHA:
        raise ValueError("wrong prepared scope or code binding")
    preparation_code = validate_preparation_dependencies(manifest)
    params = old_log["parameters"]
    required_params = dict(device="cuda", precision="float16", batch_size=16, max_length=512, expected_files=9639, corpora=["structured"])
    if any(params.get(k) != v for k, v in required_params.items()) or old_log.get("bm25") != dict(k1=1.5, b=0.75, weight=1.0) or old_log.get("rrf") != dict(k=60, ranks_start=1, equal_weights=True, route_top_k=100, union_max=200, rerank_top_k=100):
        raise ValueError("legacy model/retrieval parameters changed")
    sparse_path = Path(params["project_src"]) / "retrieval/sparse.py"
    tokenizer_path = Path(params["project_src"]) / "retrieval/tokenization.py"
    check_sha(sparse_path, old_log["bm25_source_sha256"])
    check_sha(tokenizer_path, old_log["tokenizer_source_sha256"])
    if manifest.get("tokenizer_source_sha256") != old_log["tokenizer_source_sha256"]:
        raise ValueError("prepared/run tokenizer binding differs")
    original_queries_path = Path(params["queries"])
    check_sha(original_queries_path, old_log["queries_sha256"])
    frozen_queries = {q["query_id"]: q for q in read_jsonl(original_queries_path)}
    if mode == "dev":
        for query in queries:
            validate_dev_query(query, frozen_queries)
    else:
        if any(q["query_id"] in frozen_queries or q["text"] in {row["text"] for row in frozen_queries.values()} for q in queries):
            raise ValueError("confirmation must use new query IDs and text")
    source_audit = verify_sources(manifest)
    source_audit["preparation_code"] = preparation_code
    corpus_path = PREPARED / "structured.jsonl"
    check_sha(corpus_path, manifest["corpora"]["structured"]["sha256"])
    units = list(read_jsonl(corpus_path))
    unit_map = {unit["unit_id"]: unit for unit in units}
    if len(units) != manifest["corpora"]["structured"]["count"] or len(unit_map) != len(units) or backend.ordered_text_sha(units) != manifest["corpora"]["structured"]["ordered_unit_text_sha256"]:
        raise ValueError("structured corpus count/order differs")
    bindings = {row["file_id"]: row for row in manifest["source_manifest"]}
    if len(bindings) != 9639:
        raise ValueError("reviewed source identities are not 9639 unique files")
    for unit in units:
        if unit.get("corpus") != "structured":
            raise ValueError("non-structured unit in frozen corpus")
        validate_unit_binding(unit, bindings)
    baseline = {}
    wanted = {q["query_id"] for q in queries}
    if mode == "dev":
        for row in read_jsonl(LEGACY_RESULTS):
            if row.get("corpus") != "structured" or row.get("arm") != "rrf_rerank" or row.get("query_id") not in wanted:
                continue
            qid = row["query_id"]
            if qid in baseline or row["text"] != frozen_queries[qid]["text"]:
                raise ValueError("duplicate/stale baseline query result")
            stages = row["stages"]
            for name, maximum in [("bm25", 100), ("dense", 100), ("rrf_union", 200), ("rrf_top100", 100), ("rerank", 100)]:
                validate_ranked(stages[name], unit_map, maximum)
            union = weighted_rrf([stages["bm25"], stages["dense"]], [1, 1], k=60, top_k=200)
            if union != stages["rrf_union"] or union[:100] != stages["rrf_top100"] or {r["unit_id"] for r in stages["rerank"]} != {r["unit_id"] for r in union[:100]}:
                raise ValueError("frozen baseline stages are inconsistent")
            scores = {hit["unit_id"]: hit["score"] for hit in stages["rerank"]}
            test_record = build_record(frozen_queries[qid], "A0", [stages["bm25"], stages["dense"]], scores, unit_map, adapter, timing={}, provenance={})
            assert_a0_reproduction(test_record, row)
            baseline[qid] = row
        if set(baseline) != wanted:
            raise ValueError("missing exact baseline query results")
    emit("prepare_complete", units=len(units), verified_sources=source_audit["source_files"], seconds=time.perf_counter() - started)
    return backend, adapter, old_log, manifest, units, unit_map, baseline, source_audit


def make_model_args(output, old_log):
    params = old_log["parameters"]
    return SimpleNamespace(output=output, cache=CACHE, embedding_model=Path(params["embedding_model"]),
                           reranker_model=Path(params["reranker_model"]), project_src=Path(params["project_src"]),
                           device=params["device"], precision=params["precision"], batch_size=params["batch_size"],
                           max_length=params["max_length"])


def validate_models(models, old_log):
    previous = old_log["models"]
    # Reused logits depend on identical weights, tokenizer files, precision and runtime.
    for field in ("device", "precision", "query_instruction", "torch", "transformers", "numpy", "embedding", "reranker"):
        if canonical(models.log[field]) != canonical(previous[field]):
            raise ValueError("current local model/runtime differs from frozen score provenance: " + field)
    if models.args.batch_size != old_log["parameters"]["batch_size"] or models.args.max_length != old_log["parameters"]["max_length"]:
        raise ValueError("current batch size/max length differs from frozen score provenance")


def runtime_binding(old_log):
    params, models = old_log["parameters"], old_log["models"]
    return dict(runner_sha256=BACKEND_SHA, adapter_sha256=ADAPTER_SHA,
                device=params["device"], precision=params["precision"], batch_size=params["batch_size"],
                max_length=params["max_length"], torch=models["torch"], transformers=models["transformers"],
                numpy=models["numpy"], query_instruction=models["query_instruction"],
                embedding_cache_sha256=models["embedding"]["cache_sha256"],
                reranker_cache_sha256=models["reranker"]["cache_sha256"])


def document_encoding_binding(models):
    # Same document binding fields as the frozen LocalModels.encode method.
    return dict(model=models.embedding_info, tokenizer_class=type(models.embed_tokenizer).__name__,
                token_audit_schema_version=2, max_length=models.args.max_length, query_instruction="",
                pooling="CLS", normalization="L2", torch=models.log["torch"],
                transformers=models.log["transformers"], precision=models.args.precision, kind="document")


def seed_document_cache(old_log, manifest, units, models, backend, *, legacy_cache=LEGACY_CACHE):
    """Copy only the hash-verified frozen document pair into this run's new cache."""
    events = [row for row in old_log["models"]["cache_events"]
              if row.get("kind") == "document" and row.get("corpus") == "structured"]
    if len(events) != 1:
        raise ValueError("legacy run must identify exactly one structured document cache key")
    key = events[0]["key"]
    if not isinstance(key, str) or len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
        raise ValueError("invalid legacy document cache key")
    corpus = manifest["corpora"]["structured"]
    text_sha = backend.ordered_text_sha(units)
    expected_binding = document_encoding_binding(models)
    if len(units) != corpus["count"] or text_sha != corpus["ordered_unit_text_sha256"] or backend.cache_key(text_sha, expected_binding) != key:
        raise ValueError("legacy document cache is not bound to current projection/model inputs")
    source_cache, target_cache = Path(legacy_cache).resolve(), Path(models.args.cache).resolve()
    if source_cache == target_cache:
        raise ValueError("legacy cache is read-only; target must be a new experiment cache")
    source_meta, source_vectors = source_cache / (key + ".json"), source_cache / (key + ".npy")
    metadata = read_json(source_meta)
    if metadata.get("key") != key or metadata.get("ordered_unit_text_sha256") != text_sha or canonical(metadata.get("binding")) != canonical(expected_binding):
        raise ValueError("stale legacy document cache metadata binding")
    vector_sha = check_sha(source_vectors, metadata["npy_sha256"])
    meta_sha = sha_file(source_meta)
    backend.validate_token_audit(metadata.get("token_audit"), [u["unit_id"] for u in units], models.args.max_length)
    vectors = models.np.load(source_vectors, allow_pickle=False, mmap_mode="r")
    try:
        if vectors.ndim != 2 or vectors.shape[0] != len(units) or list(vectors.shape) != metadata.get("shape") or vectors.dtype != models.np.dtype("float32"):
            raise ValueError("legacy document cache array shape/dtype differs")
    finally:
        del vectors
    expected = {".json": meta_sha, ".npy": vector_sha}
    # Check both destinations before writing either: differing prior content is
    # never overwritten, while identical copied files can be reused safely.
    for suffix, expected_sha in expected.items():
        target = target_cache / (key + suffix)
        if target.exists() and sha_file(target) != expected_sha:
            raise FileExistsError("different content already exists in E04 cache: " + str(target))
    target_cache.mkdir(parents=True, exist_ok=True)
    copied = []
    for suffix, expected_sha in expected.items():
        source, target = source_cache / (key + suffix), target_cache / (key + suffix)
        if not target.exists():
            with source.open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
            copied.append(suffix)
        check_sha(target, expected_sha)
        check_sha(source, expected_sha)
    emit("document_cache_seeded", key=key, copied=copied, cache=str(target_cache))
    return dict(key=key, source_cache=str(source_cache), target_cache=str(target_cache),
                metadata_sha256=meta_sha, npy_sha256=vector_sha, copied_suffixes=copied,
                ordered_unit_text_sha256=text_sha, legacy_cache_access="read_only",
                source_key_from="frozen legacy run models.cache_events document/structured")


def confirmation_index(models, args, units, queries):
    sys.path.insert(0, str(args.project_src.resolve()))
    from retrieval.sparse import RetrievalDocument, SparseRetrievalIndex
    emit("confirmation_index_start", units=len(units), queries=len(queries))
    started = time.perf_counter()
    index = SparseRetrievalIndex([RetrievalDocument(unit_id=u["unit_id"], case_ids=(u["case_id"],),
                                                   text=u["text"], source="structured", weight=1.0) for u in units], k1=1.5, b=0.75)
    seconds = time.perf_counter() - started
    query_vectors = models.encode(queries, "query", "shared")
    doc_vectors = models.encode(units, "document", "structured")
    emit("confirmation_index_ready", units=len(units), bm25_index_seconds=seconds)
    return index, query_vectors, doc_vectors, seconds


def confirmation_routes(models, index, query_vector, doc_vectors, units, query):
    started = time.perf_counter()
    bm25 = [dict(unit_id=h.document.unit_id, score=float(h.score), rank=h.rank) for h in index.search(query["text"], top_k=100)]
    bm25_seconds = time.perf_counter() - started
    started = time.perf_counter()
    scores = doc_vectors @ query_vector
    order = models.np.lexsort((models.np.arange(len(scores)), -scores))[:100]
    dense = ranked([dict(unit_id=units[int(i)]["unit_id"], score=float(scores[i])) for i in order])
    return [bm25, dense], dict(bm25_seconds=bm25_seconds, dense_seconds=time.perf_counter() - started, routes_reused=False)


def run(args):
    assert_new_output(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    experiment_sha = sha_file(__file__)
    log_path = Path(str(args.output) + ".run.json")
    partial_path = Path(str(args.output) + ".partial")
    pool_path = Path(str(args.output) + ".score_pool.jsonl")
    log = dict(status="partial", mode=args.mode, query_count=0, queries_path=str(args.queries.resolve()),
               queries_sha256=None, arms=args.arms, configurations={a: ARMS[a] for a in args.arms if a in ARMS},
               runner_sha256=BACKEND_SHA, adapter_sha256=ADAPTER_SHA, experiment_sha256=experiment_sha,
               legacy_results_sha256=LEGACY_RESULTS_SHA, legacy_run_sha256=LEGACY_RUN_SHA,
               manifest_sha256=MANIFEST_SHA, selection=None, result_rows=0, completed_queries=0,
               network="local_files_only; no paid API", corpus="structured", source_population=9639,
               rrf=dict(k=60, ranks_start=1, route_top_k=100, union_max=200, duplicates="count once within route",
                        tie_break="score descending, unit_id ascending", raw_scores_combined=False))
    save_json(log_path, log)
    models = None
    try:
        if args.mode == "confirmation":
            selection = load_selection(args.selection, args.selection_sha256, args.arms)
        elif args.selection is not None or args.selection_sha256 is not None:
            raise ValueError("selection binding is only used in confirmation mode")
        else:
            selection = None
        queries_sha = sha_file(args.queries)
        queries = list(read_jsonl(args.queries))
        if not queries or any(not isinstance(q, dict) or not isinstance(q.get("query_id"), str) or not q["query_id"] or not isinstance(q.get("text"), str) or not q["text"].strip() for q in queries) or len({q["query_id"] for q in queries}) != len(queries):
            raise ValueError("query input must have unique nonempty IDs and text")
        if not args.arms or len(set(args.arms)) != len(args.arms) or any(a not in ARMS for a in args.arms):
            raise ValueError("arms must be unique valid E04 configurations")
        log.update(query_count=len(queries), queries_sha256=queries_sha, selection=selection)
        save_json(log_path, log)
        backend, adapter, old_log, manifest, units, unit_map, baseline, source_audit = prepare_inputs(queries, args.mode)
        log["source_audit"] = source_audit
        model_args = make_model_args(args.output, old_log)
        emit("model_load_start", device=model_args.device, precision=model_args.precision)
        models = backend.LocalModels(model_args)
        validate_models(models, old_log)
        emit("model_load_complete", seconds=models.log["model_load_seconds"], gpu=models.log["gpu"])
        binding = runtime_binding(old_log)
        log["runtime_binding"] = binding
        log["parameters"] = {key: str(value) if isinstance(value, Path) else value for key, value in vars(model_args).items()}
        index_seconds = 0.0
        if args.mode == "confirmation":
            log["document_cache_seed"] = seed_document_cache(old_log, manifest, units, models, backend)
            save_json(log_path, log)
            index, query_vectors, doc_vectors, index_seconds = confirmation_index(models, model_args, units, queries)
        with partial_path.open("x", encoding="utf-8") as output, pool_path.open("x", encoding="utf-8") as pool_output:
            for qi, query in enumerate(queries):
                query_started = time.perf_counter()
                qid = query["query_id"]
                emit("query_start", query_id=qid, index=qi + 1, total=len(queries), mode=args.mode)
                reused = {}
                original = baseline.get(qid)
                if original:
                    routes = [original["stages"]["bm25"], original["stages"]["dense"]]
                    reused = {r["unit_id"]: r["score"] for r in original["stages"]["rerank"]}
                    route_timing = dict(bm25_seconds=0.0, dense_seconds=0.0, routes_reused=True,
                                        original_route_seconds={k: original["timing"][k] for k in ("bm25_seconds", "dense_seconds")})
                else:
                    routes, route_timing = confirmation_routes(models, index, query_vectors[qi], doc_vectors, units, query)
                union = weighted_rrf(routes, [1, 1], k=60, top_k=200)
                # Score the actual entire <=200 union once. All four configurations
                # draw from this same pool, even when only two arms are requested.
                scores, gpu_seconds = fill_score_pool(query, union, unit_map, reused, models)
                missing_ids = {r["unit_id"] for r in missing_candidates(union, reused)}
                for row in union:
                    uid = row["unit_id"]
                    score_origin = dict(kind="actual_local_gpu_rerank" if uid in missing_ids else "frozen_same_input_rerank",
                                        legacy_result_path=None if uid in missing_ids else str(LEGACY_RESULTS),
                                        legacy_result_sha256=None if uid in missing_ids else LEGACY_RESULTS_SHA,
                                        legacy_query_id=None if uid in missing_ids else qid)
                    pool_row = dict(query_id=qid, unit_id=uid, score=scores[uid],
                                    binding=score_binding(query, unit_map[uid], MANIFEST_SHA, binding), provenance=score_origin)
                    validate_score_binding(pool_row["binding"], score_binding(query, unit_map[uid], MANIFEST_SHA, binding))
                    pool_output.write(canonical(pool_row).decode("utf-8") + "\n")
                pool_output.flush()
                for arm in args.arms:
                    t = time.perf_counter()
                    provenance = dict(mode=args.mode, runner_sha256=BACKEND_SHA, adapter_sha256=ADAPTER_SHA,
                                      experiment_sha256=experiment_sha, manifest_sha256=MANIFEST_SHA,
                                      structured_sha256=manifest["corpora"]["structured"]["sha256"],
                                      queries_sha256=queries_sha, query_text_sha256=sha_text(query["text"]),
                                      runtime_binding=binding, selection=selection,
                                      score_pool_path=str(pool_path.resolve()), score_pool_scope="same query actual two-route union",
                                      actual_union_units=len(union), reused_score_units=len(reused), newly_scored_units=len(missing_ids),
                                      routes_origin="frozen_original_top100" if original else "actual_local_bm25_and_bge",
                                      legacy_results_sha256=LEGACY_RESULTS_SHA if original else None,
                                      returned_context="unchanged frozen V2 aggregate full context")
                    timing = dict(**route_timing, shared_pool_rerank_seconds=gpu_seconds,
                                  rerank_seconds=gpu_seconds, gpu_seconds_shared_by_arms=True,
                                  bm25_index_seconds=index_seconds)
                    record = build_record(query, arm, routes, scores, unit_map, adapter, timing=timing, provenance=provenance)
                    record["timing"]["fusion_and_aggregate_seconds"] = time.perf_counter() - t
                    record["timing"]["shared_query_seconds"] = time.perf_counter() - query_started
                    if original and arm == "A0":
                        assert_a0_reproduction(record, original)
                        record["provenance"]["a0_exact_reproduction"] = True
                    output.write(canonical(record).decode("utf-8") + "\n")
                    log["result_rows"] += 1
                output.flush()
                log["completed_queries"] += 1
                log["elapsed_seconds"] = time.perf_counter() - started
                log["models"] = models.log
                save_json(log_path, log)
                emit("query_complete", query_id=qid, arms=args.arms, union_units=len(union), reused=len(reused),
                     new_scores=len(missing_ids), gpu_seconds=gpu_seconds, seconds=time.perf_counter() - query_started)
        if log["result_rows"] != len(queries) * len(args.arms):
            raise RuntimeError("incomplete result rows")
        check_sha(__file__, experiment_sha)
        check_sha(BACKEND, BACKEND_SHA)
        check_sha(ADAPTER, ADAPTER_SHA)
        check_sha(args.queries, queries_sha)
        check_sha(PREPARED / "manifest.json", MANIFEST_SHA)
        if selection:
            check_sha(args.selection, args.selection_sha256)
        if args.output.exists():
            raise FileExistsError("output appeared during run; refusing replace")
        partial_path.rename(args.output)
        log.update(status="complete", elapsed_seconds=time.perf_counter() - started,
                   output_path=str(args.output.resolve()), output_sha256=sha_file(args.output),
                   score_pool_sha256=sha_file(pool_path))
    except BaseException as exc:
        log.update(status="failure", error=f"{type(exc).__name__}: {exc}", elapsed_seconds=time.perf_counter() - started)
        save_json(Path(str(args.output) + ".failure.json"), log)
        emit("run_failure", error=log["error"], result_rows=log["result_rows"])
        raise
    finally:
        if models:
            models.token_handle.close()
            log["models"] = models.log
            log["token_audit_sha256"] = sha_file(Path(str(args.output) + ".token_audit.jsonl"))
        save_json(log_path, log)
    emit("run_complete", rows=log["result_rows"], seconds=log["elapsed_seconds"], output=str(args.output))
    return log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("dev", "confirmation"), required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arms", nargs="+", choices=tuple(ARMS), default=list(ARMS))
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--selection-sha256")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
