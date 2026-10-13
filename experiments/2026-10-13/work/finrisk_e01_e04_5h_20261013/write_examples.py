"""Render actual paired hits and existing judgments, without new grades."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def main():
    main_rows = rows(OUT / "evaluation/per_query_metrics.jsonl")
    display_rows = rows(OUT / "display_evaluation/per_query_metrics.jsonl")
    combo_rows = rows(OUT / "combo_evaluation/per_query_metrics.jsonl")
    by = {(r["query_id"], r["arm"]): r for r in main_rows + display_rows + combo_rows}
    sections = ["# 五个实验样例", "", "以下完整显示文本直接取实际返回记录；分数/理由为已有模型判断，不重新编写证据或给分。", ""]
    specs = [("C007", "B0", "D1", "F003464", "范围补齐：合同外利益不止是案由"),
             ("N014", "B0", "D1", "F001987", "争议增量：跨产品核查框架，非医疗险直接证据"),
             ("Q009", "B0", "W4", None, "检索权重：新增的是条件核查帮助"),
             ("N018", "B0", "W4", None, "保留退步：真实代理销售的边界"),
             ("C002", "B0", "C2", "F004490", "未修单元：跨表行主体仍可能错移用")]
    for index, (qid, left, right, fid, title) in enumerate(specs, 1):
        before, after = by[qid, left], by[qid, right]
        sections += [f"## {index}. {title}", "", "输入：" + before["query_text"], ""]
        bh = {h["file_id"]: h for h in before["top5"]}
        ah = {h["file_id"]: h for h in after["top5"]}
        if fid:
            old = bh.get(fid)
            new = ah.get(fid)
        else:
            old_ids, new_ids = set(bh), set(ah)
            if qid == "Q009":
                new = next((h for h in after["top5"] if h["context_help_grade"] >= 2 and h["file_id"] not in old_ids), after["top5"][0])
                old = before["top5"][-1]
            else:
                old = next((h for h in before["top5"] if h["context_help_grade"] >= 2 and h["file_id"] not in new_ids), before["top5"][0])
                new = next((h for h in after["top5"] if h["context_help_grade"] < 2 and h["file_id"] not in old_ids), after["top5"][-1])
        for label, hit in ((left, old), (right, new)):
            if hit is None:
                sections += [f"### {label}", "", "该文书未进入Top5。", ""]
                continue
            sections += [f"### {label}：{hit['file_id']}，第{hit['rank']}位", "",
                         f"片段{hit['context_help_grade']}分；模型误用警示：{'是' if hit['context_misleading_risk'] else '否'}。", "",
                         hit["context_reason"], "", "实际返回全文：", ""]
            sections += ["> " + line for line in hit["returned_hit"]["text"].splitlines()]
            sections += ["", "实际判读引用：" + (hit["evidence_quote"] or "低分未附正向支持引用"), ""]
        if qid == "N014":
            sections += ["此处2分依据是可核对话术与条款的间接框架。案例是贷款，不含医疗险免责/等待期直接证据；F001988为同事件另一主体文书，不能算两份独立证据。sensitivity.json单独排除这两处计算保守结果，原评分没改。", ""]
        if qid == "C002":
            sections += ["F004490没有属于本轮21已审核scope的获胜单元，因此仍是旧父上下文。该警示不能归为新前缀直接制造主体；它说明只修代表单元未覆盖所有同类片段。", ""]
    (OUT / "样例对比.md").write_text("\n".join(sections) + "\n", encoding="utf-8")
    print("saved 5 paired actual examples")


if __name__ == "__main__":
    main()
