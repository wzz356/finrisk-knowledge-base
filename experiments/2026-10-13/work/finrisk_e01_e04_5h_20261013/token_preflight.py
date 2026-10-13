"""Read-only tokenizer checks before freezing model inputs; no model inference."""
import json
from pathlib import Path
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def main():
    old = json.loads((ROOT / "outputs/FinRisk_知识库V2_20261012/retrieval/all9639_results.jsonl.run.json").read_text(encoding="utf-8"))
    params = old["parameters"]
    embed = AutoTokenizer.from_pretrained(str(params["embedding_model"]), local_files_only=True, trust_remote_code=False)
    rerank = AutoTokenizer.from_pretrained(str(params["reranker_model"]), local_files_only=True, trust_remote_code=False)
    queries = rows(OUT / "queries.jsonl")
    texts = []
    for s in rows(OUT / "scope_units.jsonl"):
        if s["scope_status"] == "ambiguous_unchanged":
            continue
        texts.append(("S1", s["file_id"], s["indexed_text"]))
        texts.append(("C2", s["file_id"], s["prefix_text"] + "\n" + s["indexed_text"] if s["prefix_text"] else s["indexed_text"]))
    for card in rows(OUT / "mechanism_cards.jsonl"):
        texts.append(("card", card["card_id"], card["retrieval_text"]))
    checks = []
    for view, fid, text in texts:
        length = len(embed(text, truncation=False)["input_ids"])
        pairs = [] if view == "card" else [(len(rerank(q["text"], text, truncation=False)["input_ids"]), q["query_id"]) for q in queries]
        worst = max(pairs, default=(0, None))
        checks.append({"view": view, "source": fid, "embedding_tokens": length,
                       "worst_rerank_tokens": worst[0], "worst_query_id": worst[1],
                       "over_limit": length > 512 or worst[0] > 512})
    output = {"kind": "tokenizer_only_preflight_not_inference", "rows": len(checks), "checks": checks,
              "over_limit": sum(c["over_limit"] for c in checks), "max_embedding_tokens": max(c["embedding_tokens"] for c in checks),
              "max_rerank_tokens": max(c["worst_rerank_tokens"] for c in checks)}
    (OUT / "token_preflight.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in output.items() if k != "checks"}, ensure_ascii=False))
    for c in checks:
        if c["over_limit"]:
            print(json.dumps(c, ensure_ascii=False))


if __name__ == "__main__":
    main()
