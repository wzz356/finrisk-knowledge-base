"""Bind three explicitly read new positions and aggregate the event display control."""
from e07 import OUT, ROOT, demo

SPECS = {
 ("D014","F009272"): (False,"partial","","仅列演示课件和条款等证据名称，未显示收益数字或保证条件",[]),
 ("D016","F004266"): (False,"partial","","只有条款宣传引人误解案由，无满期金额及条件事实",["不同机构表行不能合并行为"]),
 ("D016","F001997"): (True,"partial","声称保险到期后会有16%的收益,与保险条款规定的“按保险费之和的108%给付满期保险金”的事实不符。",
   "明确到期利益宣传和条款金额不符，帮助核查领取条件/保证数字；输入产品未知不能直接套定性",["完整返回保留公司申辩及监管回应；不补成当前产品同案"])
}


def main():
    sources = demo.source_map()
    pending = demo.rows(OUT / "e06_pending_judgments.jsonl")
    reused = demo.rows(OUT / "e06_reused_judgments.jsonl")
    if {(r["query_id"], r["hit"]["file_id"]) for r in pending} != set(SPECS): raise ValueError("New reading population differs")
    new = []
    for record in pending:
        hit=record["hit"]; useful, relation, quote, reason, warnings=SPECS[(record["query_id"], hit["file_id"])]
        if quote and (quote not in hit["text"] or quote not in sources[hit["file_id"]]): raise ValueError("New quote is not actual source/display")
        if useful and not quote: raise ValueError("Useful position requires exact quote")
        new.append(dict(record,assessment={"file_id":hit["file_id"],"unit_id":hit["unit_id"],"rank":hit["rank"],
            "helpful":useful,"relation":relation,"quote":quote,"reason":reason,"warnings":warnings},
            origin="current_session_model",human_approved=False))
    all_rows=reused+new
    if len(all_rows)!=80 or len({(r["query_id"],r["hit"]["file_id"],r["hit"]["unit_id"]) for r in all_rows})!=80:raise ValueError("Incomplete/duplicate evidence control")
    parent = demo.rows(ROOT / "outputs/FinRisk_离线演示V3_20261013/model_judgments.jsonl")
    old_counts={r["query_id"]:sum(a["helpful"] for a in r["evidence_assessments"]) for r in parent}
    new_counts={qid:sum(r["assessment"]["helpful"] for r in all_rows if r["query_id"]==qid) for qid in old_counts}
    execution=demo.read_json(OUT / "e06_execution.json")
    demo.write_new(OUT / "e06_new_judgments.jsonl",new,True)
    demo.write_new(OUT / "e06_all_judgments.jsonl",all_rows,True)
    demo.write_new(OUT / "e06_metrics.json",dict(execution,status="complete_exploratory_control",pending_semantic_positions=0,
        useful_positions_before=sum(old_counts.values()),useful_positions_after=sum(new_counts.values()),
        covered_queries_before=sum(v>0 for v in old_counts.values()),covered_queries_after=sum(v>0 for v in new_counts.values()),
        per_query_before=old_counts,per_query_after=new_counts,
        conclusion="Local role/event annotations are useful candidate metadata; hard same-event postponement reduced known duplicate occupancy but also useful positions, so do not enable default diversity reranking.",
        independent_gold=False,human_approved=False))
    print(sum(old_counts.values()),sum(new_counts.values()))


if __name__ == "__main__": main()
