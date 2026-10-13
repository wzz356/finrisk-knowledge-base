"""Seal this offline pilot and provide a read-only byte verification entry point."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
OUT = ROOT / "outputs" / "FinRisk_E01-E04五小时实验_20261013"
MANIFEST = OUT / "delivery_manifest.json"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def inventory():
    paths = [path for path in OUT.rglob("*") if path.is_file() and path != MANIFEST]
    paths += [path for path in WORK.iterdir()
              if path.is_file() and path.suffix in {".py", ".md", ".log"}]
    paths.sort(key=lambda path: path.relative_to(ROOT).as_posix())
    records = []
    for path in paths:
        if path.is_symlink():
            raise ValueError(f"Symlink is not a sealed artifact: {path}")
        path.resolve().relative_to(ROOT.resolve())
        records.append({"path": path.relative_to(ROOT).as_posix(),
                        "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    return records


def validate_records(manifest):
    expected = manifest["files"]
    actual = inventory()
    if actual != expected:
        want = {record["path"]: record for record in expected}
        have = {record["path"]: record for record in actual}
        drift = [key for key in sorted(want.keys() | have.keys()) if want.get(key) != have.get(key)]
        raise ValueError("Delivery byte/inventory mismatch: " + ", ".join(drift[:20]))
    return {"status": "passed", "sealed_files": len(actual),
            "sealed_bytes": sum(record["size_bytes"] for record in actual),
            "manifest_sha256": sha256(MANIFEST)}


def build():
    if MANIFEST.exists():
        raise FileExistsError("Refusing to overwrite delivery_manifest.json; use --check.")
    primary = load_json(OUT / "verification.json")
    extra = load_json(OUT / "verification_extra.json")
    if primary["status"] != "passed" or extra["status"] != "passed":
        raise ValueError("Both actual verification stages must have passed.")
    if primary["pending_grades"] != 0 or any(phase["pending"] != 0 for phase in extra["control_phases"]):
        raise ValueError("Unfinished semantic judgments cannot be sealed as complete.")
    if primary["human_approved"] or extra["human_approved"]:
        raise ValueError("This model-judged experiment has no human approval.")
    for name in ["实验总报告.md", "完整方案.md", "样例对比.md", "复跑说明.md", "decision.json"]:
        if not (OUT / name).is_file():
            raise ValueError(f"Required delivery is missing: {name}")
    if not (WORK / "report_review.md").is_file():
        raise ValueError("Independent report review is missing.")
    records = []
    counts = {}
    for name in ["results.jsonl", "display_results.jsonl", "combo_results.jsonl"]:
        rows = [json.loads(line) for line in (OUT / name).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        counts[name] = len(rows)
        records.extend(rows)
    unique = {(row["arm"], row["query_id"]) for row in records}
    if list(counts.values()) != [210, 126, 126] or len(unique) != 336:
        raise ValueError("Unexpected result population; do not claim the planned experiment complete.")
    test_evidence = []
    for name, count in [("tests_root_runtime.log", 32), ("display_green_final.log", 2),
                        ("extra_verification_green.log", 2)]:
        path = WORK / name
        log = path.read_text(encoding="utf-8-sig")
        if f"Ran {count} tests" not in log or "\nOK" not in log:
            raise ValueError(f"Passing test evidence unavailable: {name}")
        test_evidence.append({"path": path.relative_to(ROOT).as_posix(),
                              "tests_passed": count, "sha256": sha256(path)})
    now = datetime.now(timezone.utc)
    started = datetime.fromisoformat("2026-10-12T18:16:39+00:00")
    deadline = datetime.fromisoformat("2026-10-12T23:16:39+00:00")
    manifest = {
        "schema": "finrisk_offline_pilot_delivery_v1",
        "status": "complete_offline_E01_E04_pilots",
        "completed_at_utc": now.isoformat(),
        "started_at_utc": started.isoformat(),
        "deadline_at_utc": deadline.isoformat(),
        "elapsed_seconds_at_seal": (now - started).total_seconds(),
        "within_five_hour_limit": now <= deadline,
        "source_documents": primary["source_documents"],
        "searchable_units": primary["searchable_units"],
        "query_inputs": primary["queries"],
        "result_record_counts": counts,
        "raw_records_including_parent_duplicates": len(records),
        "unique_query_arm_combinations": len(unique),
        "same_round_model_graded_pairs": extra["same_round_model_graded_pairs"],
        "same_round_distinct_graded_contexts": extra["same_round_distinct_graded_contexts"],
        "real_rerank_inputs": primary["real_rerank_inputs"],
        "same_run_shared_scores": primary["same_run_shared_scores"],
        "token_truncations": primary["token_truncations"],
        "regression_tests_passed_in_separate_recorded_runs": sum(item["tests_passed"] for item in test_evidence),
        "test_evidence": test_evidence,
        "human_approved": False,
        "application_modified": False,
        "production_default_changed": False,
        "github_pushed": False,
        "independent_combination_confirmation": False,
        "scope": "E01-E04 small pilot results, not all enhancement techniques, production deployment, full-corpus semantic acceptance or a human gold benchmark.",
        "excluded_from_package": ["model weights", "vector caches", "virtual environments", "unchanged previous corpora"],
        "dependency_pointer_files": ["input_freeze.json", "execution_freeze.json"],
        "files": inventory(),
    }
    with MANIFEST.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return validate_records(load_json(MANIFEST))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only: verify sealed artifact inventory, sizes and SHA256.")
    args = parser.parse_args()
    result = validate_records(load_json(MANIFEST)) if args.check else build()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
