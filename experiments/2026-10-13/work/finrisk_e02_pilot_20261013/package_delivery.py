"""Create a byte-level manifest for the completed offline E02 pilot."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
OUT = ROOT / "outputs/FinRisk_E02小批量实验_20261013"
TARGET = OUT / "delivery_manifest.json"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def entry(path):
    return {"path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size, "sha256": sha(path)}


def main():
    if TARGET.exists():
        raise FileExistsError("Refusing to overwrite the delivery manifest")
    verification = json.loads((OUT / "verification.json").read_text(encoding="utf-8"))
    decision = json.loads((OUT / "decision.json").read_text(encoding="utf-8"))
    if verification["status"] != "passed" or verification["pending_judgments"] != 0:
        raise ValueError("Delivery verification is incomplete")
    if "PASS" not in (WORK / "report_review.md").read_text(encoding="utf-8"):
        raise ValueError("Independent report review is missing")
    output_files = [entry(p) for p in sorted(OUT.rglob("*")) if p.is_file() and p != TARGET]
    work_files = [entry(p) for p in sorted(WORK.iterdir())
                  if p.is_file() and p.suffix in {".py", ".md", ".log"}]
    manifest = {
        "status": "complete_offline_pilot",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_documents": verification["source_documents"],
        "structured_units": verification["structured_units"],
        "prefix_units": verification["prefix_units"],
        "queries": verification["queries"],
        "result_records": verification["result_records"],
        "new_real_rerank_scores": verification["new_real_rerank_scores"],
        "frozen_real_score_reuse": verification["frozen_real_score_reuse"],
        "model_graded_pairs": verification["source_verified_pairs"],
        "model_graded_contexts": verification["source_verified_contexts"],
        "regression_tests": {"passed": 39, "failed": 0, "skipped": 0,
                             "evidence": entry(WORK / "tests_root_runtime.log")},
        "adoption_decision": decision,
        "human_approved": False,
        "application_modified": False,
        "github_pushed_this_pilot": False,
        "independent_holdout": False,
        "scope": "Completed diagnostic pilot; semantic scope fixes remain before full adoption.",
        "output_files": output_files,
        "work_code_notes_and_logs": work_files,
        "excluded": ["manifest itself", "vector/model caches", "virtual environments", "temporary test directories"],
        "dependency_note": "Original V2/E04 dependencies remain at their frozen paths; see input_freeze.json and execution_freeze.json.",
    }
    TARGET.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    saved = json.loads(TARGET.read_text(encoding="utf-8"))
    for row in saved["output_files"] + saved["work_code_notes_and_logs"]:
        path = ROOT / row["path"]
        if path.stat().st_size != row["bytes"] or sha(path) != row["sha256"]:
            raise ValueError("Manifest verification failed: " + row["path"])
    print(json.dumps({"status": "passed", "output_files": len(output_files),
                      "work_files": len(work_files), "manifest_sha256": sha(TARGET)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
