# 独立规格审核

结论：复验后的受审代码无未解决阻断项。此结论限于离线工程实现，不替代全量机械验收、法律语义审核或专家金标。

按 `2026-10-18-finrisk-evidence-runtime-design.md` 先核对规格，再做质量检查；审查目标代码及测试，只写本目录四份报告。未重新构造600MB全量读器，未新增API调用。

## 已修复问题

**SPEC-R1，P1，scope_selector.py:39。** 原实现把不同stage枚举一律判mismatch。真实资料复现：`保险公司在售前介绍万能型保险。`，范围为insurer/universal_life/pre_sale，M05装配会排除L005-A0012的万能产品说明书风险提示和L005-A0029的适用范围。信息披露与售前/回访可以重叠，仅字面分类不同不足以证明互斥。最小修复是未登记互斥依据的stage差异保守conditional。该修复已落地；新增单测和实际67条资产回归通过，L005-A0012/L005-A0029均conditional并完整装入。

## 规格核对

- P0-A：外部清单SHA、DB载荷SHA与五版本核验；SQLite mode=ro/immutable/query_only；按ID映射、有界字节缓存；原单元/候选/来源保留；未知ID、bool/越界区间、未审旧绑定和额外span有拒绝验证。旧接口原字段由冻结基类复用。
- P0-B：侧表覆盖67条、原文和来源位置回放；排除依据按axis direct_literal检查；unknown/general不硬排除；当前输入引用标current_input且字面核验，不冒充事实核准；规范原文优先，全文和依赖整组纳入或整组预算省略。阶段重叠问题已修复。
- P0-C：12个已登记机制无2个候选上限；触发span可回读；读取与调用方声称检查分开；否定仅候选，无触发明确unmapped；无风险成立或整段安全自动结论。

## 实际验证与边界

最新统一轻量复验40项通过：FullReader小夹具12项、scope 11项、packer 6项、coverage 5项、assets 3项、CLI 3项。额外实际资料探针验证阶段保留，以及3机制/12机制装配补读与已纳入集合不相交，文本均不超8000字。

未运行会重新构造全量读器的test_evidence_runtime.py，未独立重做110878单元/9639全文候选与旧960逐值验收；这些最终结果须引用主流程实际报告。新题独立性和最终封包也由主流程验收。L002-A0029侧表修补已另行登记，不重复计为实现缺陷。

## 最后增量审核

runtime_cli.py及tests/test_runtime_cli.py已纳入受审SHA。白名单只允许公开知识操作，close等私有操作拒绝；root/pin必须显式输入；serve仅在循环外构造一个EvidenceRuntime，逐行复用。新增坏数据库参数容错缺口（QUALITY-R3）已修复并用真实小FullReader验证：坏参数返回ok=false后，同一实例继续完成有效读取。

最终policy的L002-A0029修补符合scope_review/review.json的SCOPE-001最小建议：保留旧actor标签并加入general、actor basis改assistant_interpretation、conditional_axes加入actor，原文SHA、书面委托及销售人员不得代确认分支保留。仅该条变化，结果SHA与reports/scope_patch.json一致；多主体匹配均保持conditional。本次未重新执行67条内容审核。
