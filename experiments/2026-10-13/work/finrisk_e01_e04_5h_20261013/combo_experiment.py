"""Selected weighted-retrieval plus source-scoped return, without new inference."""
import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("combo_display_helpers", HERE / "display_experiment.py")
D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)
OUT, ROOT = D.OUT, D.ROOT


def main():
    target = OUT / "combo_results.jsonl"
    if target.exists():
        raise FileExistsError(target)
    run = json.loads((OUT / "results.jsonl.run.json").read_text(encoding="utf-8"))
    if run["status"] != "complete" or D.sha(OUT / "results.jsonl") != run["output_sha256"]:
        raise ValueError("Actual parent run binding differs")
    spec = importlib.util.spec_from_file_location("combo_frozen_runner", HERE / "experiment.py")
    R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
    sources, units = {}, {}
    for name in ("prefix_inputs_p1.jsonl", "prefix_inputs_p2.jsonl"):
        for row in D.rows(ROOT / "outputs/FinRisk_E02小批量实验_20261013" / name):
            sources[row["file_id"]] = row["full_source_text"]
            units[row["unit"]["unit_id"]] = row["unit"]
    approved = R.validate_scope_units(D.rows(OUT / "scope_units.jsonl"), D.rows(OUT / "scope_review.jsonl"),
                                      R.read_json(ROOT / "outputs/FinRisk_E02小批量实验_20261013/cohort.json"),
                                      units, sources, D.sha(OUT / "scope_units.jsonl"))
    parents = D.rows(OUT / "results.jsonl")
    bases = [r for r in parents if r["arm"] in {"B0", "W4"}]
    weighted = [r for r in parents if r["arm"] == "W4"]
    if len(bases) != 84 or len(weighted) != 42:
        raise ValueError("Parent population incomplete")
    exposure = 0
    for parent in weighted:
        result = copy.deepcopy(parent); result["arm"] = "WD"
        for kind in ("files", "cases"):
            result[kind] = [D.restore_model_fields(h, R.decorate_hit(h, units, approved, "S1", sources))
                            if h["unit_id"] in approved else copy.deepcopy(h) for h in parent[kind]]
            for old, new in zip(parent[kind], result[kind]):
                D.check_model_hit(old, new)
        if result["stages"] != parent["stages"]:
            raise ValueError("Combination changed original W4 stages")
        exposure += sum(bool(h.get("scope_profile")) for h in result["files"][:5])
        result["display_only_control"] = {"parent_arm": "W4", "new_model_calls": 0, "model_indexed_text_kept": True,
                                           "parent_results_sha256": run["output_sha256"], "post_selection_used_inputs": True}
        bases.append(result)
    target.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for r in bases), encoding="utf-8")
    metadata = {"status": "complete", "rows": 126, "queries": 42, "arms": ["B0", "W4", "WD"], "scope_top5_slots": exposure,
                "new_model_calls": 0, "output_sha256": D.sha(target), "parent_results_sha256": run["output_sha256"],
                "code_sha256": D.sha(Path(__file__)), "display_helper_sha256": D.sha(HERE / "display_experiment.py"),
                "design_sha256": D.sha(OUT / "combo_design.md"), "scope_units_sha256": D.sha(OUT / "scope_units.jsonl"),
                "scope_review_sha256": D.sha(OUT / "scope_review.jsonl"), "human_approved": False, "independent_confirmation": False}
    (OUT / "combo_results.jsonl.run.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(bases), "scope_top5_slots": exposure, "new_model_calls": 0}))


if __name__ == "__main__":
    main()
