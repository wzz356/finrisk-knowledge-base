"""Offline metric recomputation. No API calls or credential access."""
import json
from collections import Counter
from pathlib import Path

from pool_evaluation import evaluate_pool
from evaluate_formal_risk import score_predictions


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def main():
    root = Path(__file__).resolve().parents[1]
    methods = ("BM25", "BGE", "RRF", "DeepSeek")
    rankings = {m: rows(root / f"rankings_{m}_main24.jsonl") for m in methods}
    actual = evaluate_pool(rows(root / "closed_queries.jsonl"), rankings,
                           read(root / "reference_pool.json"), rows(root / "qrels_new_final.jsonl"))
    saved = read(root / "full_pool_metrics.json")
    for method in methods:
        assert actual["methods"][method]["summary"] == saved["methods"][method]["summary"], method
    assert actual["outside_random_diagnostics"] == saved["outside_random_diagnostics"]
    master = rows(root / "evaluation_reference/master.jsonl")
    labels = {item["risk_tag"] for item in read(root / "official_labels.json")}
    packets = rows(root / "api_risk/risk_inputs.jsonl")
    comparison = read(root / "risk_comparison.json")
    sources = {d["file_id"]: d["text"] for d in rows(root / "reference_source_documents.jsonl")}
    arm_summaries = {}
    for arm in ("no_retrieval", "RAG"):
        predictions = rows(root / f"api_risk/predictions_{arm}.jsonl")
        score = score_predictions(master, predictions, labels)
        saved_risk = read(root / f"risk_metrics_{arm}.json")
        assert all(saved_risk[k] == v for k, v in score.items()), arm
        given = {p["query_id"]: {e["file_id"]: e["text"] for e in p["evidence"]}
                 for p in packets if p["arm"] == arm}
        context_counts, source_counts = Counter(), Counter()
        for prediction in predictions:
            for citation in prediction["citations"]:
                fid, quote = citation["file_id"], citation["source_quote"]
                context = given[prediction["query_id"]]
                for docs, counts in ((context, context_counts), (sources, source_counts)):
                    status = "unknown_source" if fid not in docs else "present" if quote in docs[fid] else "absent"
                    counts[status] += 1
        quote_audit = comparison["arms"][arm]["quotation_audit"]
        for counts, scope in ((context_counts, "exact_context"), (source_counts, "full_source")):
            assert {s: counts[s] for s in ("present", "absent", "unknown_source")} == quote_audit[scope]["citation_literal_counts"]
        arm_summaries[arm] = {k: score[k] for k in ("state_accuracy", "risk_binary", "labels")}
    print(json.dumps({"status": "passed", "retrieval_methods": list(methods),
                     "retrieval_queries": 24, "risk_queries_per_arm": 90,
                     "actual_context_and_source_quote_counts_match": True,
                     "risk": arm_summaries, "network_or_api_used": False,
                     "global_recall_reported": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
