"""Targeted transparency check for two general cross-product analogy positions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"


def main():
    analysis = json.loads((OUT / "analysis.json").read_text(encoding="utf-8"))
    all_rows = []
    for phase, allowed in (("display_evaluation", {"D1", "D2"}), ("combo_evaluation", {"WD"})):
        all_rows += [json.loads(s) for s in (OUT / phase / "per_query_metrics.jsonl").read_text(encoding="utf-8").splitlines() if s.strip() and json.loads(s)["arm"] in allowed]
    checks = {}
    for arm in ("D1", "D2", "WD"):
        r = next(r for r in all_rows if r["arm"] == arm and r["query_id"] == "N014")
        debated = [h for h in r["top5"] if h["file_id"] in {"F001987", "F001988"} and h["context_help_grade"] >= 2]
        original = analysis["counts"][arm]
        covered = int(any(h["context_help_grade"] >= 2 for h in r["top5"] if h not in debated))
        checks[arm] = {"excluded_positions": len(debated), "files": [h["file_id"] for h in debated],
                       "all_useful_after_exclusion": original["all"]["useful_contexts"] - len(debated), "all_denominator": 210,
                       "all_covered_after_exclusion": original["all"]["covered_queries"] - r["context_coverage_at5"] + covered,
                       "new_useful_after_exclusion": original["new_business"]["useful_contexts"] - len(debated), "new_denominator": 100,
                       "new_covered_after_exclusion": original["new_business"]["covered_queries"] - r["context_coverage_at5"] + covered}
    output = {"kind": "targeted_exclusion_sensitivity_not_replacement_grades", "original_judgments_changed": False,
              "reason": "N014医疗险完整披露输入新增两处有用是贷款话术与条款对比的泛化核查帮助，不是医疗险免责/等待期的直接案例；同事件多主体来源不等于两份独立证据。",
              "scope": "Only these two debated general analogies excluded; not a consistent all-items strict-mechanism benchmark.", "checks": checks}
    (OUT / "sensitivity.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == "__main__":
    main()
