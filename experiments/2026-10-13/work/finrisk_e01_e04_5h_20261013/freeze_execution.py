"""Freeze actual reviewed inputs, implementations and old dependencies before GPU."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    target = OUT / "execution_freeze.json"
    if target.exists():
        raise FileExistsError(target)
    initial = json.loads((OUT / "input_freeze.json").read_text(encoding="utf-8"))
    files = {}
    for name, expected in initial["protected_input_sha256"].items():
        p = ROOT / name
        if sha(p) != expected:
            raise ValueError("Protected input changed: " + name)
        files[str(p.resolve())] = expected
    for cache, snapshot in initial["old_cache_snapshots"].items():
        folder = ROOT / cache
        now = {p.name: sha(p) for p in folder.iterdir() if p.is_file()}
        if now != snapshot:
            raise ValueError("Old cache changed: " + cache)
        files.update({str((folder / name).resolve()): digest for name, digest in now.items()})
    for name in ("queries.jsonl", "new_queries.jsonl", "scope_units.jsonl", "scope_review.jsonl", "mechanism_cards.jsonl", "mechanism_review.jsonl", "design.md", "input_freeze.json", "token_preflight.json", "评分规则.md", "source_review_notes.md"):
        p = OUT / name
        files[str(p.resolve())] = sha(p)
    preflight = json.loads((OUT / "token_preflight.json").read_text(encoding="utf-8"))
    if preflight["over_limit"]:
        raise ValueError("Oversized model input")
    for name in ("experiment.py", "test_experiment.py", "evaluate.py", "test_evaluate.py", "code_review.md", "tests_root_runtime.log"):
        p = WORK / name
        files[str(p.resolve())] = sha(p)
    for path in (ROOT / "work/finrisk_e04_pilot_20261012/experiment.py", ROOT / "work/finrisk_e04_pilot_20261012/evaluate.py", ROOT / "work/finrisk_v2_20261012/eval_v2.py", ROOT / "work/finrisk_retrieval_20261012/runner.py", ROOT / "work/finrisk_v2_20261012/run_v2.py"):
        files[str(path.resolve())] = sha(path)
    value = {"files_sha256": files, "regression_tests_passed": 32, "real_model_run_started": False,
             "query_population": {"diagnostic_replay": 22, "new_business_risk": 10, "new_condition_boundary": 10},
             "arms": ["B0", "S1", "C2", "W4", "M3"], "card_top_k": 2,
             "start_utc": "2026-10-12 18:16:39 UTC", "deadline_utc": "2026-10-12 23:16:39 UTC",
             "paid_project_api": False, "human_approved": False}
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "frozen_files": len(files), "sha256": sha(target)}))


if __name__ == "__main__":
    main()
