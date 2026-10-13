"""Source-only preparation and checks for the 24 E01/E02 representations.

This authoring helper reads only the frozen source work packages and their
source-quoted prefixes. It does not read queries, experiment results, or scores.
Offsets are Unicode character offsets in full_source_text, [start, end).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "outputs" / "FinRisk_E02小批量实验_20261013"
OUT = ROOT / "outputs" / "FinRisk_E01-E04五小时实验_20261013"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def occurrences(source: str, quote: str) -> list[dict[str, int]]:
    found = []
    start = 0
    while (start := source.find(quote, start)) >= 0:
        found.append({"start": start, "end": start + len(quote)})
        start += 1
    return found


# The intervals below were selected after actually reading every full source
# and original unit. They complete the existing unit's own action/paragraph;
# no selection is conditioned on a query or on retrieval performance.
SCOPES = {
    "F003464": {
        "segments": [(162, 258, "behavior_paragraph", "一号案由及其紧随的经查事实是同一完整行为段，补全原单元只有案由标题的问题。")],
        "reason": "保留一号合同外利益案由与营业一部书面承诺五年期分红险一年后给付本金的完整事实；不纳入二号银代误导或三号手续费案由。",
    },
    "F008940": {
        "segments": [(30, 40, "document_party", "个人文书身份；不表明该个人亲自实施销售宣传。"), (277, 417, "behavior_and_responsibility", "连续保留该中心销售人员的完整事实句和随后对副总经理管理责任的明确认定。")],
        "reason": "补全赠送礼品句尾，并保留紧接事实的直接负责管理人员认定。李荣是受处罚个人，销售发言主体仍为销售人员。",
    },
    "F008944": {
        "segments": [(30, 41, "document_party", "个人文书身份；不表明该个人亲自实施销售宣传。"), (277, 416, "behavior_and_responsibility", "连续保留该中心销售人员的完整事实句和随后对总经理管理责任的明确认定。")],
        "reason": "补全赠送礼品句尾，并保留紧接事实的直接负责管理人员认定。吕思挺是受处罚个人，销售发言主体仍为销售人员。",
    },
    "F009491": {
        "segments": [(75, 100, "party_role", "文书职务字段为事实段中的该公司提供正式机构身份。"), (347, 474, "behavior_and_responsibility", "二号案由的微信群方案及随后明确的焦勇直接领导责任连续保留。")],
        "reason": "范围限于二号合同外利益事实和焦勇对上述违规问题负直接领导责任的原话；不把负责人身份或领导责任改写为亲自发布微信群方案。",
    },
    "F009587": {
        "segments": [(43, 50, "document_party", "个人文书身份为当事人指代提供姓名。"), (239, 567, "behavior_and_responsibility", "保留引出以下机构行为的管理责任原话，以及一号案由三个产品各自对应的完整宣传事实和证明材料句。")],
        "reason": "原单元从料中截断且只保留最后一个产品尾部。现恢复一号案由完整段，并限定朱传营承担管理责任；排除二号虚构中介业务套费事实。",
    },
    "F004155": {
        "segments": [(174, 230, "independent_table_row", "原单元第一次匹配位于第2行，逐字保留该行序号、机构、行为、处罚。"), (435, 510, "independent_table_row", "原单元第二次匹配位于第7行，逐字保留该行序号、个人及时任职务、该行两个行为和处罚。")],
        "reason": "两个匹配位置各自的表内同行范围可以限定，故并列保留第2行和第7行；两段独立，不声称两主体同案、同一实施者或直接责任，不以其中一行主体概括整表。",
        "notes": ["原unit在[202,222)与[474,494)重复出现；两个原事件/角色候选关联仍未确认。", "第7行还含销售误导，仅作为该行原文独立保留，未据此把第2行机构附加销售误导行为。", "第2行未重复文号和机关；不把合并单元格或首行文号推定为每一行独立文号。", "两行均是对应匹配的局部返回范围，不展示整表其他五行，不合并两行主体。"],
        "prefix_scope": "文书身份摘录，非穷举。两个对应原文段落独立；前缀不构成统一片段主体，不确认原unit的事件/角色映射。",
    },
    "F001987": {
        "segments": [(131, 483, "behavior_and_evidence", "证据句中的以上行为由紧邻的完整经查段明确：销售人员的产品性质宣传和保单贷款宣传分别保留。"), (548, 594, "responsibility", "同一监管认定段明确刘峥的职务、管控缺失和直接主管责任。")],
        "reason": "原单元只有以上行为的证据句。现恢复其完整前置事实及直接主管责任原话；销售宣传与实际条款的比较完整保留，不将宣传内容当作合同真实约定。",
    },
    "F001345": {
        "segments": [(44, 72, "document_party", "正式机构名称和简称的源内定义。"), (583, 1103, "behavior_and_responsibility", "一号倒签单案由、完整原因与收入/准备金后果，以及三名直接责任人的局部认定连续保留。")],
        "reason": "原单元从确认起截断，只余未到期准备金结果。现限定到一号倒签单完整行为及其明确责任段；不纳入二号危险单位划分及李玲的责任。",
    },
    "F004090": {
        "segments": [(93, 178, "independent_table_row", "第1行完整包含序号、济南中心支公司、160号文号、委托医护人员销售健康险、处罚和机关。")],
        "reason": "原单元唯一出现于第1行，其机构与行为具有直接同行关系；返回仅限该行，不将济南主体扩展到滨州、济宁或其他个人的行为。",
        "notes": ["旧unit evidence_ambiguous=true是候选元数据状态；实际原文仅一个匹配位置[136,149)，在第1行。", "第6行未显示独立行为；未从其他行补造孙宁行为，也未纳入当前范围。", "保留[93,178)完整第1行，排除[178,636)其余五行及页尾。"],
    },
    "F001988": {
        "segments": [(66, 87, "document_party", "正式受处罚机构名称为经查段中的你公司提供身份。"), (132, 453, "behavior_and_evidence", "原单元证据句所支持的紧邻完整经查段，分别保留各保单宣传与真实条款的比较。")],
        "reason": "原单元只有以上行为的证据句。现恢复该机构两类不实宣传的完整经查段及证据句，不借用个人处罚文书的主管责任，也不把保单贷款宣传当作真实条款。",
    },
    "F000742": {
        "segments": [(769, 934, "behavior_and_responsibility", "完整二号案由包含电话销售产品范围原话、该计划所含万能型附加险及紧随的李朝晖直接责任认定。")],
        "reason": "补全原单元在计划名称处截断的二号事实，范围止于该项李朝晖责任句；不纳入一号电销欺骗、三号虚假承保录音，也不把高璐或彭惠英归为本项责任人。",
    },
    "F002958": {
        "segments": [(52, 60, "document_party", "受处罚个人身份，仅标示姓名。"), (94, 217, "responsibility_and_behavior", "连续保留任职副经理期间对以下公司行为负直接责任的限定及该次拒赔事实。")],
        "reason": "原单元的该公司指代由紧邻前句明确；同时保留周培红的直接责任角色，不断言她亲自实施未查勘或拒赔动作。",
    },
    "F003497": {
        "segments": [(56, 80, "document_party", "你公司的正式机构身份。"), (122, 277, "behavior_paragraph", "连续保留套费案由、非代理业务虚挂、手续费转账、代理公司扣费和返还转付完整动作链，止于句号。")],
        "reason": "原单元在以现金处截断。现补全该行为段，明确都邦支公司、纵横代理公司、业务员和其他代理人分别出现的动作；不将代理公司套取返还动作笼统归于受罚机构亲自实施。",
    },
    "F002890": {
        "segments": [(1646, 1936, "behavior_subsection", "完整第3项(2)限定为齐齐哈尔中支农业保险理赔资料：原单元此外的前文、4020万元用途说明和监管认定连续保留。")],
        "reason": "原单元在留作2009年预处截断。现恢复其完整所在(2)小节和虚增/截留赔款的局部认定；不纳入营运资金或虚假退还保费的其他小节，不把全部个人当事人认作同一实施者。",
    },
    "F003638": {
        "segments": [(55, 79, "document_party", "文书受处罚单位的正式身份，区别于具体实施的下属机构。"), (117, 306, "behavior_paragraph", "原单元从名下起截断；恢复完整2007年行为段，保留下属机构与鸿义代理公司的动作、非代理业务虚挂限定及手续费流向。")],
        "reason": "完整同一行为段明确分公司下属机构虚挂业务与代理公司扣费、现金/转账返还、业务员转付的动作链；文书受罚单位身份不等同各环节亲自实施主体。",
    },
}


SINGLES = {
    "F009488": "原单元已完整呈现二号合同外利益案由及微信群激励方案；单一机构文书的该公司指代可由源内当事人字段确认，保留原索引文本。",
    "F000699": "原单元已完整呈现安盛天平电话销售欺骗事实且直接写明公司销售人员；保留该案由原文本，不混入拒绝单独承保交强险行为。",
    "F001943": "原单元为完整一号个险销售误导条目，列出课件和代抄两项内容；文书机构明确，不扩成其他银保、团险或个人责任条目。",
    "F001978": "原单元为完整二号培训课件及三档利益演示条目，全文当事机构和该公司指代一致，保留原文本。",
    "F008852": "公开表仅列一名机构当事人，原单元为完整拒绝依法赔偿或给付的案由；没有具体拒赔情节可补，保留原文本。",
    "F001128": "原单元完整呈现第一项产品说明会课件及三档演示事实，句子虽有源换行但无截断；不扩至第二项展业册不同宣传内容。",
}


AMBIGUOUS = {
    "F006493": "公司与监事兼运营部负责人共同列于一份公开表，随后共用三项案由；源表未逐行为区分实施人或个人责任性质。保留原unit和全部匹配位置，不作排他性主体前缀。",
    "F006220": "公司与四名个人共同列于公开表，六项案由集中列示；不能把任一条案由逐项归给罗文仲、韦敏雄、谢中发或张国坚。原候选个人关联未确认，保留原unit，不补主体前缀。",
    "F000269": "源表列单位、主要负责人赵文和公司/赵文分别受罚，但共用三项案由，未逐项说明个人实施动作或责任性质。保留原unit和全部位置，不把单位身份作为排他性实施主体前缀。",
}


LINK_REASONS = {
    "F003464": ["单一机构文书的你公司指代与当前一号完整行为段一致。", "同一号案由紧随的完整经查事实，已包含在当前范围内；不借用其他案由。"],
    "F008940": ["当前范围的个人文书身份，不证明李荣亲自作出宣传。", "当前完整行为段后紧接的管理责任原话，限定该个人责任性质。", "同一句礼品承诺的连续原文已在当前事实段完整保留，主体仍为销售人员。"],
    "F008944": ["当前范围的个人文书身份，不证明吕思挺亲自作出宣传。", "当前完整行为段后紧接的管理责任原话，限定该个人责任性质。", "同一句礼品承诺的连续原文已在当前事实段完整保留，主体仍为销售人员。"],
    "F009488": ["单一机构文书身份与当前二号案由中的该公司指代一致。"],
    "F009491": ["个人文书身份；不据姓名证明其亲自发布微信群方案。", "职务行提供该公司正式身份，亦单独保留在scope中。", "紧接二号案由的领导责任原话，亦在scope中；不是亲自实施认定。"],
    "F009587": ["个人文书身份；不是机构提供材料行为的亲自实施认定。", "引出以下行为的管理责任原话与当前一号段对应，未借入二号事实。", "当前一号完整事实段的三个产品及各自宣传语连续保留，各产品关系不互换。"],
    "F000699": ["当前电话销售事实直接使用安盛天平及公司销售人员；正式机构名称由源内定义，不扩至其他案由。"],
    "F004155": ["摘录第2行文书机构身份，非穷举；对应第一个独立scope行，不据此概括另一行主体或整表。", "摘录第7行个人及时任职务身份，非穷举；对应第二个独立scope行，未确认具体实施方式、直接责任或与第2行同案。"],
    "F001987": ["完整经查段内给出机构及简称，当前范围恢复了证据句的这组前置事实。", "同一监管认定段原话概括当前范围中的两类宣传，未把宣传当实际合同约定。", "原话限定当前范围的主管责任，区分销售人员发言与刘峥的管控责任。"],
    "F001345": ["当前一号倒签单段直接出现该机构简称，源内定义与范围一致。", "当前范围限于该一号案由，没有引入危险单位划分行为。", "同一完整事实段的行为期间和抽取保单范围，后文收入与准备金后果均在当前scope内。"],
    "F004090": ["第1行机构与委托医护人员销售健康险同行，当前scope仅保留该完整行；不是整表主体。"],
    "F001943": ["机构字段与第一项个险条目所在的检查对象一致；不把负责人姓名当作实施人。"],
    "F001988": ["单一机构文书中的你公司与当前完整经查及证据句相连。", "紧接证据句的认定原话说明当前事实范围，两种不同保单宣传不合并成一次销售。"],
    "F000742": ["当前二号行为直接写明泰康人寿，源内正式名称和简称定义一致。", "当前二号scope已补全同一句计划和万能型附加险说明，不借用第一或第三项。"],
    "F001978": ["机构字段、检查对象、违法引导句均对应当前第二项行为。", "行为期间的引导句统领当前第二项；不当作检查或处罚决定日期。"],
    "F002958": ["当前scope中受处罚个人姓名；具体责任由连续任职责任句限定。", "紧邻当前公司拒赔事实的任职与直接责任原话；不证明个人亲自实施拒赔。"],
    "F008852": ["公开表唯一机构当事人与紧接的该拒赔案由对应；源文未给具体拒赔情节。"],
    "F003497": ["当前段中的你公司为都邦东莞中支，纵横代理公司独立参与扣费及返还。", "当前scope已完整保留同一句现金/转账套取、返还及转支付流向，保持代理公司动作。"],
    "F002890": ["完整第3项(2)直接指名该中支，当前scope中的此外沿用该局部主体，不扩至所有个人。", "当前完整小节已保留该笔款项完整用途及除了实际支付农险赔款外的限定，不移用其他小节事实。"],
    "F003638": ["仅标注文书受罚机构身份，当前事实中的具体参与者仍为其下属机构。", "当前scope已恢复同一完整行为段，主体、年份、非代理业务虚挂与流向均有原文依据。"],
    "F001128": ["名称字段与检查对象及当前第一项产品说明会课件行为对应，不扩到第二项展业册事实。"],
}


def main() -> None:
    inputs = []
    for name in ("prefix_inputs_p1.jsonl", "prefix_inputs_p2.jsonl"):
        inputs += [json.loads(line) for line in (OLD / name).read_text(encoding="utf-8").splitlines()]
    old_prefix = {}
    for line in (OLD / "prefixes.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        # Only identity and source-quoted claims are used; old review, scores,
        # outcomes and approval-like fields are neither read nor inherited.
        old_prefix[row["file_id"]] = deepcopy(row["claims"])
    assert len(inputs) == 24
    assert len({row["unit"]["unit_id"] for row in inputs}) == 24
    assert set(SCOPES) | set(SINGLES) | set(AMBIGUOUS) == {row["file_id"] for row in inputs}

    outputs = []
    for row in inputs:
        fid, source, unit = row["file_id"], row["full_source_text"], row["unit"]
        base = unit["text"]
        assert sha(source) == row["source_sha256"] == unit["source_sha256"], fid
        assert sha(base) == unit["unit_id"].rsplit(":", 1)[-1], fid
        matches = occurrences(source, base)
        assert matches == unit["source_spans"], fid
        spec = SCOPES.get(fid)
        if spec:
            status, reason = "scoped", spec["reason"]
            specs = spec["segments"]
        else:
            status = "single_subject" if fid in SINGLES else "ambiguous_unchanged"
            reason = SINGLES.get(fid, AMBIGUOUS.get(fid))
            assert len(matches) == 1, fid
            specs = [(matches[0]["start"], matches[0]["end"], "original_unit", "保留原索引文本逐字区间，所有匹配位置另存matched_occurrences。")]
        segments = [{"text": source[a:b], "span": {"start": a, "end": b}, "role": role, "reason": why} for a, b, role, why in specs]
        indexed = "\n".join(seg["text"] for seg in segments)
        claims = [] if status == "ambiguous_unchanged" else old_prefix[fid]
        if claims:
            reasons = LINK_REASONS[fid]
            assert len(claims) == len(reasons), fid
            for claim, why in zip(claims, reasons):
                claim["link_reason"] = why
        prefix = "\n".join(f"{claim['label']}：{claim['quote']}" for claim in claims)
        assert len(prefix) <= 180, (fid, len(prefix))
        for claim in claims:
            span = claim["span"]
            assert source[span["start"]:span["end"]] == claim["quote"], fid
        notes = list(spec.get("notes", [])) if spec else []
        if status == "ambiguous_unchanged":
            assert indexed == base, fid
            notes += ["共同案由中的个人实施/责任关系未解决；新显示范围和前缀未获批准。", "按root约定，本项不改变索引/返回，也不补背景；原候选case/behavior映射仅保留待核。"]
        notes.append("作者仅见来源工作包和源引文前缀；未读取查询、结果或评分。当前模型作者候选，等待root复核，非真人批准。")
        result = {
            "unit_id": unit["unit_id"],
            "parent_unit_id": unit["unit_id"],
            "file_id": fid,
            "source_sha256": sha(source),
            "base_unit_text_sha256": sha(base),
            "segments": segments,
            "indexed_text": indexed,
            "scope_status": status,
            "scope_reason": reason,
            "prefix_claims": claims,
            "prefix_text": prefix,
            "prefix_scope": (spec or {}).get("prefix_scope", "仅限当前范围的源内身份或背景；文书身份不自动等于亲自实施或排他性主体。") if claims else "前缀为空；主体/责任歧义未解决，原表示保持不变。",
            "notes": notes,
            "occurrence_ambiguity": len(matches) > 1,
            "matched_occurrences": matches,
            "attribution_ambiguity": status == "ambiguous_unchanged" or fid == "F004155",
            "base_evidence_ambiguous": unit["evidence_ambiguous"],
            "base_context_ambiguous": unit["context_ambiguous"],
            "original_case_ids": deepcopy(unit["original_case_ids"]),
            "original_behavior_ids": deepcopy(unit["original_behavior_ids"]),
            "base_case_ids": deepcopy(unit["case_ids"]),
            "base_behavior_ids": deepcopy(unit["behavior_ids"]),
            "base_associations": deepcopy(unit["associations"]),
            "association_review_status": "original_candidate_mappings_not_confirmed_by_scope_selection",
            "author_type": "current_session_model",
            "human_approved": False,
            "review_status": "pending_root_review",
            "source_read_chars": len(source),
            "base_unit_read_chars": len(base),
            "base_unit_chars": len(base),
            "indexed_chars": len(indexed),
            "prefix_chars": len(prefix),
            "text_changed": indexed != base,
        }
        validate(result, source, base)
        outputs.append(result)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "scope_units.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in outputs), encoding="utf-8")
    write_notes(outputs)
    summary = {"rows": len(outputs), "statuses": dict(Counter(r["scope_status"] for r in outputs)), "changed": sum(r["text_changed"] for r in outputs), "source_read_chars": sum(r["source_read_chars"] for r in outputs), "base_unit_read_chars": sum(r["base_unit_read_chars"] for r in outputs), "indexed_chars": sum(r["indexed_chars"] for r in outputs), "prefix_chars": sum(r["prefix_chars"] for r in outputs), "verification": "all_source_base_sha_spans_quotes_and_joins_passed", "human_approved": False}
    print(json.dumps(summary, ensure_ascii=False))


def validate(row: dict, source: str, base: str) -> None:
    assert 1 <= len(row["segments"]) <= 4
    assert row["indexed_text"] == "\n".join(s["text"] for s in row["segments"])
    assert row["matched_occurrences"] == occurrences(source, base)
    assert row["human_approved"] is False
    assert row["source_sha256"] == sha(source)
    assert row["base_unit_text_sha256"] == sha(base)
    for seg in row["segments"]:
        span = seg["span"]
        assert 0 <= span["start"] < span["end"] <= len(source)
        assert seg["text"] == source[span["start"]:span["end"]]
    for match in row["matched_occurrences"]:
        assert any(seg["span"]["start"] <= match["start"] < match["end"] <= seg["span"]["end"] for seg in row["segments"])
    if row["scope_status"] == "ambiguous_unchanged":
        assert row["indexed_text"] == base
        assert not row["prefix_claims"] and not row["prefix_text"]
    else:
        assert 1 <= len(row["prefix_claims"]) <= 3
    assert len(row["prefix_text"]) <= 180


def write_notes(rows: list[dict]) -> None:
    lines = [
        "# E01/E02源范围作者记录",
        "",
        "作者：当前会话模型；全部 `human_approved=false`，`review_status=pending_root_review`。仅生成候选范围与源引文背景，root仍需独立审核新实际显示范围。未继承旧prefix批准状态。",
        "",
        "输入只读：旧E02 `prefix_inputs_p1.jsonl`、`prefix_inputs_p2.jsonl` 的24份完整来源及原单元，以及 `prefixes.jsonl` 的原文引文。未读查询、结果、评分、360预留正文、教材PDF、.env；未调用付费API或GitHub。旧文件及源代码未修改。",
        "",
        "实际逐份阅读全文及原unit：24份全文共25,497个Unicode字符，24份原unit共1,698字符（正文换行计入）。所有source SHA与工作包声明一致；所有原unit SHA与unit_id的末尾SHA一致；全部匹配位置与旧source_spans一致。",
        "",
        "分型：15 scoped（范围改变），6 single_subject（完整原unit保留），3 ambiguous_unchanged（原unit保留，前缀为空）。共15/24改变索引范围；按源内行为段补齐截断、指代及明确责任，未按查询选片。单元沿用旧unit_id作为父引用；本文件不生成新的永久ID或representation_id。",
        "",
        "indexed_text严格为1–4个连续、逐字源segments以单个换行连接；span均为full_source_text的Unicode `[start,end)`，不计入跨段连接符。每段含role与选择理由；连接不构成同一主体关系声明。prefix_text仅为原E02允许标签及源quote，1–3条且不超过180字符；派生scope_reason、notes、prefix_scope不得作为监管引文。",
        "",
        "## 两张多主体表格",
        "",
        "F004090：保留第1行 `[93,178)`，其中原unit唯一匹配为 `[136,149)`。完整行包含济南中心支公司、160号文号、委托医护人员销售健康险、处罚及机关；排除其余五行。原候选 evidence_ambiguous 标志保存在base字段；局部同行关联有原文依据，新的范围仍待root审核。第6行没有独立案由，不从其他行补造其事实。",
        "",
        "F004155：原unit两处匹配 `[202,222)`、`[474,494)`全部保留，分别对应第2行 `[174,230)` 与第7行 `[435,510)`。`occurrence_ambiguity=true`；两个完整表行独立呈现。第2行是民生人寿延安中支，第7行是曹爱斌及时任职务且另含销售误导。仅限定每一行自身范围；不证明两主体同案、同一实施者或直接责任，不用一行主体概括整表。原事件/角色候选映射仍未确认，保留待核。前缀仅文书身份、非穷举，不能组成统一片段主体。",
        "",
        "## 保留歧义的后置项",
        "",
        "F006493：公司与个人共用三个案由，没有逐项实施或责任区分。F006220：机构与四人共用六项案由，个人行为映射未明确。F000269：单位与负责人赵文分别受罚但共同案由缺少个人实施/责任说明。这三份原索引文本、全部匹配位置保持不变，prefix_claims=[]、prefix_text为空；runner不改变索引/返回，不补背景。",
        "",
        "## 逐份阅读与改动剂量",
        "",
        "|文件|全文实际阅读字符|原unit字符|新indexed字符|prefix字符|分型|区间|",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        spans = "；".join(f"[{s['span']['start']},{s['span']['end']})" for s in row["segments"])
        lines.append(f"|{row['file_id']}|{row['source_read_chars']}|{row['base_unit_chars']}|{row['indexed_chars']}|{row['prefix_chars']}|{row['scope_status']}|{spans}|")
    lines += [
        "",
        f"合计新indexed {sum(r['indexed_chars'] for r in rows):,}字符；相较原unit增加{sum(r['indexed_chars']-r['base_unit_chars'] for r in rows):,}字符。候选prefix共{sum(r['prefix_chars'] for r in rows):,}字符；3项歧义不补prefix。",
        "",
        "## 验证和残余限制",
        "",
        "作者验证：24/24源SHA、24/24 base SHA、原unit全部位置、每个segment逐字区间、每条prefix quote区间、每段1–4限制、prefix 1–3及180字符上限、indexed严格换行连接、human_approved=false全部通过。所有原unit匹配位置均被实际scope段完整包含，不遗漏F004155第二处匹配。",
        "",
        "残余：三项多主体责任归属未解决；F004155的双位置原事件/角色关系未确认。选中同一段或同一表行只确认实际展示范围，不批准旧结构化case/behavior语义映射。短公开表缺少具体实施情节的记录未补造事实。全部为当前模型作者候选，root独立审核未完成，无真人批准。",
        "",
    ]
    (OUT / "scope_notes.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
