"""Summarize only validated judgments and actual recorded exposure."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def count(rr):
    hits = [h for r in rr for h in r["top5"]]
    return {"queries": len(rr), "denominator": 5 * len(rr), "useful_contexts": sum(h["context_help_grade"] >= 2 for h in hits),
            "covered_queries": sum(r["context_coverage_at5"] for r in rr), "context_warnings": sum(h["context_misleading_risk"] for h in hits),
            "useful_files": sum(h["help_grade"] >= 2 for h in hits), "file_warnings": sum(h["misleading_risk"] for h in hits),
            "mean_context_grade": sum(h["context_help_grade"] for h in hits) / (5 * len(rr)),
            "scope_slots": sum(bool(h["returned_hit"].get("scope_profile")) for h in hits),
            "prefix_slots": sum(bool(h["returned_hit"].get("prefix")) for h in hits)}


def main():
    main = rows(OUT / "evaluation/per_query_metrics.jsonl")
    display = rows(OUT / "display_evaluation/per_query_metrics.jsonl")
    combo = rows(OUT / "combo_evaluation/per_query_metrics.jsonl")
    all_rows = main + [r for r in display if r["arm"] != "B0"] + [r for r in combo if r["arm"] == "WD"]
    arm_rows = {a: [r for r in all_rows if r["arm"] == a] for a in ("B0", "S1", "C2", "W4", "M3", "D1", "D2", "WD")}
    counts = {a: {"all": count(rr), "new_business": count([r for r in rr if r["query_id"].startswith("N")]),
                  "replay": count([r for r in rr if not r["query_id"].startswith("N")]),
                  "new_risk": count([r for r in rr if r["group"] == "new_business_risk"]),
                  "new_boundary": count([r for r in rr if r["group"] == "new_condition_boundary"])} for a, rr in arm_rows.items()}
    base = {r["query_id"]: r for r in arm_rows["B0"]}
    deltas = {}
    for a, rr in arm_rows.items():
        if a == "B0":
            continue
        changed = []
        for r in rr:
            b = base[r["query_id"]]
            diff = count([r])["useful_contexts"] - count([b])["useful_contexts"]
            warnings = count([r])["context_warnings"] - count([b])["context_warnings"]
            if diff or warnings or r["context_coverage_at5"] != b["context_coverage_at5"]:
                changed.append({"query_id": r["query_id"], "query_text": r["query_text"], "useful_delta": diff, "warning_delta": warnings,
                                "coverage_before": b["context_coverage_at5"], "coverage_after": r["context_coverage_at5"],
                                "before": [{"file_id": h["file_id"], "grade": h["context_help_grade"], "warning": h["context_misleading_risk"], "quote": h["evidence_quote"], "reason": h["context_reason"]} for h in b["top5"]],
                                "after": [{"file_id": h["file_id"], "grade": h["context_help_grade"], "warning": h["context_misleading_risk"], "quote": h["evidence_quote"], "reason": h["context_reason"]} for h in r["top5"]]})
        deltas[a] = changed
    value = {"kind": "mechanical_aggregation_of_same_round_model_judgments", "counts": counts, "per_query_deltas": deltas,
             "uncovered_queries": {a: [r["query_id"] for r in rr if not r["context_coverage_at5"]] for a, rr in arm_rows.items()}}
    (OUT / "analysis.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all": {a: c["all"] for a, c in counts.items()}, "changed": {a: [{k: d[k] for k in ("query_id", "useful_delta", "warning_delta", "coverage_before", "coverage_after")} for d in values] for a, values in deltas.items()}, "uncovered": value["uncovered_queries"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
