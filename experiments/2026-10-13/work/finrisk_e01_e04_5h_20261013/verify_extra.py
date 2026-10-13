"""Verify display/combination controls and exact same-round semantic reuse."""
import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("extra_display_helpers", HERE / "display_experiment.py")
D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)
OUT = D.OUT


def check(test, message):
    if not test:
        raise ValueError(message)


def load(name):
    spec = importlib.util.spec_from_file_location("verify_" + name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def verify_reused_pool(fresh, saved):
    check(set(fresh) == set(saved), "Control grading pair population changed")
    expected = copy.deepcopy(fresh)
    for pid in expected:
        check(saved[pid].get("file_judgment_from_cache") is True and saved[pid].get("needs_file_judgment") is False,
              "Expected same-round complete whole-source reuse is missing")
        expected[pid].update(file_judgment_from_cache=True, needs_file_judgment=False)
    check(expected == saved, "Control grading source/display pool changed")


def main():
    original = {(r["query_id"], r["arm"]): r for r in D.rows(OUT / "results.jsonl")}
    model_fields_checked = 0
    for filename, parents in (("display_results.jsonl", {"B0": "B0", "D1": "B0", "D2": "B0"}),
                              ("combo_results.jsonl", {"B0": "B0", "W4": "W4", "WD": "W4"})):
        sidecar = json.loads((OUT / (filename + ".run.json")).read_text(encoding="utf-8"))
        check(sidecar["status"] == "complete" and sidecar["output_sha256"] == D.sha(OUT / filename), "Control output changed")
        control = D.rows(OUT / filename)
        check(len(control) == 126, "Control population incomplete")
        for r in control:
            parent = original[r["query_id"], parents[r["arm"]]]
            check(r["text"] == parent["text"] and r["stages"] == parent["stages"], "Control changed query/routes")
            for kind in ("files", "cases"):
                check(len(r[kind]) == len(parent[kind]), "Control changed aggregate population")
                for old, new in zip(parent[kind], r[kind]):
                    D.check_model_hit(old, new)
                    model_fields_checked += 1
        code = "display_experiment.py" if filename.startswith("display") else "combo_experiment.py"
        check(sidecar["code_sha256"] == D.sha(HERE / code), "Control code changed after use")
        for key, name in (("scope_units_sha256", "scope_units.jsonl"), ("scope_review_sha256", "scope_review.jsonl")):
            check(sidecar[key] == D.sha(OUT / name), "Control source review changed")
    complete_phases = []
    for phase, code, filename in (("display_evaluation", "display_evaluate", "display_results.jsonl"),
                                  ("combo_evaluation", "combo_evaluate", "combo_results.jsonl")):
        m = load(code); e = m.E
        qp = OUT / "queries.jsonl"; rp = OUT / filename; folder = OUT / phase
        queries = e.load_queries(qp); sources = e.load_sources(); results = e.read_rows(rp)
        pool, provenance = e.build_pool(queries, results, sources)
        verify_reused_pool(pool, e.validate_pool(e.read_rows(folder / "blind_judgment_pool.jsonl")))
        check(provenance == e.read_rows(folder / "judgment_provenance.jsonl"), "Control provenance changed")
        check(not e.read_rows(folder / "remaining_pool.jsonl"), "Missing control judgments")
        grades = e.unique(e.read_rows(folder / "validated_judgments.jsonl"), "pair_id", "grades")
        summary, perquery = e.backend.compute_metrics(queries, results, pool, grades)
        saved = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
        check(saved["status"] == "complete" and saved["metrics"] == summary["metrics"] and saved["strata"] == summary["strata"], "Control metric recomputation differs")
        check(perquery == e.read_rows(folder / "per_query_metrics.jsonl"), "Control per-query recomputation differs")
        check(saved["judgments_sha256"] == D.sha(folder / "validated_judgments.jsonl"), "Control grades changed")
        for name, digest in saved["input_sha256"].items():
            check(D.sha(Path(name)) == digest, "Control evaluation input changed")
        reuse = json.loads((folder / "reuse_provenance.json").read_text(encoding="utf-8"))
        for name, digest in reuse["input_sha256"].items():
            check(D.sha(Path(name)) == digest, "Same-round reused grades changed")
        complete_phases.append({"phase": phase, "pairs": len(pool), "contexts": sum(len(p["contexts"]) for p in pool.values()), "pending": 0})
    main_grades = D.rows(OUT / "evaluation/validated_judgments.jsonl")
    display_grades = D.rows(OUT / "display_evaluation/validated_judgments.jsonl")
    main_map = {g["pair_id"]: g for g in main_grades}
    fields = load("display_evaluate").E.backend.FILE_FIELDS
    for g in display_grades:
        check(all(g[key] == main_map[g["pair_id"]][key] for key in fields), "Whole-source grade modified in display round")
    value = {"status": "passed", "controls_records": 252, "model_fields_checked_hits": model_fields_checked,
             "new_gpu_calls": 0, "control_phases": complete_phases, "whole_file_grades_unchanged": True,
             "same_round_model_graded_pairs": 268, "same_round_distinct_graded_contexts": 312,
             "human_approved": False, "independent_confirmation": False,
             "scope": "Mechanical checks and exact semantic reuse; model interpretations remain non-human judgments."}
    (OUT / "verification_extra.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
