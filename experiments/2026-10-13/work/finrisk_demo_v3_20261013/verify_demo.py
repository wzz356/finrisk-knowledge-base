"""Recompute actual stage, source, display and judgment bindings without semantic grading."""
import copy
import csv
import json
from collections import Counter
import demo


def main(output_name="verification.json"):
    frozen = demo.assert_freeze(demo.OUT / "input_freeze.json")
    queries = demo.rows(demo.OUT / "queries.jsonl")
    query_map = {query["query_id"]: query for query in queries}
    actual = demo.rows(demo.OUT / "retrieval_results.jsonl")
    display = demo.rows(demo.OUT / "display_results.jsonl")
    packets = demo.rows(demo.OUT / "evidence_packets.jsonl")
    judgments = demo.rows(demo.OUT / "model_judgments.jsonl")
    log = demo.read_json(demo.OUT / "retrieval_results.jsonl.run.json")
    demo.check_parent_run(log, demo.OUT / "queries.jsonl", demo.OUT / "retrieval_results.jsonl")
    assert log["status"] == "complete" and log["output_sha256"] == demo.sha_file(demo.OUT / "retrieval_results.jsonl")
    assert log["queries_sha256"] == demo.sha_file(demo.OUT / "queries.jsonl")
    assert log["rrf"] == {"k": 60, "ranks_start": 1, "equal_weights": True, "route_top_k": 100, "union_max": 200, "rerank_top_k": 100}
    assert log["parameters"]["arms"] == ["rrf_rerank"]
    assert len(query_map) == len(actual) == len(display) == len(packets) == len(judgments) == 16
    assert {r["query_id"] for r in actual} == set(query_map)
    sources = demo.source_map()
    units, approved = demo.load_scope(sources)
    adapter = demo.module(demo.ADAPTER, "v3_verify_adapter")
    backend = adapter.backend()
    hit_checks = 0
    for old, new, packet in zip(actual, display, packets):
        assert old["query_id"] == new["query_id"] == packet["query_id"]
        assert old["text"] == query_map[old["query_id"]]["text"]
        stages = old["stages"]
        assert len(stages["bm25"]) == len(stages["dense"]) == len(stages["rrf_top100"]) == len(stages["rerank"]) == 100
        assert backend.rrf([stages["bm25"], stages["dense"]], k=60, top_k=200) == stages["rrf_union"]
        assert stages["rrf_union"][:100] == stages["rrf_top100"]
        assert {r["unit_id"] for r in stages["rrf_top100"]} == {r["unit_id"] for r in stages["rerank"]}
        assert sorted(stages["rerank"], key=lambda row: (-row["score"], row["unit_id"])) == stages["rerank"]
        cases, files = adapter.aggregate(stages["rerank"], units)
        assert files == old["files"] and cases == old["cases"]
        assert old["stages"] == new["stages"]
        for kind in ["files", "cases"]:
            assert len(old[kind]) == len(new[kind])
            for before, after in zip(old[kind], new[kind]):
                for key in ["file_id", "unit_id", "rank", "score", "indexed_text", "indexed_source_text", "indexed_source_spans", "case_ids", "case_id"]:
                    assert before.get(key) == after.get(key), key
                assert before["indexed_text"] == units[before["unit_id"]]["text"]
                assert demo.scoped_hit(before, units, approved, sources) == after
                hit_checks += 1
        assert demo.make_packet(query_map[old["query_id"]], new["files"][:5], sources) == packet
    with demo.DICTIONARY.open(encoding="utf-8-sig", newline="") as stream:
        labels = {row["risk_tag"] for row in csv.DictReader(stream)}
    assert len(labels) == 27
    checked = demo.validate_judgments(packets, judgments, labels)
    assert checked == demo.read_json(demo.OUT / "judgment_verification.json")
    initial = demo.rows(demo.OUT / "model_judgments_initial.jsonl")
    corrected = copy.deepcopy(initial)
    next(j for j in corrected if j["query_id"] == "D004")["evidence_assessments"][2]["quote"] = "给\n予保险合\n同约定以\n外利益"
    assert corrected == judgments
    audit = demo.rows(demo.OUT / "retrieval_results.jsonl.token_audit.jsonl")
    rerank_audit = [row for row in audit if row["stage"] == "rerank"]
    assert len(rerank_audit) == 1600
    for record in actual:
        expected = {row["unit_id"] for row in record["stages"]["rerank"]}
        observed = [row["unit_id"] for row in rerank_audit if row["query_id"] == record["query_id"]]
        assert len(observed) == 100 and set(observed) == expected
    truncations = sum(bool(row["truncated"]) for row in audit)
    counts = Counter(j["decision"] for j in judgments)
    by_query = {j["query_id"]: sum(a["helpful"] for a in j["evidence_assessments"]) for j in judgments}
    result = {"status": "passed", "source_documents": len(sources), "indexed_units": len(units),
        "inputs": 16, "retrieval_records": 16, "evidence_positions": 80, "model_hit_fields_checked": hit_checks,
        "weights": [1, 1], "scoped_top5_positions": sum(bool(h.get("display_only")) for p in packets for h in p["evidence"]),
        "frozen_dependencies_unchanged": len(frozen["files_sha256"]), "real_rerank_inputs": len(rerank_audit),
        "token_truncations": truncations, "run_elapsed_seconds": log["elapsed_seconds"],
        "document_cache_hits": [e["hit"] for e in log["models"]["cache_events"] if e["kind"] == "document"],
        "query_cache_hits": [e["hit"] for e in log["models"]["cache_events"] if e["kind"] == "query"],
        "model_decision_counts": dict(counts), "model_useful_positions": checked["model_useful_positions"],
        "model_useful_positions_by_query": by_query, "inputs_with_model_helpful_evidence": sum(n > 0 for n in by_query.values()),
        "source_and_packet_reconstruction": "passed", "judgment_quote_correction_only": "D004/F004280 literal line wrapping",
        "human_approved": False, "independent_quality_gold": False, "author_is_judge": True,
        "scope": "Stage/source/coverage mechanics and current-session evidence interpretation; not risk-label accuracy."}
    demo.write_new(demo.OUT / output_name, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
