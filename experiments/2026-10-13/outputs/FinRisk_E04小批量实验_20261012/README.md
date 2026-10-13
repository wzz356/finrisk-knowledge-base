# E04小批量实验成果

完成于2026-10-13。12条开发输入、4个配置；10条新来源确认输入、2个配置。共68条检索结果记录，132个查询—文书配对及132个实际片段评分完整。

**结论：保留A0。**A1在开发集有改善迹象，需统一评分并做新来源确认；扩大候选池的A3在本轮确认集没有提高有用片段率。结果为模型辅助评价，无人工金标。

- [实验报告](./实验报告.md)：配置、实际指标、选择规则、失败分析、教材对应与下一步。
- [失败与边界样例](./失败样例.md)：按实际返回原话说明哪里有帮助、哪里没有。
- [复跑说明](./复跑说明.md)：当前本机环境的执行入口、输入依赖和保护边界。
- [核验结果](./verification.json)、[交付清单](./delivery_manifest.json)。
- 开发：`dev_queries.jsonl`、`dev_results.jsonl`、`dev_evaluation/metrics.json`、`dev_evaluation/per_query_metrics.jsonl`。
- 确认：`confirmation_queries.jsonl`、`confirmation_results.jsonl`、`confirmation_evaluation/metrics.json`、`confirmation_evaluation/per_query_metrics.jsonl`。
- 冻结：`input_freeze.json`、`execution_freeze.json`、`confirmation_freeze.json`、`selection.json`。
- 运行参数/模型/分数来历：两个结果文件的`.run.json`、`.score_pool.jsonl`、`.token_audit.jsonl`。
- 各阶段`*_judgments/notes_p*.md`记录评分过程和实际接触的字段，尤其确认盲评局限。

原V2知识库、旧缓存和应用配置保持原状；本轮结果尚未上传GitHub。
