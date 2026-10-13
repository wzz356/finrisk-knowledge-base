"""Frozen-ranking display controls using this round's actual B0 results only."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]


def check_model_hit(old, new):
    for key in ("file_id", "unit_id", "rank", "score", "indexed_text", "case_id", "case_ids", "source_sha256"):
        if key in old and old[key] != new.get(key):
            raise ValueError("Display-only changed model/ranking field: " + key)


def restore_model_fields(old, new):
    result = copy.deepcopy(new)
    if new.get("scope_profile"):
        result["display_scoped_index_text"] = new["indexed_text"]
        result["display_representation_id"] = new["representation_id"]
        result["display_only"] = True
    for key in ("indexed_text", "representation_id", "indexed_source_text", "indexed_source_spans"):
        if key in old:
            result[key] = copy.deepcopy(old[key])
        else:
            result.pop(key, None)
    check_model_hit(old, result)
    return result


def main():
    target = OUT / "display_results.jsonl"
    sidecar = OUT / "display_results.jsonl.run.json"
    if target.exists() or sidecar.exists():
        raise FileExistsError("Refusing to overwrite display experiment")
    frozen = json.loads((OUT / "execution_freeze.json").read_text(encoding="utf-8"))
    for path, digest in frozen["files_sha256"].items():
        if sha(Path(path)) != digest:
            raise ValueError("Frozen dependency changed: " + path)
    spec = importlib.util.spec_from_file_location("display_frozen_runner", WORK / "experiment.py")
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    run = json.loads((OUT / "results.jsonl.run.json").read_text(encoding="utf-8"))
    if run["status"] != "complete" or sha(OUT / "results.jsonl") != run["output_sha256"]:
        raise ValueError("Actual parent run not complete/bound")
    sources, units = {}, {}
    for name in ("prefix_inputs_p1.jsonl", "prefix_inputs_p2.jsonl"):
        for row in rows(ROOT / "outputs/FinRisk_E02小批量实验_20261013" / name):
            sources[row["file_id"]] = row["full_source_text"]
            units[row["unit"]["unit_id"]] = row["unit"]
    approved = runner.validate_scope_units(rows(OUT / "scope_units.jsonl"), rows(OUT / "scope_review.jsonl"),
                                           runner.read_json(ROOT / "outputs/FinRisk_E02小批量实验_20261013/cohort.json"),
                                           units, sources, sha(OUT / "scope_units.jsonl"))
    bases = [r for r in rows(OUT / "results.jsonl") if r["arm"] == "B0"]
    if len(bases) != 42:
        raise ValueError("Missing parent B0 queries")
    records, exposure = [], {"D1": 0, "D2": 0}
    for base in bases:
        records.append(copy.deepcopy(base))
        for arm, decoration_arm in (("D1", "S1"), ("D2", "C2")):
            record = copy.deepcopy(base)
            record["arm"] = arm
            for kind in ("files", "cases"):
                record[kind] = [restore_model_fields(h, runner.decorate_hit(h, units, approved, decoration_arm, sources))
                                if h["unit_id"] in approved else copy.deepcopy(h) for h in base[kind]]
                for old, new in zip(base[kind], record[kind]):
                    check_model_hit(old, new)
            if record["stages"] != base["stages"]:
                raise ValueError("Display control changed retrieval stages")
            exposure[arm] += sum(bool(h.get("scope_profile")) for h in record["files"][:5])
            record["display_only_control"] = {"parent_arm": "B0", "new_model_calls": 0,
                                               "parent_results_sha256": run["output_sha256"],
                                               "model_indexed_text_kept": True, "scope_source_review": "same reviewed source display"}
            records.append(record)
    target.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for r in records), encoding="utf-8")
    log = {"status": "complete", "queries": 42, "rows": 126, "arms": ["B0", "D1", "D2"], "scoped_top5_slots": exposure,
           "actual_new_model_calls": 0, "source": "same-round actual GPU B0; rank/score/model indexed text unchanged",
           "output_sha256": sha(target), "parent_results_sha256": run["output_sha256"],
           "parent_run_sha256": sha(OUT / "results.jsonl.run.json"), "code_sha256": sha(Path(__file__)),
           "scope_units_sha256": sha(OUT / "scope_units.jsonl"), "scope_review_sha256": sha(OUT / "scope_review.jsonl"),
           "design_sha256": sha(OUT / "display_design.md"), "human_approved": False}
    sidecar.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "rows": 126, "exposure": exposure, "new_model_calls": 0}))


if __name__ == "__main__":
    main()
