# 法规边界增量交付

先读来源核验报告.md和机制解释覆盖层.md。机器入口如下：

- source_verification.jsonl：10核心来源和L011/L012共12条核验记录；全部pending。
- rule_patch.jsonl：12机制解释补丁，不改原文，不新增独立违法条件。
- baseline_operational_rules.json / operational_rules_overlay.json：旧/新两臂条件卡。
- support_articles.jsonl：42条原文、原区间与原SHA，两臂共同使用。
- fact_and_scope_policy.json：事实来源与适用范围协议，两臂一致。
- boundary_inputs.jsonl：24条input-only；boundary_reference.jsonl只用于离线评分。
- boundary_freeze.json：最终输入与卡片的冻结指纹。
- boundary_experiment_design.json：两臂合计最多48判断、输出契约与局限。
- acquisition_results*.json：原件两轮下载失败记录；source_artifacts/reader_snapshots只为工具返回快照。
- verification.json：结构/区间/指纹核验；SHA256SUMS为实际交付文件清单。

本子任务付费API调用0。未取得官方原始HTML/PDF，原件SHA不存在。L011/L012未完成完整官方全文及现行效力核验，不能据此新增active。DeepSeek成绩由主代理统一生成，本目录不提前给性能结论。
