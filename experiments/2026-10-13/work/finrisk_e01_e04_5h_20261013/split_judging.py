"""Remove method metadata and balance whole queries across three model reviewers."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"


def main():
    source = OUT / "evaluation/blind_judgment_pool.jsonl"
    pool = [json.loads(s) for s in source.read_text(encoding="utf-8").splitlines() if s.strip()]
    grouped = defaultdict(list)
    for p in pool:
        row = {key: p[key] for key in ("pair_id", "query_id", "file_id", "query_text", "full_source_text")}
        row["contexts"] = [{"context_id": c["context_id"], "text": c["text"]} for c in p["contexts"]]
        grouped[p["query_id"]].append(row)
    weight = {qid: sum(len(p["full_source_text"]) + len(p["query_text"]) + sum(len(c["text"]) for c in p["contexts"]) for p in values) for qid, values in grouped.items()}
    buckets, totals = [[] for _ in range(3)], [0, 0, 0]
    for qid in sorted(grouped, key=lambda q: (-weight[q], q)):
        index = min(range(3), key=lambda i: (totals[i], i))
        buckets[index].extend(sorted(grouped[qid], key=lambda p: p["pair_id"]))
        totals[index] += weight[qid]
    folder = OUT / "judgments"
    folder.mkdir(exist_ok=True)
    parts = []
    for i, values in enumerate(buckets, 1):
        path = folder / f"input_p{i}.jsonl"
        if path.exists():
            raise FileExistsError(path)
        path.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in values), encoding="utf-8")
        parts.append({"part": i, "pairs": len(values), "contexts": sum(len(p["contexts"]) for p in values),
                      "query_ids": sorted({p["query_id"] for p in values}), "source_chars": sum(len(p["full_source_text"]) for p in values),
                      "reading_chars": totals[i-1], "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {"pool_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "parts": parts,
                "methods_ranks_author_targets_hidden": True, "visible_intervention_format": True,
                "same_query_all_methods_same_reviewer": True, "human_approved": False}
    (folder / "split_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(parts, ensure_ascii=False))


if __name__ == "__main__":
    main()
