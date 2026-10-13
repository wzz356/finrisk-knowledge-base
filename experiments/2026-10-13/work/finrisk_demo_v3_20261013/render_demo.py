"""Render the completed, validated session records for reading and presentation."""
import demo

STATUS = {"risk_detected": "存在风险表述", "no_obvious_risk": "本段未见明显风险", "insufficient_information": "信息不足，需补核"}
RELATION = {"direct": "机制直接对应", "partial": "部分相似", "boundary": "反向条件对照", "irrelevant": "无关"}


def write_md(name, lines):
    with (demo.OUT / name).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")


def detail(packet, judgment, full):
    lines = [f"## {packet['query_id']}：{STATUS[judgment['decision']]}", "", f"输入：{packet['input_text']}", "",
             "疑似标签：" + ("、".join(r["risk_tag"] + ("（可能）" if r["certainty"] == "possible" else "（较可能）") for r in judgment["risk_labels"]) or "无"), "",
             "判断：" + judgment["reason"], ""]
    for label in judgment["risk_labels"]:
        lines += [f"- **{label['risk_tag']}**：输入原话“{label['input_quote']}”；支持文件：" + ("、".join(label["evidence_file_ids"]) or "当前无有效案例支撑") + f"。限制：{label['limitations']}"]
    lines += ["", "待核信息：" + "；".join(judgment["missing_information"]), "", "条件/范围：" + "；".join(judgment["boundary_notes"]), ""]
    chosen = list(zip(packet["evidence"], judgment["evidence_assessments"]))
    if not full:
        chosen = next(([pair] for pair in chosen if pair[1]["helpful"]), [])
    for hit, assessment in chosen:
        lines += [f"### {hit['file_id']}，重排第{hit['rank']}：{RELATION[assessment['relation']]}", "",
                  f"是否帮助判断：{'是' if assessment['helpful'] else '否'}。{assessment['reason']}", "",
                  f"原文区间：{hit['source_spans']}；范围返回修正：{'已审核单元' if hit.get('display_only') else '原V2返回'}；状态：候选，未经人工批准。", ""]
        if assessment["warnings"]:
            lines += ["限制：" + "；".join(assessment["warnings"]), ""]
        lines += ["```text", hit["text"] if full else assessment["quote"], "```", ""]
    return lines


def main():
    packets = demo.rows(demo.OUT / "evidence_packets.jsonl")
    judgments = {j["query_id"]: j for j in demo.rows(demo.OUT / "model_judgments.jsonl")}
    check = demo.read_json(demo.OUT / "verification_final.json")
    summary = ["# FinRisk 1:1完整流程演示结果", "", "输入文字→双路召回→1:1 RRF→rerank→原文证据包→当前会话风险判别。",
        "", "当前采用用户指定的1:1；原2:1实验保留为后续依据。本轮全9639文书/65475单元参与检索，16条输入与旧42及3条演示无逐字重复。", "",
        f"真实后台检索记录耗时{check['run_elapsed_seconds']:.2f}秒（不含入口冻结核验、缓存复制和会话判断），实际1600个重排输入；文档向量经指纹命中，新查询真实编码，token截断0。", "",
        "|输入|会话判断|疑似官方标签|有用返回位置/5|", "|---|---|---|---:|"]
    for packet in packets:
        qid = packet["query_id"]; judgment = judgments[qid]
        summary += [f"|{qid}|{STATUS[judgment['decision']]}|" + ("、".join(r["risk_tag"] for r in judgment["risk_labels"]) or "无") + f"|{check['model_useful_positions_by_query'][qid]}|"]
    summary += ["", "会话判断6条风险表述、6条本段未见明显风险、4条信息不足；80个位置中53个被模型认为有核查帮助，14/16条至少一段有用。包含部分相似和反向条件对照，不等于53个直接违规证据或独立事件。", "",
        "这16条由同一会话构造并判读，设计角色不是金标；没有同输入原版/范围返回的完整判别对照，不能将53/80与旧实验分数相减声称改进，也不计算最终标签准确率。", "",
        "## 已接通的部分", "", "- 固定BM25/BGE各100、RRF1:1/k60、rerank100、文书Top5。", "- 已审核21单元可修返回，本轮实际曝光3处：D001/F004090、D005/F003497、D011/F002890。其余原样，不按文件批准所有单元。", "- 16条记录完整保存疑似27类标签、输入触发原话、五位置案例关系、连续原文引文、条件差异和缺失信息。", "- CLI支持新输入真实检索与证据包导出；判断仍由当前会话完成，未接自动判别API或应用接口。", "",
        "## 保留的不足", "", "- D002：输入主动说明重疾疾病定义、等待期及免责，但Top5主要是案由或合同外利益，无直接条件案例。判断可以读取输入，案例支撑仍不足。", "- D013：理赔便利/速度的承诺与实际服务差异仍未召回；录音证据清单或资料不规范不是该机制，保留销售误导/虚假宣传可能项，明确无有效案例支撑。", "- D015：仅1份提供实际代理与收款对象差异；其他多是证据目录，不能以手续费付个人直接定性。", "- 多文书同事件占位仍存在：D011宝应两份文件、D014同培训事件、D016两组同事件迹象等；本轮未以演示为由改排序。", "- 历史保证率、演示档位、资格证要求不直接当当前通用规则；输入主体与公司/责任人员层次分开。", "- F001319/F001320源文本有病句，展示原样，只引用完整可读事实，不自动修补资金机制。", "",
        "## 验证", "", "12项必要测试通过；重算16条RRF、重排候选及文书/案例聚合，检查640个命中字段；重建全部16包/80位置，逐字引用与官方27类通过。原执行67项依赖中66项保持原SHA；新入口补齐父结果SHA及完整参数校验，初始入口/冻结另存，修复后最终71项依赖核对通过。真实检索、证据包和语义判断未变，未重跑GPU。一次引用换行错误修正已保留初稿/记录，未改语义判断或源文。", "",
        "核验为结构、回源、排名与记录一致性，不替代独立人工语义验收。新采用方案与旧2:1历史报告分存。", "",
        "下一步可用[三个典型演示](三类典型展示.md)展示流程，再收集真实业务反馈，优先修D002/D013这类缺口。完整实际文字见[全部输入输出](全部输入输出.md)，复跑见[README](README.md)。"]
    write_md("演示报告.md", summary)
    all_lines = ["# 16条输入与实际Top5完整记录", "", "全部风险判断为当前会话模型意见，非人工金标。原文块按实际返回原样展示；机构/人员、跨产品和事件重复限制见每条说明。", ""]
    for packet in packets:
        all_lines += detail(packet, judgments[packet["query_id"]], True)
    write_md("全部输入输出.md", all_lines)
    sample = ["# 三类典型演示", "", "固定1:1双路融合＋rerank。每例给一段实际支持引文；完整Top5和未帮助材料见全部输入输出。", ""]
    for qid in ["D003", "D006", "D014"]:
        packet = next(p for p in packets if p["query_id"] == qid)
        sample += detail(packet, judgments[qid], False)
    sample += ["## 展示时说明", "", "风险候选、原文引用和待核条件分别展示。召回了违规案例，不等于输入必然违规；信息不足可给可能标签并列缺口。D002/D013目前无有效Top5支撑，不用成功样例掩盖。"]
    write_md("三类典型展示.md", sample)


if __name__ == "__main__":
    main()
