# FinRisk V2 投影规格独立复审

最新追加：合法旧 `null` 元数据兼容 **spec PASS**，审查 SHA256 `7f8805bdfa99f9a1f07e7d92415f85b86eee534b5d76b032258cb123f1a315ca`。已先完成本项独立规格复验，再交代码质量结论；下文保留前轮规格证据。

复审日期：2026-10-12。结论：**spec PASS（规格通过）**。

首轮审查的 5 类阻断问题已修复。本轮独立重跑现有 21 项测试、原始最小反例及额外归属／限定组合样例，全部通过。仅更新本报告；未修改实现或现有测试，未读取 360 盲验，未调用 API，未开展代码质量审查。

## 实际验证

执行：`python -m unittest discover -s 'work/finrisk_v2_20261012' -p 'test_projection_v2.py' -v`。

实际结果：`Ran 21 tests in 0.065s`、`OK`、退出码 0，含真实 F002401、F001369 公开回归。F002401 展业证处罚短正文不带渠道费用背景前缀；F001369 保留可靠计量、现场检查后纠正、不予采纳的监管复核。

独立重跑首轮报告原始样例，结果：

```text
PASS response_plain_continuation
PASS wrapped_complete_paragraph
PASS enumerated_table
PASS party_position_ambiguity
PASS combined_long_context
PASS all_attributions_and_quote_kinds
PASS noncontiguous_segments_roundtrip
PASS finding_linked_qualifiers
```

另构造一组独立组合样例：同一行为的条件在两处出现、否定／例外处于独立父段、一条条件不精确匹配、另一行为具有单独限定。实际确认：本行为的全部精确限定及父段随 finding 返回；保留 case/behavior/字段与每处 span；重复限定歧义显式标记；不精确引文进入 audit；另一行为限定和标签值未串入；draft 未变；所有单元短正文上限、精确回源与 candidate/pending 状态均保持。

## 首轮缺口复审结果

| 首轮问题 | 当前独立验证 | 修复证据 |
| --- | --- | --- |
| P1 完整申辩及监管回应续段遗漏 | 原始两种软换行样例均返回完整相关申辩／回应；现有回归同时确认不吞入后续处罚 | projection_v2.py 的 parent_spans 明确续句处理和 _context_spans 相邻回应扩展 |
| P2 枚举表格拆段漏限制 | 原始带制表符、中文序号样例保留表头及“资料缺失／不得办理”；现有回归确认表外章节结束表块 | parent_spans 的 section_start 对表内 row 排除 |
| P2 多个短块合计超长漏标记 | 原始 50 块样例 source context 350 字符、展示 1085 字符，context_long=true；实际总长提示存在 | projection_v2.py:331、341-342 |
| P2 主体多位置歧义漏标记 | 原始两处主体位置样例的 party_position_ambiguous、source_position_ambiguous、evidence_ambiguous 均为 true | projection_v2.py:301-305、337-338 |
| P1 同行为独立限定未随 finding 返回 | 原始 conditions/negations/exceptions 三段均随 finding 返回，完整父段及精确链接保留；另核查排除另一行为限定 | projection_v2.py 的 add 限定上下文回填及 :279-281 候选链接 |

## 其他批准规格

- structured/raw 为独立 corpus，各自按同文件相同正文去重；额外 3 主体、3 行为共享正文样例保留全部 IDs、associations、finding/support/condition 三种引文种类及两处精确正文位置。
- text 等于短 source_text，prefix 为空；不输出标签值、推测正文或主体补写；所有 unit 的 source_spans 逐个精确回源。
- 非连续上下文显示明确分段；context_segments 与 context_spans 一一对应并逐块回源。context_source_text 的无分隔拼接仅作为已声明协议字段，不作为连续叙述展示。
- qualifier_source_links 保留 case/behavior、限定字段、逐字引文、全部精确位置及 candidate_behavior_link_not_verified；attribution_status 保持 candidate_association_not_verified，不据候选绑定核定事实。
- unknown 角色不推定直接实施；纯 source 兜底不造案件；候选内容不变，candidate/pending 状态保留。
- 位置歧义、长上下文、句内边界和多个不连续块提示保留。

规格通过限于批准的投影协议和本轮实际验证。结构恢复仍采用明确标识规则，说明中已保留复杂 PDF／表格边界的限制；本报告不提供盲验、检索收益或代码质量结论。

## 可执行原始反例复审

在仓库根目录用标准 Python 运行以下完整代码。仅原样构造首轮输入，验收断言改为修复后批准预期；不读数据分片、不调用 API、不修改文件。该代码已从本报告提取并实际执行，全部 PASS。


