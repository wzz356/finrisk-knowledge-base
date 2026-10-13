# E01–E04五小时实验交付

42条文字（22回放、20新文字），全9639份文书/65475单元竞争。210条主真实检索，另有固定排序显示及组合各126条，含重复父结果；去重为8方案×42=336种输入/方案记录。

**推荐：2:1检索权重作为候选，范围修正仅在已审对象试用；暂不全量生成背景或常开机制卡。**新文字有用片段59/100→W4的63/100；组合65/100，但排除两个有争议的跨产品核查类比后仍是63/100。结果是模型意见，非人工金标。

- [实验总报告](./实验总报告.md)：E01–E04分项结论、指标、剂量、退步及敏感性。
- [完整方案](./完整方案.md)：下一离线版本候选流程、实际落地与后置范围。
- [5个样例](./样例对比.md)：原样展示真实返回文字与评分。
- [复跑说明](./复跑说明.md)：现有环境、依赖及新输出约束。
- [主核验](./verification.json)、[补充核验](./verification_extra.json)、[交付清单](./delivery_manifest.json)。

主数据results.jsonl、evaluation；显示display_results.jsonl、display_evaluation；组合combo_results.jsonl、combo_evaluation。analysis.json统一汇总，sensitivity.json只针对两个争议位置，不改评分。judgments保留全部本轮判断、输入和阅读记录。

scope_units/源review、mechanism_cards/源review、input_freeze/execution_freeze、真实GPU/score/token侧车完整保留。未改变旧来源、库默认、应用接口；本轮未推送GitHub。该交付不等于基础全量语义验收或所有增强技巧完成。
