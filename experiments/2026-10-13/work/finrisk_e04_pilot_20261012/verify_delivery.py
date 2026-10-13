"""Read-only E04 input/result checks; writes only new delivery audit artifacts."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
OUT = ROOT / "outputs/FinRisk_E04小批量实验_20261012"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def obj(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def rows(path):
    return [json.loads(s) for s in Path(path).read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def check(value, message):
    if not value:
        raise ValueError(message)


def close(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def main():
    frozen = obj(OUT / "input_freeze.json")
    for name, expected in frozen["protected_input_sha256"].items():
        check(sha(ROOT / name) == expected, f"protected SHA changed: {name}")
    check(sha(OUT / "dev_queries.jsonl") == frozen["dev_queries_sha256"], "dev queries changed")
    implementation = obj(OUT / "execution_freeze.json")
    for name, expected in implementation["implementation_sha256"].items():
        check(sha(WORK / name) == expected, f"implementation changed: {name}")
    check(sha(ROOT / "work/finrisk_v2_20261012/eval_v2.py") == implementation["legacy_evaluation_helper_sha256"], "legacy evaluation changed")
    old_cache = ROOT / "work/finrisk_retrieval_20261012/vector_cache"
    cache_now = {p.name: sha(p) for p in old_cache.iterdir() if p.is_file()}
    check(cache_now == implementation["old_cache_readonly_snapshot"], "old cache changed")
    for name, expected in obj(OUT / "confirmation_freeze.json")["files_sha256"].items():
        check(sha(OUT / name) == expected, f"confirmation freeze changed: {name}")
    selection_sha = sha(OUT / "selection.json")
    check(selection_sha == "71daddb3d3a75373dd76c6a09d6dc6abf33f98ef38c68d8e7bf5c55ae2b06bff", "selection changed")
    selection = obj(OUT / "selection.json")
    check(selection["selected_arm"] == "A0" and selection["confirmation_arms"] == ["A0", "A3"], "selection arm drift")

    spec = importlib.util.spec_from_file_location("delivery_e04_eval", WORK / "evaluate.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    sources = evaluator.load_sources()
    check(len(sources) == 9639, "source count changed")
    all_phase_rows = {}
    audits = {}
    for phase, nq, nr, npair, expected_score in (("dev", 12, 48, 77, {"frozen_same_input_rerank": 1200, "actual_local_gpu_rerank": 938}),
                                               ("confirmation", 10, 20, 55, {"actual_local_gpu_rerank": 1735})):
        qpath = OUT / (phase + "_queries.jsonl")
        rpath = OUT / (phase + "_results.jsonl")
        phase_out = OUT / (phase + "_evaluation")
        queries = evaluator.load_queries(qpath)
        result_rows = rows(rpath)
        all_phase_rows[phase] = result_rows
        run = obj(Path(str(rpath) + ".run.json"))
        check(run["status"] == "complete" and len(queries) == nq and len(result_rows) == nr, f"{phase}: run/count incomplete")
        check(run["completed_queries"] == nq and run["result_rows"] == nr, f"{phase}: run log count drift")
        for key, path in (("queries_sha256", qpath), ("output_sha256", rpath),
                          ("score_pool_sha256", Path(str(rpath) + ".score_pool.jsonl")),
                          ("token_audit_sha256", Path(str(rpath) + ".token_audit.jsonl"))):
            check(run[key] == sha(path), f"{phase}: {key} drift")
        if phase == "confirmation":
            check(run["selection"]["sha256"] == selection_sha, "confirmation selection SHA mismatch")
        score_rows = rows(Path(str(rpath) + ".score_pool.jsonl"))
        score_counts = dict(Counter(v["provenance"]["kind"] for v in score_rows))
        check(score_counts == expected_score, f"{phase}: score provenance counts changed")
        check(len({(v["query_id"], v["unit_id"]) for v in score_rows}) == len(score_rows), "duplicate score pair")
        truncation = run["models"]["truncation"]
        check(all(v["truncated_inputs"] == 0 for v in truncation), f"{phase}: unexpected truncation")
        pool, provenance = evaluator.build_pool(queries, result_rows, sources)
        saved_pool = evaluator.validate_pool(rows(phase_out / "blind_judgment_pool.jsonl"))
        check(pool.keys() == saved_pool.keys(), f"{phase}: saved pool pair mismatch")
        for pid in pool:
            for key in ("query_id", "query_text", "query_sha256", "file_id", "source_sha256", "full_source_text", "contexts", "query_task", "scoring_instructions"):
                check(pool[pid][key] == saved_pool[pid][key], f"{phase}: saved pool/source mismatch: {pid}:{key}")
        check(provenance == rows(phase_out / "judgment_provenance.jsonl"), f"{phase}: provenance mismatch")
        judgments = evaluator.unique(rows(phase_out / "validated_judgments.jsonl"), "pair_id", "judgment")
        check(len(pool) == npair and set(pool) == set(judgments), f"{phase}: incomplete judgments")
        fresh, perquery = evaluator.compute_metrics(queries, result_rows, pool, judgments)
        saved = obj(phase_out / "metrics.json")
        check(saved["status"] == "complete" and saved["human_judgments"] == 0, f"{phase}: invalid status")
        check(close(fresh["metrics"], saved["metrics"]), f"{phase}: metrics not reproducible")
        check(close(perquery, rows(phase_out / "per_query_metrics.jsonl")), f"{phase}: per-query metrics drift")
        check(not rows(phase_out / "remaining_pool.jsonl"), f"{phase}: pending grades")
        check(saved["judgments_sha256"] == sha(phase_out / "validated_judgments.jsonl"), f"{phase}: judgments SHA mismatch")
        for name, expected in saved["input_sha256"].items():
            check(sha(name) == expected, f"{phase}: metric input SHA changed: {name}")
        role_by_id = {v["query_id"]: v.get("query_role", v["group"]) for v in queries.values()}
        metric_counts = []
        for arm in run["arms"]:
            selected = [v for v in perquery if v["arm"] == arm]
            for role in ["all"] + sorted(set(role_by_id.values())):
                rr = selected if role == "all" else [v for v in selected if role_by_id[v["query_id"]] == role]
                hits = [h for v in rr for h in v["top5"]]
                metric_counts.append({"arm": arm, "role": role, "queries": len(rr), "denominator": len(rr)*5,
                                      "context_useful": sum(h["context_help_grade"] >= 2 for h in hits),
                                      "context_covered_queries": sum(v["context_coverage_at5"] for v in rr),
                                      "context_warnings": sum(h["context_misleading_risk"] for h in hits),
                                      "file_useful": sum(h["help_grade"] >= 2 for h in hits),
                                      "file_warnings": sum(h["misleading_risk"] for h in hits)})
        audits[phase] = {"queries": nq, "result_records": nr, "query_file_pairs": npair,
                         "contexts": sum(len(p["contexts"]) for p in pool.values()), "pending_pairs": 0,
                         "score_provenance_counts": score_counts, "truncated_inputs": 0,
                         "elapsed_seconds": run["elapsed_seconds"], "metric_counts": metric_counts}

    old = {(r["query_id"]): r for r in rows(ROOT / "outputs/FinRisk_知识库V2_20261012/retrieval/all9639_results.jsonl")
           if r["arm"] == "rrf_rerank" and r["corpus"] == "structured"}
    a0 = [r for r in all_phase_rows["dev"] if r["arm"] == "A0"]
    for r in a0:
        original = old[r["query_id"]]
        check(r["files"] == original["files"] and r["cases"] == original["cases"], "A0 output not exact")
        check(all(r["stages"][k] == v for k, v in original["stages"].items()), "A0 stages not exact")
    audits["dev"]["a0_exact_reproduction_queries"] = len(a0)
    dev_by = {(r["query_id"], r["arm"]): r for r in all_phase_rows["dev"]}
    same = sum(dev_by[(qid, "A2")]["files"] == dev_by[(qid, "A3")]["files"] and
               dev_by[(qid, "A2")]["cases"] == dev_by[(qid, "A3")]["cases"] for qid in {r["query_id"] for r in a0})
    check(same == 12, "A2/A3 expected exact identity failed")
    audits["dev"]["a2_a3_identical_outputs_queries"] = same
    confirm_by = {(r["query_id"], r["arm"]): r for r in all_phase_rows["confirmation"]}
    changed = []
    for qid in sorted({r["query_id"] for r in all_phase_rows["confirmation"]}):
        x = [(h["file_id"], h["text"]) for h in confirm_by[(qid, "A0")]["files"][:5]]
        y = [(h["file_id"], h["text"]) for h in confirm_by[(qid, "A3")]["files"][:5]]
        if x != y:
            changed.append(qid)
    audits["confirmation"]["changed_top5_queries"] = changed
    old_q = rows(ROOT / "outputs/FinRisk_召回实验_20261012/queries.jsonl")
    old_ids = {fid for q in old_q for fid in q.get("known_positive_file_ids", [])} | {a["file_id"] for q in old_q for a in q.get("anchor_evidence", [])}
    cq = rows(OUT / "confirmation_queries.jsonl")
    reference_ids = {a["file_id"] for q in cq for a in q["anchor_evidence"]}
    check(len(reference_ids) == 10 and not reference_ids & old_ids, "source IDs overlap")
    check(not {sources[x]["full_text"] for x in reference_ids} & {sources[x]["full_text"] for x in old_ids}, "source texts overlap")
    quote_count = 0
    for q in cq:
        for a in q["anchor_evidence"]:
            check(a["quote"] in sources[a["file_id"]]["full_text"], "confirmation anchor quote mismatch")
            quote_count += 1
    output = {"status": "passed", "verified_at_utc": datetime.now(timezone.utc).isoformat(),
              "protected_files_unchanged": len(frozen["protected_input_sha256"]),
              "old_cache_files_unchanged": len(cache_now), "frozen_implementation_files_unchanged": 4,
              "confirmation_selection_sha256": selection_sha, "source_documents": 9639,
              "confirmation_reference_sources": 10, "old_anchor_sources": len(old_ids),
              "source_id_and_exact_text_overlap": 0, "confirmation_anchor_quotes_checked": quote_count,
              "phase_audits": audits, "human_approved": False,
              "limits": ["Semantic grades are model opinions; not official gold or human approval.",
                         "Method/rank blind; some graders saw query-author task metadata, recorded in notes.",
                         "Source ID/text exclusion does not prove globally independent events."]}
    (OUT / "verification.json").write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "protected_unchanged": output["protected_files_unchanged"],
                      "old_cache_unchanged": len(cache_now), "dev": audits["dev"], "confirmation": audits["confirmation"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
