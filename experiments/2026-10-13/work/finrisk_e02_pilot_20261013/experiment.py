"""E02 extractive-prefix replay; frozen P0/P2 and real local P1 retrieval."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import sys
import time
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "outputs/FinRisk_E02小批量实验_20261013"
E04_OUT = ROOT / "outputs/FinRisk_E04小批量实验_20261012"
E04_CODE = ROOT / "work/finrisk_e04_pilot_20261012/experiment.py"
E04_CODE_SHA = "dc2269e588af38966be1e2675fb7c86f1caab60f0e11e88e535574cd3a07c46e"
E04_DELIVERY_SHA = "6626ef4872f3b70e2a5c110601ae612db24dfb50336c287656448f879547e30a"
SIDECARS = ("", ".partial", ".run.json", ".failure.json", ".score_pool.jsonl", ".token_audit.jsonl")
LABELS = {"文书主体", "片段主体", "责任角色", "行为背景", "适用条件", "材料用途", "产品背景"}
ARMS = ("P0", "P1", "P2")
CONFIGURATION = dict(weights=[1, 1], depth=100, rrf_k=60, route_top_k=100)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_sha(path, expected):
    if sha_file(path) != expected:
        raise ValueError("SHA256 mismatch: "+str(path))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def save_json(path, value):
    Path(path).write_bytes(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")+b"\n")


def emit(event, **fields):
    print(json.dumps(dict(event=event, **fields), ensure_ascii=True, allow_nan=False), flush=True)


@lru_cache(maxsize=1)
def frozen_e04():
    check_sha(E04_CODE, E04_CODE_SHA)
    spec = importlib.util.spec_from_file_location("finrisk_e02_frozen_e04", E04_CODE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_new_output(output):
    for suffix in SIDECARS:
        path = Path(str(output)+suffix)
        if path.exists():
            raise FileExistsError("refusing to overwrite output/sidecar: "+str(path))


def validate_cache_path(cache):
    path = Path(cache).resolve()
    if path == HERE or not path.is_relative_to(HERE):
        raise ValueError("cache must be an isolated child of E02 work directory")
    return path


def validate_replay_queries(queries, frozen, *, expected_count=22):
    if len(queries) != expected_count or len({q.get("query_id") for q in queries}) != expected_count:
        raise ValueError("replay requires exact unique frozen query population")
    if set(q.get("query_id") for q in queries) != set(frozen):
        raise ValueError("replay query selection differs")
    allowed = {"query_id", "text", "group", "query_role", "replay_origin"}
    for query in queries:
        old = frozen[query["query_id"]]
        if set(query)-allowed or any(query.get(k) != old.get(k) for k in ("query_id", "text", "group", "query_role")):
            raise ValueError("replay query text/group/role or metadata differs: "+query["query_id"])
        if not isinstance(query["text"], str) or not query["text"].strip():
            raise ValueError("empty replay query text")


def validate_prefixes(rows, reviews, cohort, unit_map, sources):
    selected = {row["unit_id"]:row for row in cohort["rows"]}
    if len(selected) != len(cohort["rows"]):
        raise ValueError("duplicate cohort unit")
    by_id = {row["unit_id"]:row for row in rows}
    review_map = {row["unit_id"]:row for row in reviews}
    if len(by_id) != len(rows) or set(by_id) != set(selected):
        raise ValueError("duplicate/unknown/missing candidate prefix unit")
    if len(review_map) != len(reviews) or set(review_map) != set(by_id):
        raise ValueError("duplicate/missing/unknown prefix review")
    approved = {}
    for uid, row in by_id.items():
        unit, chosen, review = unit_map.get(uid), selected[uid], review_map[uid]
        if unit is None:
            raise ValueError("prefix unit absent from frozen population")
        source = sources.get(row.get("file_id"))
        if not isinstance(source, str) or row.get("file_id") != unit["file_id"]:
            raise ValueError("prefix file/source identity differs")
        expected = dict(file_id=unit["file_id"], source_sha256=sha_text(source), base_unit_text_sha256=sha_text(unit["text"]))
        if unit["source_sha256"] != expected["source_sha256"] or any(row.get(k) != v or chosen.get(k) != v for k,v in expected.items()):
            raise ValueError("prefix cohort/source/base text binding differs")
        claims, prefix = row.get("claims"), row.get("prefix_text")
        if not isinstance(claims, list) or not 1 <= len(claims) <= 3 or not isinstance(prefix, str) or not 0 < len(prefix) <= 180:
            raise ValueError("prefix requires 1-3 quotes and at most 180 characters")
        rendered = []
        for claim in claims:
            label, quote, span = claim.get("label"), claim.get("quote"), claim.get("span")
            if label not in LABELS or not isinstance(quote, str) or not quote or not isinstance(span, dict) or not isinstance(claim.get("link_reason"), str) or not claim["link_reason"].strip():
                raise ValueError("invalid extract label/quote/link reason/span")
            start, end = span.get("start"), span.get("end")
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source) or source[start:end] != quote:
                raise ValueError("exact quote/span mismatch")
            rendered.append(label+"："+quote)
        if prefix != "\n".join(rendered):
            raise ValueError("prefix differs from labelled exact quotes")
        if review.get("status") not in {"approved_model_review", "rejected"} or review.get("prefix_sha256") != sha_text(prefix) or review.get("source_sha256") != expected["source_sha256"] or not isinstance(review.get("reason"), str) or not review["reason"].strip():
            raise ValueError("prefix review status/SHA/reason binding differs")
        if review["status"] == "approved_model_review":
            approved[uid] = row
    return approved


def validate_quality(prefixes_path, reviews_path, quality_path):
    # The review's text SHA alone cannot bind a changed duplicate span/link reason.
    # The independently produced quality artifact binds the complete reviewed rows.
    quality = read_json(quality_path)
    files = quality.get("files_sha256",{})
    for name,path in (("prefixes.jsonl",prefixes_path),("prefix_review.jsonl",reviews_path)):
        expected = files.get(name)
        if not isinstance(expected,str) or len(expected) != 64:
            raise ValueError("prefix quality file SHA256 binding missing: "+name)
        check_sha(path,expected)
    return quality


def make_overlay(units, approved):
    if not set(approved).issubset({unit["unit_id"] for unit in units}):
        raise ValueError("overlay unit missing")
    return [dict(unit, text=approved[unit["unit_id"]]["prefix_text"]+"\n"+unit["text"])
            if unit["unit_id"] in approved else unit for unit in units]


def overlay_vectors(base, units, changed_units, changed_vectors, np):
    positions = {unit["unit_id"]:i for i,unit in enumerate(units)}
    ids = [unit["unit_id"] for unit in changed_units]
    if len(positions) != len(units) or len(set(ids)) != len(ids) or not set(ids).issubset(positions):
        raise ValueError("invalid overlay vector unit identities")
    if base.ndim != 2 or base.shape[0] != len(units) or base.dtype != np.dtype("float32") or changed_vectors.shape != (len(ids), base.shape[1]) or changed_vectors.dtype != base.dtype or not np.isfinite(changed_vectors).all():
        raise ValueError("overlay vector shape/dtype/value differs")
    result, rows = base.copy(), [positions[uid] for uid in ids]
    if rows:
        result[rows] = changed_vectors
    return result, rows


def decorate_hit(hit, unit_map, approved, arm):
    uid = hit["unit_id"]
    if arm not in ARMS:
        raise ValueError("unknown E02 arm")
    if arm == "P0" or uid not in approved:
        return copy.deepcopy(hit)
    unit, prefix = unit_map[uid], approved[uid]
    if hit["file_id"] != unit["file_id"] or hit["indexed_text"] != unit["text"]:
        raise ValueError("aggregate winner differs from frozen unit")
    original_context = hit["text"]
    result = copy.deepcopy(hit)
    result.update(text="【背景说明（原文摘录，候选）】\n"+prefix["prefix_text"]+
                  "\n\n【原文片段】\n"+original_context,
                  prefix=prefix["prefix_text"], prefix_claims=copy.deepcopy(prefix["claims"]),
                  prefix_source_unit_id=uid, prefix_profile="E02-extractive-v1",
                  prefix_review_status="approved_model_review",
                  prefix_source_sha256=prefix["source_sha256"], prefix_sha256=sha_text(prefix["prefix_text"]),
                  base_context_text=original_context, original_unit_text=unit["text"],
                  indexed_text=prefix["prefix_text"]+"\n"+unit["text"] if arm == "P1" else hit["indexed_text"])
    return result


def assert_baseline_reproduction(record, original):
    for key in ("query_id", "text", "files", "cases", "stages"):
        if canonical(record.get(key)) != canonical(original.get(key)):
            raise ValueError("P0 frozen E04 A0 differs: "+key)


def validate_computed_scores(candidates, rows):
    ids = {row["unit_id"] for row in candidates}
    if len(ids) != len(candidates) or len(rows) != len(ids) or {row["unit_id"] for row in rows} != ids:
        raise ValueError("reranker candidate IDs incomplete or duplicate")
    scores = {}
    for row in rows:
        score = row["score"]
        if isinstance(score, bool) or not isinstance(score, (int,float)) or not math.isfinite(score):
            raise ValueError("nonfinite rerank score")
        scores[row["unit_id"]] = float(score)
    return scores


def audit_inputs(tokenizer, texts, ids, max_length, handle, *, stage, pairs=None, query_id=None, bindings=None):
    if len(texts) != len(ids) or (pairs is not None and len(pairs) != len(texts)):
        raise ValueError("token audit input count differs")
    encoded = tokenizer(texts, pairs, truncation=False, padding=False) if pairs is not None else tokenizer(texts, truncation=False, padding=False)
    lengths = [len(row) for row in encoded["input_ids"]]
    if len(lengths) != len(texts):
        raise ValueError("tokenizer returned incomplete lengths")
    for i,(uid,text,length) in enumerate(zip(ids,texts,lengths)):
        row = dict(stage="strict_preflight_"+stage, id=uid, query_id=query_id, input_tokens=length,
                   max_length=max_length, input_text_sha256=sha_text(text),
                   paired_text_sha256=sha_text(pairs[i]) if pairs is not None else None,
                   rejected=length > max_length, truncation_allowed=False,
                   binding=bindings[i] if bindings else None)
        handle.write(canonical(row).decode("utf-8")+"\n")
    handle.flush()
    if any(length > max_length for length in lengths):
        raise ValueError("token limit exceeded; refusing silent truncation: "+str(query_id or stage))
    return dict(inputs=len(texts), max_input_tokens=max(lengths, default=0), rejected=0, max_length=max_length)


def load_replay(args, e04):
    check_sha(E04_OUT/"delivery_manifest.json", E04_DELIVERY_SHA)
    delivery = read_json(E04_OUT/"delivery_manifest.json")
    delivered = {row["path"]:row["sha256"] for row in delivery["output_files"]+delivery["work_code_notes_and_logs"]}
    input_freeze = read_json(args.queries.parent/"input_freeze.json")
    validate_quality(args.prefixes,args.reviews,args.queries.parent/"prefix_quality.json")
    for name,expected in input_freeze["experiment_inputs_sha256"].items():
        check_sha(args.queries.parent/name, expected)
    queries, originals, original_phases, baseline, origins = read_jsonl(args.queries), {}, {}, {}, {}
    for phase in ("dev", "confirmation"):
        paths = [E04_OUT/(phase+suffix) for suffix in ("_queries.jsonl", "_results.jsonl", "_results.jsonl.run.json")]
        for path in paths:
            check_sha(path, delivered[path.relative_to(ROOT).as_posix()])
        phase_queries = read_jsonl(paths[0])
        phase_log = read_json(paths[2])
        if phase_log.get("status") != "complete" or phase_log.get("output_sha256") != sha_file(paths[1]):
            raise ValueError("incomplete E04 baseline run")
        for q in phase_queries:
            q = dict(q)
            q.setdefault("query_role", "boundary" if q["group"] == "boundary_condition_change" else "risk")
            if q["query_id"] in originals:
                raise ValueError("duplicate frozen E04 query")
            originals[q["query_id"]], original_phases[q["query_id"]] = q, phase
        for record in read_jsonl(paths[1]):
            if record["arm"] != "A0":
                continue
            qid = record["query_id"]
            if qid in baseline or qid not in originals or record["text"] != originals[qid]["text"]:
                raise ValueError("duplicate/stale frozen E04 A0")
            baseline[qid] = record
            origins[qid] = dict(phase=phase, path=str(paths[1].resolve()), sha256=sha_file(paths[1]),
                                run_path=str(paths[2].resolve()), run_sha256=sha_file(paths[2]))
    validate_replay_queries(queries, originals)
    if set(baseline) != set(originals):
        raise ValueError("missing E04 A0 baseline")
    dev_queries = [q for q in queries if original_phases[q["query_id"]] == "dev"]
    backend, adapter, old_log, manifest, units, unit_map, _, source_audit = e04.prepare_inputs(dev_queries, "dev")
    if len(units) != 65475 or len({u["file_id"] for u in units}) != 9639:
        raise ValueError("P1 must retain complete 9639/65475 population")
    for query in queries:
        original = baseline[query["query_id"]]
        stages = original["stages"]
        for key,maximum in (("bm25",100),("dense",100),("rrf_union",200),("rrf_top100",100),("rerank_candidates",100),("rerank",100)):
            e04.validate_ranked(stages[key], unit_map, maximum)
        scores = {row["unit_id"]:row["score"] for row in stages["rerank"]}
        rebuilt = e04.build_record(query, "A0", [stages["bm25"], stages["dense"]], scores, unit_map, adapter, timing={}, provenance={})
        assert_baseline_reproduction(rebuilt, original)
    cohort = read_json(args.queries.parent/"cohort.json")
    if len(cohort["rows"]) != 24 or len({r["file_id"] for r in cohort["rows"]}) != 24:
        raise ValueError("cohort requires 24 unique documents/units")
    sources, authors_units = {}, {}
    for name in ("prefix_inputs_p1.jsonl", "prefix_inputs_p2.jsonl"):
        for row in read_jsonl(args.queries.parent/name):
            uid, fid = row["unit"]["unit_id"], row["file_id"]
            if uid in authors_units or fid in sources or canonical(row["unit"]) != canonical(unit_map.get(uid)) or sha_text(row["full_source_text"]) != row["source_sha256"]:
                raise ValueError("prefix author source/unit input differs")
            sources[fid], authors_units[uid] = row["full_source_text"], row["unit"]
    if set(authors_units) != {r["unit_id"] for r in cohort["rows"]}:
        raise ValueError("prefix author population differs from cohort")
    approved = validate_prefixes(read_jsonl(args.prefixes), read_jsonl(args.reviews), cohort, unit_map, sources)
    return queries, baseline, origins, backend, adapter, old_log, manifest, units, unit_map, approved, source_audit


def score_binding(query, unit, approved, manifest_sha, runtime, inputs):
    prefix = approved.get(unit["unit_id"])
    return dict(query_id=query["query_id"], query_text_sha256=sha_text(query["text"]), unit_id=unit["unit_id"],
                file_id=unit["file_id"], source_sha256=unit["source_sha256"],
                indexed_text_sha256=sha_text(unit["text"]), indexed_text=unit["text"],
                prefix_sha256=sha_text(prefix["prefix_text"]) if prefix else None,
                prefix_profile="E02-extractive-v1" if prefix else None,
                manifest_sha256=manifest_sha, runtime=runtime, experiment_inputs=inputs)


def dose_record(record, approved):
    return dict(selected_in_rerank=sum(row["unit_id"] in approved for row in record["stages"]["rerank"]),
                selected_top5_unit_ids=[row["unit_id"] for row in record["files"][:5] if row["unit_id"] in approved],
                background_top5_unit_ids=[row["unit_id"] for row in record["files"][:5] if row.get("prefix")],
                background_top20_unit_ids=[row["unit_id"] for row in record["files"] if row.get("prefix")])


def run(args):
    assert_new_output(args.output)
    output_path = args.output.resolve()
    if not output_path.is_relative_to(OUT.resolve()):
        raise ValueError("output must remain within this E02 output directory")
    cache = validate_cache_path(args.cache)
    if cache.exists() and any(cache.iterdir()):
        raise FileExistsError("fresh real query/overlay encoding requires empty new cache: "+str(cache))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started, models = time.perf_counter(), None
    log_path, partial_path = Path(str(args.output)+".run.json"), Path(str(args.output)+".partial")
    pool_path = Path(str(args.output)+".score_pool.jsonl")
    tracked = [Path(__file__), args.queries, args.prefixes, args.reviews,
               args.queries.parent/"cohort.json", args.queries.parent/"input_freeze.json",
               args.queries.parent/"prefix_quality.json",
               args.queries.parent/"prefix_inputs_p1.jsonl", args.queries.parent/"prefix_inputs_p2.jsonl"]
    log = dict(status="partial", arms=list(ARMS), query_count=22, completed_queries=0, result_rows=0,
               source_population=9639, searchable_units=65475, configuration=CONFIGURATION,
               cache=str(cache), network="local_files_only; no paid API", actual_p1_inference=True,
               evaluation="diagnostic_replay; old 22 E04 inputs; not independent confirmation")
    save_json(log_path, log)
    try:
        input_hashes = {str(path.resolve()):sha_file(path) for path in tracked}
        log["input_sha256"] = input_hashes
        e04 = frozen_e04()
        queries, baseline, origins, backend, adapter, old_log, manifest, units, unit_map, approved, source_audit = load_replay(args, e04)
        overlay = make_overlay(units, approved)
        overlay_map = {unit["unit_id"]:unit for unit in overlay}
        changed_units = [unit for unit in overlay if unit["unit_id"] in approved]
        log.update(candidate_units=24, approved_units=len(approved), rejected_units=24-len(approved),
                   changed_units=len(changed_units), overlay_unit_ids=[u["unit_id"] for u in changed_units],
                   source_audit=source_audit, baseline_origins=origins,
                   runner_sha256=e04.BACKEND_SHA, adapter_sha256=e04.ADAPTER_SHA, e04_experiment_sha256=E04_CODE_SHA,
                   manifest_sha256=e04.MANIFEST_SHA, base_ordered_text_sha256=backend.ordered_text_sha(units),
                   overlay_ordered_text_sha256=backend.ordered_text_sha(overlay), baseline_reproduction_count=len(queries))
        save_json(log_path, log)
        model_args = e04.make_model_args(args.output, old_log)
        model_args.cache = cache
        emit("model_load_start", approved_units=len(approved), cache=str(cache))
        models = backend.LocalModels(model_args)
        e04.validate_models(models, old_log)
        runtime = e04.runtime_binding(old_log)
        log["runtime_binding"] = runtime
        log["parameters"] = {k:str(v) if isinstance(v,Path) else v for k,v in vars(model_args).items()}
        seed = e04.seed_document_cache(old_log, manifest, units, models, backend)
        log["document_cache_seed"] = seed
        # The inherited audit is explicitly a frozen cache hit, never new inference.
        seed_meta = read_json(cache/(seed["key"]+".json"))
        if any(row.get("truncated") for row in seed_meta["token_audit"]):
            raise ValueError("frozen base embedding token limit exceeded")
        base_vectors = models.encode(units, "document", "structured")
        if not models.log["cache_events"][-1].get("hit") or models.log["cache_events"][-1].get("key") != seed["key"]:
            raise ValueError("base vectors must use the verified seed cache")
        query_texts = [backend.QUERY_INSTRUCTION+q["text"] for q in queries]
        log["query_token_preflight"] = audit_inputs(models.embed_tokenizer, query_texts, [q["query_id"] for q in queries],
                model_args.max_length, models.token_handle, stage="query_embedding")
        query_vectors = models.encode(queries, "query", "E02_shared_queries")
        if models.log["cache_events"][-1].get("hit"):
            raise ValueError("query vectors require fresh actual encoding")
        if changed_units:
            changed_bindings = [score_binding(dict(query_id="document_overlay",text=""),unit,approved,e04.MANIFEST_SHA,runtime,input_hashes) for unit in changed_units]
            log["overlay_token_preflight"] = audit_inputs(models.embed_tokenizer, [u["text"] for u in changed_units],
                [u["unit_id"] for u in changed_units], model_args.max_length, models.token_handle,
                stage="overlay_embedding", bindings=changed_bindings)
            changed_vectors = models.encode(changed_units, "document", "E02_overlay")
            if models.log["cache_events"][-1].get("hit"):
                raise ValueError("overlay vectors require fresh actual encoding")
        else:
            changed_vectors = models.np.empty((0,base_vectors.shape[1]), dtype="float32")
        p1_vectors, positions = overlay_vectors(base_vectors, units, changed_units, changed_vectors, models.np)
        log["overlay_vector_rows"] = positions
        log["vector_operation"] = dict(base_origin="hash_verified_frozen_document_cache", base_inference_performed=False,
            new_document_encoding_rows=len(changed_units), unchanged_document_reencoding_rows=0,
            actual_query_encoding_rows=len(queries), overlay_array_sha256=hashlib.sha256(p1_vectors.tobytes(order="C")).hexdigest(),
            base_array_sha256=hashlib.sha256(base_vectors.tobytes(order="C")).hexdigest(), shape=list(p1_vectors.shape), dtype=str(p1_vectors.dtype))
        sys.path.insert(0, str(model_args.project_src.resolve()))
        from retrieval.sparse import RetrievalDocument, SparseRetrievalIndex
        emit("p1_full_bm25_build_start", units=len(overlay))
        t = time.perf_counter()
        index = SparseRetrievalIndex([RetrievalDocument(unit_id=u["unit_id"],case_ids=(u["case_id"],),text=u["text"],source="structured",weight=1.0) for u in overlay], k1=1.5,b=0.75)
        index_seconds = time.perf_counter()-t
        log["bm25"] = dict(units=len(overlay),k1=1.5,b=0.75,weight=1.0,rebuilt=True,seconds=index_seconds)
        save_json(log_path, log)
        with partial_path.open("x",encoding="utf-8") as output, pool_path.open("x",encoding="utf-8") as pool:
            for qi,query in enumerate(queries):
                qid, query_started = query["query_id"], time.perf_counter()
                emit("query_start", query_id=qid, index=qi+1, total=len(queries))
                original = baseline[qid]
                p0 = copy.deepcopy(original)
                p0.update(arm="P0",configuration=dict(CONFIGURATION),timing=dict(routes_reused=True,rerank_seconds=0.0,
                    old_real_inference_timing=original["timing"],new_gpu_inference_performed=False),
                    provenance=dict(frozen_e04_a0=origins[qid],baseline_exact_reproduction=True,experiment_inputs=input_hashes,
                                    runtime_binding=runtime,returned_context="unchanged frozen V2 context"))
                assert_baseline_reproduction(p0, original)
                routes, timing = e04.confirmation_routes(models,index,query_vectors[qi],p1_vectors,overlay,query)
                candidates = e04.weighted_rrf(routes,[1,1],k=60,top_k=200)[:100]
                if len(candidates) != 100:
                    raise ValueError("P1 requires actual rerank100 candidates")
                candidate_units = [overlay_map[row["unit_id"]] for row in candidates]
                bindings = [score_binding(query,unit,approved,e04.MANIFEST_SHA,runtime,input_hashes) for unit in candidate_units]
                token_summary = audit_inputs(models.rerank_tokenizer,[query["text"]]*len(candidates),
                    [row["unit_id"] for row in candidates],model_args.max_length,models.token_handle,
                    stage="rerank",pairs=[u["text"] for u in candidate_units],query_id=qid,bindings=bindings)
                t = time.perf_counter()
                computed = models.rerank(query["text"],candidates,overlay_map,"E02_P1",qid)
                gpu_seconds = time.perf_counter()-t
                scores = validate_computed_scores(candidates,computed)
                p1 = e04.build_record(query,"A0",routes,scores,unit_map,adapter,
                    timing=dict(**timing,rerank_seconds=gpu_seconds,bm25_index_seconds=index_seconds,new_gpu_inference_performed=True,
                                query_embedding_shared=True,document_overlay_shared=True),
                    provenance=dict(routes_origin="actual_local_full_bm25_and_bge_with_overlay",rerank_origin="actual_local_gpu_rerank100",
                                    experiment_inputs=input_hashes,runtime_binding=runtime,token_preflight=token_summary,
                                    base_ordered_text_sha256=log["base_ordered_text_sha256"],overlay_ordered_text_sha256=log["overlay_ordered_text_sha256"]))
                p1["arm"] = "P1"
                # Aggregate the immutable original units, then decorate only the actual winning unit.
                for key in ("files","cases"):
                    p1[key] = [decorate_hit(hit,unit_map,approved,"P1") for hit in p1[key]]
                p2 = copy.deepcopy(p0)
                p2.update(arm="P2",provenance=dict(p0["provenance"],returned_context="P0 winners plus approved extractive prefix",ranking_identical_to_p0=True))
                for key in ("files","cases"):
                    p2[key] = [decorate_hit(hit,unit_map,approved,"P2") for hit in p2[key]]
                if canonical(p2["stages"]) != canonical(p0["stages"]):
                    raise ValueError("P2 stages must equal P0")
                for arm,record,index_map,known_prefixes in (("P0",p0,unit_map,{}),("P1",p1,overlay_map,approved)):
                    for hit in record["stages"]["rerank"]:
                        uid = hit["unit_id"]
                        pool.write(canonical(dict(query_id=qid,arm=arm,unit_id=uid,score=hit["score"],
                            binding=score_binding(query,index_map[uid],known_prefixes,e04.MANIFEST_SHA,runtime,input_hashes),
                            provenance=dict(kind="frozen_E04_A0_real_rerank" if arm=="P0" else "actual_local_gpu_rerank100",
                                            baseline=origins[qid] if arm=="P0" else None,P2_uses_P0_scores=arm=="P0"))).decode("utf-8")+"\n")
                pool.flush()
                for record in (p0,p1,p2):
                    record["provenance"].update(score_pool_path=str(pool_path.resolve()),score_pool_arm="P0" if record["arm"]=="P2" else record["arm"],
                        manifest_sha256=e04.MANIFEST_SHA,approved_prefix_units=len(approved),query_text_sha256=sha_text(query["text"]))
                    record["prefix_dose"] = dose_record(record,approved)
                    record["timing"]["shared_query_wall_seconds"] = time.perf_counter()-query_started
                    record["timing"]["shared_time_accounting"] = "P0/P2 reuse frozen inference; new query embeddings/overlay/BM25 shared across P1 queries"
                    output.write(canonical(record).decode("utf-8")+"\n")
                    log["result_rows"] += 1
                output.flush()
                log.update(completed_queries=qi+1,elapsed_seconds=time.perf_counter()-started,models=models.log)
                save_json(log_path,log)
                emit("query_complete",query_id=qid,real_rerank_units=len(candidates),gpu_seconds=gpu_seconds,
                     top5_background_p1=len(p1["prefix_dose"]["background_top5_unit_ids"]),top5_background_p2=len(p2["prefix_dose"]["background_top5_unit_ids"]))
        if log["result_rows"] != 66 or log["completed_queries"] != 22:
            raise RuntimeError("incomplete E02 replay records")
        for path,expected in input_hashes.items():
            check_sha(path,expected)
        check_sha(E04_CODE,E04_CODE_SHA)
        check_sha(e04.BACKEND,e04.BACKEND_SHA)
        check_sha(e04.ADAPTER,e04.ADAPTER_SHA)
        if args.output.exists():
            raise FileExistsError("output appeared during run")
        partial_path.rename(args.output)
        log.update(status="complete",output_path=str(args.output.resolve()),output_sha256=sha_file(args.output),
                   score_pool_sha256=sha_file(pool_path),elapsed_seconds=time.perf_counter()-started)
    except BaseException as exc:
        log.update(status="failure",error=f"{type(exc).__name__}: {exc}",elapsed_seconds=time.perf_counter()-started)
        save_json(Path(str(args.output)+".failure.json"),log)
        emit("run_failure",error=log["error"],result_rows=log["result_rows"])
        raise
    finally:
        if models is not None:
            models.token_handle.close()
            log["models"] = models.log
            token_path = Path(str(args.output)+".token_audit.jsonl")
            if token_path.exists():
                log["token_audit_sha256"] = sha_file(token_path)
        save_json(log_path,log)
    emit("run_complete",rows=log["result_rows"],output=str(args.output),seconds=log["elapsed_seconds"])
    return log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries",type=Path,required=True)
    parser.add_argument("--prefixes",type=Path,required=True)
    parser.add_argument("--reviews",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--cache",type=Path,default=HERE/"vector_cache")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