```python
import importlib.util
from pathlib import Path

path = Path("work/finrisk_v2_20261012/projection_v2.py")
spec = importlib.util.spec_from_file_location("review_projection", path)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

def draft(quote):
    return {
        "file_id": "F000001", "semantic_status": "candidate",
        "human_review_status": "pending",
        "cases": [{"local_key": "c0", "party_quote": "甲机构"}],
        "behaviors": [{"local_key": "b0", "case_key": "c0",
                       "actor_role": "unknown", "finding_quote": quote}],
        "coverage": [],
    }

def row(source, quote, candidate=None):
    units, _ = p.project_document(
        "F000001", source, candidate or draft(quote), "review-sha", 300, 40
    )
    return next(u for u in units if u["corpus"] == "structured"
                and u["source_text"] == quote)

def check(name, satisfied):
    assert satisfied, name
    print("PASS " + name)

s = ("甲机构。\n甲机构申辩：已经整改。\n"
     "对上述申辩意见，本局认为仍构成违法。\n本局不予采纳其减免请求。")
u = row(s, "已经整改")
check("response_plain_continuation", "不予采纳" in u["context_text"])

s = ("甲机构。\n甲机构申辩：已经整改。\n其请求减免处罚。\n"
     "对上述申辩意见，本局不予采纳。")
u = row(s, "已经整改")
check("wrapped_complete_paragraph", "其请求减免处罚" in u["context_text"]
      and "不予采纳" in u["context_text"])

s = ("甲机构。\n\n条件\t办理限制。\n一、客户同意\t才可办理。\n"
     "二、资料缺失\t不得办理。")
u = row(s, "才可办理")
check("enumerated_table", "办理限制" in u["context_text"]
      and "不得办理" in u["context_text"])

s = "甲机构。\n未按规定回访。\n乙机构与甲机构另有合作。"
u = row(s, "未按规定回访。")
assert len(u["associations"][0]["party_source_spans"]) == 2
check("party_position_ambiguity", u["evidence_ambiguous"]
      or u["associations"][0]["source_position_ambiguous"])

s = "甲机构。\n" + "\n无关段落。\n".join(["不得隐瞒风险。"] * 50)
u = row(s, "不得隐瞒风险。")
assert len(u["context_source_text"]) == 350
assert len(u["context_text"]) == 1085
check("combined_long_context", u["context_long"])

q = "不得隐瞒风险。"
s = "甲机构。\n" + q + "\n无关段落。\n乙机构。\n" + q + "\n无关段落。\n丙机构。"
d = draft(q)
d["cases"] = [{"local_key": f"c{i}", "party_quote": party}
              for i, party in enumerate(["甲机构", "乙机构", "丙机构"])]
d["behaviors"] = [
    {"local_key": f"b{i}", "case_key": f"c{i}", "actor_role": "unknown",
     "finding_quote": q, "risk_mechanism_quotes": [q], "conditions": [{"quote": q}]}
    for i in range(3)
]
u = row(s, q, d)
check("all_attributions_and_quote_kinds",
      len(u["case_ids"]) == len(u["behavior_ids"]) == len(u["associations"]) == 3
      and all(a["evidence_kinds"] == ["finding", "support", "condition"]
              and a["actor_role"] == "unknown" for a in u["associations"]))
check("noncontiguous_segments_roundtrip",
      len(u["source_spans"]) == len(u["context_segments"]) == 2
      and "[原文间隔，分段摘录]" in u["context_text"]
      and all(segment["text"] == s[segment["span"]["start"]:segment["span"]["end"]]
              for segment in u["context_segments"]))

finding = "机构提供了办理服务。"
qualifiers = ["仅在客户资料齐全时可办理。", "资料缺失时不得办理。",
              "紧急情况下可先核验身份后补充资料。"]
s = "甲机构。\n\n" + "\n\n".join([qualifiers[0], finding, *qualifiers[1:]])
d = draft(finding)
for key, quote in zip(("conditions", "negations", "exceptions"), qualifiers):
    d["behaviors"][0][key] = [{"quote": quote}]
u = row(s, finding, d)
check("finding_linked_qualifiers", all(q in u["context_text"] for q in qualifiers))
assert all(q in u["context_text"] for q in qualifiers)
assert all(u["qualifier_quotes"].values())
```

## 合法旧 null 兼容追加独立规格复审

结论：**spec PASS**。本轮指定标准 Python 实际重跑 `test_projection_v2.py`：**25 tests，0.139 秒，OK，退出码 0**（前21项及新增3个 null fixture、真实 F005270 回归）。

本审查另独立经公开 `file_index.jsonl` 定位，仅读取 F005270 的对应单条 source／candidate。源正文 SHA 与 source.text_sha256 一致；19 units、2条 null audit 中，`she_responsibility`、`yang_responsibility` 的 `uncertainties:null` 均在 association 与相应 unit 保留 `legacy_null_metadata_fields`、`metadata_unknown=true`、未知解释；audit 保存实际字段及 `value:null`。全部 source_spans／context_segments 原文切片逐字相等，短正文上限与空 prefix 保持，原 draft 深比较不变。

为检验正文不变，另在独立比较副本将两个 uncertainties 从 null 替换为 []，只比较 source 投影：unit_id、text、source_spans、context_segments、每个 association 的 case／behavior／原 quote／quote spans 全部相同。该比较副本仅作为检验工具，不写回原稿，不把 null 的实际语义改为空列表。

另构造 conditions 的 null 成员及 `quotes:null`、support quotes 的 null 成员、coverage 的 null 成员及 `behavior_keys:null` 组合；5个精确字段路径在 unit／association／audit 中保留，audit value 均为 null。已存在的条件 quote 与完整上下文仍回填，未知 coverage membership 的引文不生成行为关联，原稿未变。

本项通过仅指兼容和精确来源协议；不推定“没有条件／没有不确定性”，不修改历史审批状态，不代表全9639已重建或GPU收益已验收。
