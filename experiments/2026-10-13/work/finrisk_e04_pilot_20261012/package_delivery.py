"""Record hashes of E04 artifacts; do not copy caches, weights, or old inputs."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
OUT = ROOT / "outputs/FinRisk_E04小批量实验_20261012"


def record(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return {"path": path.relative_to(ROOT).as_posix(), "size_bytes": path.stat().st_size, "sha256": h.hexdigest()}


required = ["实验报告.md", "失败样例.md", "README.md", "复跑说明.md", "verification.json"]
for name in required:
    if not (OUT / name).is_file():
        raise ValueError("missing delivery artifact: " + name)
audit = json.loads((OUT / "verification.json").read_text(encoding="utf-8"))
if audit["status"] != "passed":
    raise ValueError("verification is not passed")
files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "delivery_manifest.json")
work_files = sorted(p for p in WORK.iterdir() if p.is_file() and p.suffix in (".py", ".md", ".log"))
manifest = {"status": "complete_offline_pilot", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_documents": 9639, "structured_units": 65475, "development_queries": 12,
            "confirmation_queries": 10, "result_records": 68, "query_file_pairs": 132,
            "context_variants": 132, "evaluation": "model_review_only", "human_approved": False,
            "selected_arm": "A0", "confirmation_arms": ["A0", "A3"],
            "application_defaults_changed": False, "github_published_this_pilot": False,
            "protected_input_hashes": "input_freeze.json", "implementation_and_old_cache_hashes": "execution_freeze.json",
            "verification": "verification.json", "tests": {"run": 55, "passed": 54, "skipped": 1, "failed": 0,
            "log": "work/finrisk_e04_pilot_20261012/tests_delivery_runtime.log"},
            "output_files": [record(p) for p in files], "work_code_notes_and_logs": [record(p) for p in work_files],
            "not_packaged": ["model weights", "virtual environment", "vector caches", "original source corpus", "textbook PDF", "360 reserved source bodies"],
            "next_experiment": "Recommend evidence-backed contextual prefix pilot; not started."}
target = OUT / "delivery_manifest.json"
target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
# Check all recorded bytes again, excluding this self-referential manifest.
for r in manifest["output_files"] + manifest["work_code_notes_and_logs"]:
    if record(ROOT / r["path"]) != r:
        raise ValueError("artifact changed during manifest creation: " + r["path"])
print(json.dumps({"status": manifest["status"], "output_files": len(files), "work_files": len(work_files), "manifest_sha256": record(target)["sha256"]}, ensure_ascii=False))
