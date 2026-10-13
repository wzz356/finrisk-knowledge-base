"""Conservative local event display and diversification of the actual V3 Top20."""
import copy
import json
from collections import Counter
from e07 import OUT, ROOT, demo


def event_for_unit(unit, graph):
    found = []
    for event in graph["events"]:
        if event["status"] != "source_supported": continue
        for member in event["members"]:
            if member["file_id"] != unit["file_id"]: continue
            if member["source_sha256"] != unit["source_sha256"]:
                raise ValueError("Local graph stale source binding")
            spans = unit["source_spans"]
            if spans and all(any(bound["start"] <= span["start"] < span["end"] <= bound["end"]
                                 for bound in member["event_spans"]) for span in spans):
                found.append((event["event_id"], member["role"], member.get("actor_name")))
    if len(found) > 1:
        raise ValueError("Unit has multiple event memberships; cannot force a merge")
    return found[0] if found else None


def diversify(hits, units, graph):
    first, later, seen = [], [], set()
    for hit in hits:
        membership = event_for_unit(units[hit["unit_id"]], graph)
        key = membership[0] if membership else "unlinked_position:" + hit["unit_id"] + ":" + str(hit["rank"])
        row = copy.deepcopy(hit)
        row.update(original_rank=hit["rank"], original_score=hit["score"],
                   local_event_id=membership[0] if membership else None,
                   local_actor_role=membership[1] if membership else None,
                   local_actor_name=membership[2] if membership else None,
                   event_interpretation="local source-supported reviewed scope only; not global event completeness")
        (later if key in seen else first).append(row)
        seen.add(key)
    return [dict(row, display_rank=index) for index, row in enumerate(first + later, 1)]


def duplicates(hits):
    keys = [hit.get("local_event_id") or "unlinked_position:" + hit["unit_id"] + ":" + str(hit["rank"]) for hit in hits]
    return len(keys) - len(set(keys))


def main():
    sources = demo.source_map()
    graph = demo.read_json(OUT / "local_graph.json")
    for event in graph["events"]:
        for member in event["members"]:
            source = sources[member["file_id"]]
            if demo.sha_text(source) != member["source_sha256"]: raise ValueError("Graph source changed")
            for anchor in member["anchors"] + member.get("context_supports", []):
                span = anchor["span"]
                if source[span["start"]:span["end"]] != anchor["quote"]: raise ValueError("Graph anchor mismatch")
            span = member["role_span"]
            if source[span["start"]:span["end"]] != member["role_quote"]: raise ValueError("Graph role mismatch")
    units, _ = demo.load_scope(sources)
    actual = demo.rows(ROOT / "outputs/FinRisk_离线演示V3_20261013/display_results.jsonl")
    packets = {p["query_id"]: p for p in demo.rows(ROOT / "outputs/FinRisk_离线演示V3_20261013/evidence_packets.jsonl")}
    judgments = {j["query_id"]: j for j in demo.rows(ROOT / "outputs/FinRisk_离线演示V3_20261013/model_judgments.jsonl")}
    results, pending, evaluated = [], [], []
    before_duplicates = after_duplicates = changed = 0
    for parent in actual:
        all_new = diversify(parent["files"][:20], units, graph)
        baseline = []
        for hit in parent["files"][:5]:
            member = event_for_unit(units[hit["unit_id"]], graph)
            baseline.append(dict(hit, local_event_id=member[0] if member else None))
        before_duplicates += duplicates(baseline); after_duplicates += duplicates(all_new[:5])
        changed += [h["file_id"] for h in parent["files"][:5]] != [h["file_id"] for h in all_new[:5]]
        results.append({"query_id": parent["query_id"], "text": parent["text"], "source":"same_actual_V3_1_to_1_run",
                        "files": all_new, "original_top5": baseline, "new_model_calls": 0})
        original_hits = packets[parent["query_id"]]["evidence"]
        original_assessments = judgments[parent["query_id"]]["evidence_assessments"]
        for hit in all_new[:5]:
            binding = (hit["file_id"], hit["unit_id"], demo.sha_text(hit["text"]))
            match = next((a for old, a in zip(original_hits, original_assessments)
                          if (old["file_id"], old["unit_id"], demo.sha_text(old["text"])) == binding), None)
            record = {"query_id": parent["query_id"], "text": parent["text"], "hit": hit,
                      "displayed_text_sha256": binding[2], "source_sha256": demo.sha_text(sources[hit["file_id"]])}
            if match is None:
                pending.append(record)
            else:
                record.update(assessment=copy.deepcopy(match), reuse="exact_V3_query_file_unit_text_binding")
                evaluated.append(record)
    demo.write_new(OUT / "e06_results.jsonl", results, True)
    demo.write_new(OUT / "e06_reused_judgments.jsonl", evaluated, True)
    demo.write_new(OUT / "e06_pending_judgments.jsonl", pending, True)
    demo.write_new(OUT / "e06_execution.json", {"status":"controls_built_semantic_supplement_pending" if pending else "complete",
        "queries":len(results), "same_event_duplicates_before":before_duplicates, "same_event_duplicates_after":after_duplicates,
        "changed_top5_queries":changed, "reused_positions":len(evaluated), "new_positions_to_read":len(pending),
        "actual_new_model_calls":0, "graph_sha256":demo.sha_file(OUT / "local_graph.json"), "human_approved":False,
        "graph_scope":"local source-supported facts/roles; no community/full GraphRAG"})
    print(json.dumps({"queries":len(results),"changed":changed,"duplicates_before":before_duplicates,"duplicates_after":after_duplicates,
                      "new_positions":len(pending)},ensure_ascii=False))


if __name__ == "__main__": main()
