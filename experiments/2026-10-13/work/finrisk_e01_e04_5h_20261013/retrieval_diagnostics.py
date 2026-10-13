"""Mechanical retrieval exposure and timing only; never semantic scoring."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"


def main():
    results = [json.loads(s) for s in (OUT / "results.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
    run = json.loads((OUT / "results.jsonl.run.json").read_text(encoding="utf-8"))
    by = {(r["query_id"], r["arm"]): r for r in results}
    arms = {}
    for arm in ("B0", "S1", "C2", "W4", "M3"):
        rr = [r for r in results if r["arm"] == arm]
        changed = [r["query_id"] for r in rr if [(h["file_id"], h["unit_id"]) for h in r["files"][:5]] != [(h["file_id"], h["unit_id"]) for h in by[r["query_id"], "B0"]["files"][:5]]]
        decorated = [{"query_id": r["query_id"], "file_id": h["file_id"], "unit_id": h["unit_id"], "rank": h["rank"], "prefix": bool(h.get("prefix"))} for r in rr for h in r["files"][:5] if h.get("scope_profile")]
        arms[arm] = {"queries": len(rr), "top5_slots": sum(len(r["files"][:5]) for r in rr),
                     "changed_top5_queries": len(changed), "changed_query_ids": changed,
                     "scoped_top5_slots": len(decorated), "prefix_top5_slots": sum(d["prefix"] for d in decorated),
                     "scoped_hits": decorated,
                     "old_selected_top5_slots": sum(len(r["dose"]["scope_top5_unit_ids"]) for r in rr),
                     "mechanism_support_top5_slots": sum(len(r["dose"]["mechanism_support_top5_unit_ids"]) for r in rr),
                     "rerank_pool_seconds": sum(r["timing"]["rerank_seconds"] for r in rr),
                     "newly_scored_units": sum(r["timing"]["newly_scored_units"] for r in rr),
                     "same_run_reused_units": sum(r["timing"]["reused_units"] for r in rr)}
    counts = Counter()
    with (OUT / "results.jsonl.score_pool.jsonl").open(encoding="utf-8") as f:
        for s in f:
            counts[json.loads(s)["provenance"]["kind"]] += 1
    value = {"kind": "mechanical_exposure_not_helpfulness", "arms": arms,
             "real_run_seconds": run["elapsed_seconds"], "vector_operation": run["vector_operation"],
             "score_counts": dict(counts), "card_selection_patterns": run["mechanism_card_selection_patterns"],
             "all_actual_model_truncated_inputs": sum(x["truncated_inputs"] for x in run["models"]["truncation"])}
    (OUT / "retrieval_diagnostics.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"seconds": value["real_run_seconds"], "scores": dict(counts), "truncations": value["all_actual_model_truncated_inputs"],
                      "arms": {a: {k: d[k] for k in ("changed_top5_queries", "scoped_top5_slots", "prefix_top5_slots", "old_selected_top5_slots")} for a, d in arms.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
