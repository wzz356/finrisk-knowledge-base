"""Seal local demo artifacts; --check verifies bytes without modifying them."""
import argparse
import json
from datetime import datetime, timezone
import demo

MANIFEST = demo.OUT / "delivery_manifest.json"


def inventory():
    paths = [p for p in demo.OUT.rglob("*") if p.is_file() and p != MANIFEST]
    paths += [p for p in demo.WORK.iterdir() if p.is_file() and p.suffix in {".py", ".md", ".log"}]
    result = []
    for path in sorted(paths, key=lambda p: p.relative_to(demo.ROOT).as_posix()):
        if path.is_symlink():
            raise ValueError("Refusing symlink artifact")
        path.resolve().relative_to(demo.ROOT.resolve())
        result.append({"path": path.relative_to(demo.ROOT).as_posix(), "size_bytes": path.stat().st_size,
                       "sha256": demo.sha_file(path)})
    return result


def check():
    manifest = demo.read_json(MANIFEST)
    if manifest["files"] != inventory():
        raise ValueError("Sealed byte inventory differs")
    demo.assert_freeze(demo.OUT / "input_freeze.json")
    return {"status": "passed", "files": len(manifest["files"]), "bytes": sum(row["size_bytes"] for row in manifest["files"]),
            "manifest_sha256": demo.sha_file(MANIFEST)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        verified = demo.read_json(demo.OUT / "verification_final.json")
        if verified["status"] != "passed":
            raise ValueError("Final verification not passed")
        log = (demo.WORK / "tests_final_green.log").read_text(encoding="utf-8-sig")
        if "Ran 12 tests" not in log or "\nOK" not in log:
            raise ValueError("Passing test evidence missing")
        review = (demo.WORK / "review.md").read_text(encoding="utf-8-sig")
        if "最终结论：PASS" not in review:
            raise ValueError("Final independent review has not passed")
        demo.assert_freeze(demo.OUT / "input_freeze.json")
        demo.write_new(MANIFEST, {"schema": "finrisk_offline_demo_delivery_v1", "status": "complete_local_1_to_1_demo",
            "sealed_at_utc": datetime.now(timezone.utc).isoformat(), "inputs": 16, "source_documents": 9639,
            "indexed_units": 65475, "weights": [1, 1], "evidence_positions": 80, "scoped_positions": 3,
            "real_rerank_inputs": 1600, "tests_passed": 12, "independent_code_record_review": "passed",
            "human_approved": False, "independent_quality_gold": False, "application_modified": False,
            "github_pushed": False, "model_judgment_channel": "current_session_reading",
            "excluded": ["model weights", "vector caches", "virtual environments", "unchanged corpus dependencies"],
            "files": inventory()})
    print(json.dumps(check(), ensure_ascii=False))


if __name__ == "__main__":
    main()
