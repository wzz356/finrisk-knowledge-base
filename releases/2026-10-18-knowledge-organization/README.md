# 知识组织增强：资料、实验与交付（2026-10-18）

在现有9639份案例库上增加可选知识阅读层：12机制卡、67条法规统一阅读、L0/L1/L2导航、双向链接、条件证据包和依赖变更检测。全库检索仍为BM25＋BGE、1:1 RRF、deepseek-flash重排，未切换默认配置。

[验收报告](验收报告.md) · [完整可复核包](FinRisk_知识组织增强_交付_20261018_v2.zip) · [采用决定](contracts/adoption_decision.json) · [读取接口](contracts/read_api.md)

## 本轮实现

|内容|公开浏览入口|范围|
|---|---|---|
|12机制卡与案例原句|[mechanisms](expanded/knowledge/mechanisms.jsonl)、[导航](expanded/navigation/index.json)|59份精读全文、78原句、109链接；资料不齐保留partial|
|法规阅读注册|[67条法规](legal/articles.jsonl)、[阅读依赖](legal/dependencies.jsonl)、[来源](legal/source_registry.jsonl)|核心43＋补充24；快照身份/效力待核保留，未提升生产准入|
|分组测试集|[24段业务输入](evaluation/queries.jsonl)、[故事分组](evaluation/group_split.json)、[模型银标参考](reference/model_silver_expected.jsonl)|8故事组；开发12／4组，保留12／4组；非专家金标|
|判断对照K|[指标](experiment_K/metrics.json)、[48逐题结果](experiment_K/per_query_results.jsonl)|固定案例排名及实际文本；开发7次失败完整保留|
|前缀对照R|[正式受控指标](experiment_R_controlled/metrics.json)、[共享参考](experiment_R/qrels_development_shared.jsonl)|仅20片段改变BM25/dense表示；原查询向量复用|
|维护与成本|[维护范围](reports/update_runbook_final.md)、[费用](reports/cost_audit.json)、[补充指标](reports/additional_descriptive_metrics.json)|4313节点；仅影响检测与投影暂存，不自动生成/发布|

## 结果与采用决定

|实验|基线|增强|决定|
|---|---:|---:|---|
|K保留12题三态正确|12/12|11/12|未过采用门槛，组织层保持可选|
|K保留引用语义支持|22/39，56.41%|20/40，50.00%|登记原句存在不等于足以支撑结论|
|R开发Top-1直接支撑|7/12|7/12|未提升|
|R开发MRR@20|0.6694|0.6556|下降，停止前缀扩量与新R保留题|
|R开发池内NDCG@20|0.9296|0.9345|小幅升高不足以满足事前门槛|

K两臂案例排名完全相同，不能声称其召回提升。R的相关性仅覆盖两臂Top20并集245配对，NDCG按此已判池构造理想排序；**未测得真实全库Recall**。重排与相关性银标使用同一模型，存在共同偏差。参考修订敏感性保留在[独立报告](reports/metadata_sensitivity.json)，不把标签变化算作方案增益。

知识组织覆盖59份文书；便携验收快照为732单元／481文书；实际检索在9639份／65475结构化单元中进行。这些数字指不同范围，不能混同全库重审。官方27标签16项部分涉及、11项本轮未覆盖；M03/M08/M12等直接材料不足保留缺口。生产自动重建、在线Agent接入、RAPTOR／GraphRAG均未在本轮实现。

## 下载与复核

完整ZIP保留697个载荷：实际读取子集、67条法规及来源快照、卡片、代码、冻结协议、原始模型响应/失败/账本、参考、排名、语义审核、指标和独立审核记录。ZIP字节与本地验收版一致。散列见[发布清单](manifest.json)与[来源选择记录](selection_provenance.json)。松散文件仅供浏览，完整阅读器和法源依赖从ZIP读取。

克隆仓库后执行：

```powershell
python -S -X utf8 -B 'releases/2026-10-18-knowledge-organization/reproduce.py'
```

仅需Python标准库；先验证发布载荷，再在临时新目录解压原ZIP，回放960个旧排名位置、732单元、67条法规、12机制、K/R指标、费用及维护依赖。它不联网、不读取密钥、不重跑模型或全库初检，`new_model_calls=0`。也可下载ZIP后执行其中 `code/cli.py verify --root 解压目录`。

本轮主测试60项通过。API保守记账上界1.152937092美元，2笔未知usage全额预留，低于批准2美元；不是供应商实际账单。本次整理上传没有新增模型调用。

ZIP内报告与执行记录保留生成时状态，其中“未上传GitHub”为历史描述；本目录提交后即为本轮发布。既有[10月17日基础候选](../2026-10-17)及[较早10月18日增量](../2026-10-18)保留。下一步宜优先修正候选机制漏项和规范适用/预算选择，在全新话术上验证，不先扩展无实测收益的大型组织方案。
