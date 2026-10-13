"""Read-only verification of real run, fresh grades and protected old artifacts."""
import hashlib
import importlib.util
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"
ARMS = ("B0", "S1", "C2", "W4", "M3")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def obj(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows(path):
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]


def check(test, reason):
    if not test:
        raise ValueError(reason)


def main():
    initial = obj(OUT / "input_freeze.json")
    frozen = obj(OUT / "execution_freeze.json")
    for name, digest in frozen["files_sha256"].items():
        check(sha(name) == digest, "Frozen input/code changed: " + name)
    for name, digest in initial["protected_input_sha256"].items():
        check(sha(ROOT / name) == digest, "Old protected input changed: " + name)
    for cache, snapshot in initial["old_cache_snapshots"].items():
        now = {p.name: sha(p) for p in (ROOT / cache).iterdir() if p.is_file()}
        check(now == snapshot, "Old cache changed: " + cache)
    old_delivered = 0
    for name in ("FinRisk_E02小批量实验_20261013", "FinRisk_E04小批量实验_20261012"):
        manifest = obj(ROOT / "outputs" / name / "delivery_manifest.json")
        for r in manifest["output_files"] + manifest["work_code_notes_and_logs"]:
            check(sha(ROOT / r["path"]) == r["sha256"], "Old artifact changed: " + r["path"])
            old_delivered += 1
    run = obj(OUT / "results.jsonl.run.json")
    results = rows(OUT / "results.jsonl")
    queries = {q["query_id"]: q for q in rows(OUT / "queries.jsonl")}
    check(run["status"] == "complete" and len(results) == 210, "Real run incomplete")
    check(Counter(r["arm"] for r in results) == {a: 42 for a in ARMS}, "Wrong five-arm population")
    check(run["completed_queries"] == 42 and run["searchable_units"] == 65475 and run["source_population"] == 9639, "Population changed")
    for key, name in (("output_sha256", "results.jsonl"), ("score_pool_sha256", "results.jsonl.score_pool.jsonl"), ("token_audit_sha256", "results.jsonl.token_audit.jsonl")):
        check(run[key] == sha(OUT / name), "Real run sidecar changed: " + name)
    for name, digest in run["input_sha256"].items():
        check(sha(name) == digest, "Actual run dependency changed: " + name)
    check(all(v["truncated_inputs"] == 0 for v in run["models"]["truncation"]), "Actual token truncation")
    v = run["vector_operation"]
    check(v["actual_query_encoding_rows"] == 42 and v["query_encoding_calls"] == 1 and v["unchanged_document_reencoding_rows"] == 0, "Unexpected encoding operation")
    check(not v["old_query_vectors_used"] and not v["old_reranker_scores_used"], "Previous inference used unexpectedly")
    by = {(r["query_id"], r["arm"]): r for r in results}
    for qid in queries:
        for arm in ("W4", "M3"):
            check(all(by[qid, arm]["stages"][route] == by[qid, "B0"]["stages"][route] for route in ("bm25", "dense")), "Control routes changed: " + qid)
        for arm in ARMS:
            r = by[qid, arm]
            check(r["text"] == queries[qid]["text"] and len(r["stages"]["rerank_candidates"]) == 100, "Input or rerank dose changed")
    scope = {r["unit_id"]: r for r in rows(OUT / "scope_units.jsonl")}
    originals = {}
    for old in ("prefix_inputs_p1.jsonl", "prefix_inputs_p2.jsonl"):
        originals.update({r["unit"]["unit_id"]: r["unit"] for r in rows(ROOT / "outputs/FinRisk_E02小批量实验_20261013" / old)})
    for r in results:
        for h in r["files"] + r["cases"]:
            if h.get("scope_profile"):
                s = scope[h["unit_id"]]
                check(s["scope_status"] != "ambiguous_unchanged", "Ambiguous scope decorated")
                expected = s["indexed_text"]
                if r["arm"] == "C2" and s["prefix_text"]:
                    expected = s["prefix_text"] + "\n" + expected
                check(h["indexed_text"] == expected and h["original_unit_text"] == originals[h["unit_id"]]["text"], "Wrong displayed winner view")
    score_counts, shared = Counter(), {}
    with (OUT / "results.jsonl.score_pool.jsonl").open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line); binding = row["binding"]
            check(row["pool_key"] == hashlib.sha256(canonical(binding)).hexdigest(), "Score binding hash differs")
            check(binding["query_text_sha256"] == text_sha(queries[row["query_id"]]["text"]), "Score query differs")
            key = row["pool_key"]
            if key in shared:
                check(shared[key] == row["score"], "Shared same-input score changed")
            else:
                shared[key] = row["score"]
            score_counts[row["provenance"]["kind"]] += 1
    check(sum(score_counts.values()) == 21000, "Score pool lacks rerank100 for every arm/input")
    check(score_counts["actual_local_gpu_rerank"] == len(shared), "Actual/shared score counts differ")
    spec = importlib.util.spec_from_file_location("delivery_fiveh_eval", WORK / "evaluate.py")
    e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
    sources = e.load_sources()
    pool, provenance = e.build_pool(queries, results, sources)
    check(pool == e.validate_pool(rows(OUT / "evaluation/blind_judgment_pool.jsonl")), "Fresh evaluation pool differs")
    check(provenance == rows(OUT / "evaluation/judgment_provenance.jsonl"), "Fresh slot provenance differs")
    check(not rows(OUT / "evaluation/remaining_pool.jsonl"), "Missing semantic grades")
    judgments = e.unique(rows(OUT / "evaluation/validated_judgments.jsonl"), "pair_id", "judgments")
    fresh, perquery = e.compute_metrics(queries, results, pool, judgments)
    saved = obj(OUT / "evaluation/metrics.json")
    check(saved["status"] == "complete" and saved["metrics"] == fresh["metrics"] and saved["strata"] == fresh["strata"], "Metric recomputation differs")
    check(perquery == rows(OUT / "evaluation/per_query_metrics.jsonl"), "Per-query recomputation differs")
    check(saved["judgments_sha256"] == sha(OUT / "evaluation/validated_judgments.jsonl"), "Grade file changed")
    for name, digest in saved["input_sha256"].items():
        check(sha(name) == digest, "Evaluation dependency changed")
    value = {"status": "passed", "verified_at_utc": datetime.now(timezone.utc).isoformat(), "source_documents": 9639,
             "searchable_units": 65475, "queries": 42, "result_records": 210,
             "protected_input_files": len(initial["protected_input_sha256"]), "old_delivered_files_unchanged": old_delivered,
             "old_cache_files_unchanged": sum(map(len, initial["old_cache_snapshots"].values())),
             "frozen_execution_files_unchanged": len(frozen["files_sha256"]), "model_graded_pairs": len(pool),
             "model_graded_contexts": sum(len(p["contexts"]) for p in pool.values()), "pending_grades": 0,
             "real_rerank_inputs": len(shared), "same_run_shared_scores": score_counts["same_run_exact_model_input_shared"],
             "token_truncations": 0, "human_approved": False, "application_modified": False,
             "scope": "Source/completeness/recomputation checks, not human semantic acceptance or full-corpus adoption."}
    (OUT / "verification.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
