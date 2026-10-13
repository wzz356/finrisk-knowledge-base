"""Assign additional unseen displays to the same query's original reviewer."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"


def main():
    folder = OUT / "judgments"
    assignments = json.loads((folder / "split_manifest.json").read_text(encoding="utf-8"))["parts"]
    remaining = [json.loads(s) for s in (OUT / "display_evaluation/remaining_pool.jsonl").read_text(encoding="utf-8").splitlines() if s.strip()]
    manifests = []
    for part in assignments:
        values = []
        for p in remaining:
            if p["query_id"] not in part["query_ids"]:
                continue
            if p["needs_file_judgment"]:
                raise ValueError("Same-round whole-source grade not reused")
            row = {key: p[key] for key in ("pair_id", "query_id", "file_id", "query_text", "full_source_text")}
            row["needs_file_judgment"] = False
            row["contexts"] = [{"context_id": c["context_id"], "text": c["text"]} for c in p["contexts"]]
            values.append(row)
        path = folder / f"display_input_p{part['part']}.jsonl"
        if path.exists():
            raise FileExistsError(path)
        path.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in values), encoding="utf-8")
        manifests.append({"part": part["part"], "pairs": len(values), "contexts": sum(len(p["contexts"]) for p in values),
                          "source_chars": sum(len(p["full_source_text"]) for p in values), "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (folder / "display_split_manifest.json").write_text(json.dumps(manifests, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifests, ensure_ascii=False))


if __name__ == "__main__":
    main()
