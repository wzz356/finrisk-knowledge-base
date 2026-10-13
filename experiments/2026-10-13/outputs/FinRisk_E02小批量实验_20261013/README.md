# E02背景前缀小批量实验

完成于2026-10-13。24份文书/24个代表单元、22条固定回放输入、3方案/66条检索结果，125全文与146上下文模型评分完整。

**结论：暂不全量铺开，保留A0。**P1有用片段85→86/110，覆盖21/22不变；P2仍85/110。两份多主体父上下文存在背景范围hold，须先修展示与关联范围。结果为模型意见，没有独立人工金标。

- [实验报告](./实验报告.md)：实际指标、教材对应、数值刷新控制、失败及下一步。
- [5个样例对比](./样例对比.md)：直接对比真实返回原话和模型理由。
- [设计](./design.md)、[评分规则](./评分规则.md)、[复跑说明](./复跑说明.md)。
- `cohort.json`、`queries.jsonl`、`prefixes.jsonl`、`prefix_review.jsonl`、`prefix_quality.json`：抽样、背景与原文支持/审核。
- `results.jsonl`及`.run.json`、`.score_pool.jsonl`、`.token_audit.jsonl`：真实检索阶段、模型/分数来历与耗时。
- `evaluation/metrics.json`、`per_query_metrics.jsonl`、`validated_judgments.jsonl`：统一全新评分和逐位置指标。
- `return_scope_review.jsonl`、`decision.json`：原单元批准之外的扩展阅读hold及采用决定。
- `query_vector_refresh_audit.json`、`query_vector_candidate_control.json`：浮点刷新与固定评分池Top5稳健性诊断。
- [最终核验](./verification.json)、[交付清单](./delivery_manifest.json)。

这些前缀是实验候选。旧库、应用默认和E04交付未变；本轮没有推送GitHub，也没有启动下一轮范围修正。
