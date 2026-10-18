# 分析适配器独立窄范围审核

2026-10-18。**结论：当前实现通过，无开放阻断项。** 审核最初识别的条件列表标准化与 bootstrap 有效性口径分叉，已由实现方作最小修复，本审核已独立复验。没有修改实现、冻结文件或参数。

仅读取 `analysis_adapter.py`、`analyze_results.py`、`tests/test_analysis_adapter.py`、已审核的 `scoring.py/scoring_notes.md`、`protocol.py/effect_common.py`。没有读取真实 reference/expected、模型结果、运行账本或冻结清单，没有联网、调用 API 或运行分析入口 `main()`。

| 检查 | 结论 |
|---|---|
| 评分对齐与终止门槛 | 静态通过。`analyze_results.py:9–29` 在读取参考前检查两个 split 阶段 terminal/all_tasks_attempted、作业与 accepted 哈希及请求 body 绑定，再核对输入文字、audit 和参考文字哈希。该审核未验证真实清单或结果的哈希值。 |
| 固定 72 槽位与失败 | 通过。`30–35` 从 audit 逐槽标准化，显式要求 72 条且 query×arm 唯一；scorer 再按固定 mapping 分母评分。36×2 玩具输入含两条无 accepted 的槽位，两臂各 36 题分母不变，失败 2 条。适配器会为无 accepted 生成显式 invalid 记录，因此它们进入 scorer 的 invalid 数，而非 missing 记录数；覆盖率和失败率保留代价。 |
| 合法列表→字典及有效性一致 | 已修复通过。协议 `validate_result` 在深拷贝中将 `[status, quote]` 标准化；分析入口当前第 21 行采用返回副本。`analysis_adapter.py:14–15` 复用冻结评分器 `_valid_prediction`，comparisons/bootstrap 的 valid 标志与 scorer 一致。合法列表先经协议返回值标准化可正确得分；未标准化列表、畸形机制字段及无 accepted 均失败，不能在 bootstrap 白得正确分。 |
| 引用展示来源 | 通过。query_id/arm 由调用层赋值；current_text、displayed_case_ids、displayed_article_ids 来自 job.data，模型同名字段不能覆盖。协议要求返回 ID 来自展示列表，scorer 仅作字面与成员关系机械检查；没有引入语义充分性指标。 |
| 组 bootstrap | 通过。每格单独按 group_id 有放回抽同样数量的组，整组保留所有题、使用每题 new_correct-old_correct，抽样后按题加权；固定 seed。玩具异组大小验证 point_delta=1/3、区间[-1,1]；同一组内 +1/-1 的两题始终共同抽样，区间[0,0]。空集合端点 null。解释明确为小组数描述性百分位区间。 |
| 费用汇总 | 在账本字段契约下通过。`54–62` 汇总全部尝试与任务数、状态、返回模型、已记录 usage 和 settle.booked_usd；未知 usage 次数单列、actual_invoice_verified=false；未结算和大于 2 美元分别报错。3 个人工账本场景验证正常汇总、未结算拒绝、超帽拒绝。未核验真实价格、账单、账本来源或每条 booked_usd 的形成过程。reserve/settle 集合校验只证明 ID 覆盖，唯一结算仍依赖受控账本写入契约。 |

实际验证：现有 **5 tests，OK，退出码 0**；另 **12 个独立手写场景通过，退出码 0**。其中 9 个为适配/评分/组抽样场景，3 个为费用代码片段场景。为遵守读取范围，协议 judgment 校验函数及费用片段从指定源码 AST 中抽取后在内存执行，未导入范围外项目模块，未执行任何真实文件读取或保存路径。评分输出检查 JSON 无 NaN。

已解决的问题 A1：旧入口忽略 `validate_result` 的标准化返回副本，且旧 valid 只判断 parsed 非空；协议允许的列表条件可能使 scorer 判 invalid、comparisons 判正确。最小修复已采用标准化副本并复用评分器有效性规则，当前手写夹具验证通过。此项是接口防御缺口；未读取实际 accepted，不能据此声称真实结果曾受影响。

本审核不证明实际推理已终止、真实 72 条数据完整、参考正确、账单金额或模型效果；只确认当前适配与统计代码口径。无需据本审核调整冻结推理、提示词、检索或判定参数。
