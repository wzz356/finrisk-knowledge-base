# FinRisk V2 检索投影

## 接口与范围

`project_document(file_id, full_text, draft, candidate_sha256, chunk_chars=300, overlap_chars=40) -> (units, audit)`，纯 Python 标准库，不含机器绝对路径，不写原稿、不修改候选标签或审核状态、不调用模型或付费 API。

结构化与原文兜底是两个独立 corpus；各 corpus 内按 `(file_id, source_text)` 去重，同一正文只保留一条模型输入。结构化引文与兜底正文恰好相同时也合并。主体、行为、角色和引文来源保存在 `case_ids`、`behavior_ids`、`associations`；单值 `case_id/behavior_id` 仅为 V1 兼容代表，不能作为共享证据的唯一归属。纯原文兜底使用 `file_id:SOURCE`，plural ID 为空，不伪造案件。

## 原文与上下文

- `text == source_text`，`prefix` 为空；模型输入不含主体补写、行为背景、角色标签、摘要或候选标签值，字符上限为 `chunk_chars`。
- `source_spans` 保留每个完全相同正文的全部精确位置，包括重叠出现。每个 span 的原文切片均等于 `source_text`。
- `context_spans` 指向完整连续父段；申辩的明确续句和机关回应的明确续句保留，紧邻明确监管回应标识时扩展回应，不凭关键词推断机关认定。空行、句末、明确章节标题划分父段；软断行和制表符/管道表格连续行保守保留；表格内带序号的行不会被外部章节规则切断，表外明确章节仍结束表块。
- `context_source_text` 等于所有 context span 的原文切片直接串接；`context_segments` 为每块 `{text, span}`，逐块可核验。单块的 `context_text` 等于 `context_source_text`；多块展示文本加入 `[原文间隔，分段摘录]`，避免把不连续原文伪装成连续事实。
- 长父段完整留在 context，字符裁切只发生在模型输入。`context_long` 按实际 `context_text` 总长判断，包含多块展示标识；`input_hard_split`、`context_ambiguous` 和 `ambiguity_reason` 明确提示句内边界、重复位置、多个候选主体或不连续段落。
- `associations` 保留候选角色（含 `unknown`）、引文种类、原引文的所有精确位置和主体引文位置，`attribution_status` 固定为 `candidate_association_not_verified`。`quote_position_ambiguous`、`party_position_ambiguous`、`qualifier_position_ambiguous` 单独说明位置歧义，任何一种多位置均纳入整体歧义。重复正文或同父段包含多个案件均不证明各主体直接实施了行为。
- 同一候选行为已经绑定的 `conditions/negations/exceptions` 精确引文及其完整父段回填到该行为证据的返回 context。`qualifier_source_links` 保留对应 case/behavior、字段、原引文、所有位置和 `candidate_behavior_link_not_verified`；`qualifier_quotes` 保存实际匹配引文，不使用标签值或补写条件。共享 finding 合并各关联行为自己的限定，并保留归属；不同 finding 的其他行为不会被串入。
- 旧稿的引文集合、条目 `quotes`、`coverage` 或 `behavior_keys` 显式 null 只在收集引文时作为无可遍历引文处理；原稿仍保持 null。`legacy_null_metadata_fields`、`metadata_unknown`、`metadata_unknown_reason` 保留未知意义，audit 记录字段与 `value: null`；明确不能解释为没有不确定性或没有限定条件。未知 coverage 成员列表不会生成行为关联。非数组、非 null 的引文集合拒绝处理，避免把字符串或其他类型猜作引文集合。

## 实际验证

- 首轮 12 项回归对未修改 V1 运行：11 项断言失败，1 项已有参数/引用校验通过。失败记录见 `projection_baseline_tests.log`。
- 表格句号父段修复和不连续上下文显示修复均先记录失败测试，分别见 `projection_table_red.log`、`projection_segments_red.log`。
- 独立规格审查发现 4 类缺口，并补查出独立父段限定未回填的问题。新增 7 项失败测试分别见 `projection_review_red.log` 与 `projection_shared_qualifier_red.log`，修复后按父段、歧义、限定三组逐项验证。
- 9639 文件范围运行发现旧稿 F005270 的两个行为 `uncertainties=null`，另加 4 项 nullable 失败回归后修复，red 记录见 `projection_nullable_red.log`。
- 最终 25 项测试通过，见 `projection_v2_tests.log`。覆盖错误背景前缀、25 行为共享正文、多主体及重复引文全部位置、原稿不变、unknown 角色、条件/否定/例外回填、长父段及多段总长、表格枚举边界、申辩和监管完整句续行、主体位置歧义、逐字回源、不连续上下文显示、无匹配引文审计及旧 null 元数据未知。复审结论由独立规格审查给出；本说明不代替复审。
- 真实回归仅通过公开仓库 `data/file_index.jsonl` 定位读取明确获准的 F002401、F001369、F005270 source/candidate 分片。F002401 的展业证正文不会带费用开拓背景；F001369 的计量困难/已整改申辩上下文保留可靠计量、现场检查后纠正、不予采纳的监管复核；F005270 的 null 不再导致遍历错误，两个受影响行为的未知标记及原稿 null 均保留。

## 限制

父段恢复和相邻回应识别是保守规则，不能保证所有 PDF 断行、无标识回应或复杂表格的语义边界。没有猜测性回应扩展；未精确匹配的引文写入 audit 并保留 raw 兜底。字符上限不是 token 上限，实际 embedding/rerank token 截断仍须由 runner 审计。上下文可比模型输入长，不能把短输入的排序分数当作对完整上下文的认定。

只合并同文件内完全相同正文，保留所有原文位置；不做跨文件事件合并，也不据此改变案件主体、责任层次或标签。V2 同时改变去重、前缀、分段和返回上下文，后续检索收益应作为组合投影改进报告，不能单独归因于去重。
