"""Freeze query inputs and old dependencies without changing prior artifacts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"
E02 = ROOT / "outputs/FinRisk_E02小批量实验_20261013"
E04 = ROOT / "outputs/FinRisk_E04小批量实验_20261012"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def main():
    for name in ("queries.jsonl", "input_freeze.json"):
        if (OUT / name).exists():
            raise FileExistsError(name)
    manifests = {}
    for previous in (E02, E04):
        path = previous / "delivery_manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for r in manifest["output_files"] + manifest["work_code_notes_and_logs"]:
            if sha(ROOT / r["path"]) != r["sha256"]:
                raise ValueError("Old delivery changed: " + r["path"])
        manifests[path.relative_to(ROOT).as_posix()] = sha(path)
    old = rows(E02 / "queries.jsonl")
    new = rows(OUT / "new_queries.jsonl")
    assert len(old) == 22 and len(new) == 20
    queries = old + new
    assert len({q["query_id"] for q in queries}) == 42
    assert len({q["text"] for q in queries}) == 42
    assert sum(q["query_role"] == "risk" for q in new) == 10
    (OUT / "queries.jsonl").write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in queries), encoding="utf-8")
    protected = json.loads((E02 / "input_freeze.json").read_text(encoding="utf-8"))["protected_input_sha256"]
    protected.update(manifests)
    for path in (E02 / "prefix_inputs_p1.jsonl", E02 / "prefix_inputs_p2.jsonl", E02 / "prefixes.jsonl", E02 / "cohort.json"):
        protected[path.relative_to(ROOT).as_posix()] = sha(path)
    for name, expected in protected.items():
        if sha(ROOT / name) != expected:
            raise ValueError("Protected input drift: " + name)
    caches = {}
    for name in ("finrisk_retrieval_20261012", "finrisk_e04_pilot_20261012", "finrisk_e02_pilot_20261013"):
        cache = ROOT / "work" / name / "vector_cache"
        caches[cache.relative_to(ROOT).as_posix()] = {p.name: sha(p) for p in cache.iterdir() if p.is_file()}
    value = {"protected_input_sha256": protected, "old_cache_snapshots": caches,
             "query_sha256": sha(OUT / "queries.jsonl"), "new_queries_sha256": sha(OUT / "new_queries.jsonl"),
             "design_sha256": sha(OUT / "design.md"), "replay_queries": 22, "new_business_queries": 20,
             "query_count": 42, "human_gold": False, "event_independence_verified": False}
    (OUT / "input_freeze.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "query_count": 42, "protected_inputs": len(protected), "cache_files": sum(map(len, caches.values()))}))


if __name__ == "__main__":
    main()
