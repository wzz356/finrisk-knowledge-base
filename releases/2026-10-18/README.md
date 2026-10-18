# FinRisk 知识库增量交付（2026-10-18）

本次在[2026-10-17基础交付](../2026-10-17)上提供版本交接、定向证据范围、法规来源与边界、辅助检索实验。当前案例仍为9639份、15620个主体案件、25186条行为候选，使用官方27类标签；本轮没有全量重生成或切换应用默认。

先读[验收报告](data/验收报告.md)及[接入说明](data/接入说明.md)。发布中的原报告和规划保留生成时状态，其中“未上传”是历史记录；本次Git提交即为发布状态。

## 可交接成果

|成果|入口|采用范围|
|---|---|---|
|版本与证据交接|[交接说明](data/handoff_scope/交接说明.md)、[版本锁](data/handoff_scope/version_lock.json)、[33条绑定修复](data/handoff_scope/projection_candidate_rebinds.jsonl)|保留稳定ID；9处局部ID差异有显式映射|
|分层证据范围|[范围覆盖](data/handoff_scope/scope_overlays.jsonl)、[阅读样例](data/handoff_scope/evidence_samples.jsonl)、[只读加载器](data/handoff_scope/evidence_loader.py)|16份定向文书＋1份修正样例＋2个法条单元；57个登记区间；不代表全库人工审核|
|法规阅读与解释|[交付43条](data/delivery_articles43.jsonl)、[解释覆盖层](data/law_review/机制解释覆盖层.md)、[来源核验](data/law_review/来源核验报告.md)|固定实验42条另存；交付补第40条依赖；12来源均未提升production_active|
|事实与候选边界|[证据契约](data/boundary_evidence_contract.json)、[事实策略](data/law_review/fact_and_scope_policy.json)|案例和法条不能替代本次业务事实；嫌疑标签与机制成立分开|
|检索辅助表达|[12机制表达表](data/auxiliary_lexicon.json)|仅实验配置，未全局启用；BM25:BGE维持1:1|
|讨论与后续方向|[Agentic RAG讨论](docs/FinRisk_AgenticRAG讨论结论_20261018.md)、[改进建议原稿](docs/FinRisk_知识库下一阶段改进建议_20261018.md)|后者是本轮实施前建议，完成状态以本验收报告为准|

基础候选仍从[10月17日交付中的effective_candidates](../2026-10-17/outputs/FinRisk_知识库V2.1轻量收尾_20261015/effective_candidates.jsonl.gz)读取draft；本目录是增量覆盖与评测，不重复上传全9639篇。

## 新增全库检索对照

[24条业务输入](data/queries_final.jsonl)，全9639篇/65475结构化单元初检，BM25+BGE→1:1 RRF→DeepSeek Flash重排。两臂4800候选位置，3411个唯一配对评分；源文件Top20并集674配对、369份文书全文盲标。大JSONL无损gzip，见[data排名](data/rankings.jsonl.gz)、[相关性银标](data/qrels_silver.jsonl.gz)、[逐题指标](data/retrieval_per_query.jsonl)、[指标汇总](data/retrieval_metrics.json)。

|12道风险题，探索指标|原查询|增加辅助表达|
|---|---:|---:|
|Top-1直接支撑命中率|75.00%|83.33%|
|MRR@20|0.8194|0.8611|
|pool-NDCG@20|0.8565|0.9286|
|Precision@20|45.00%|51.25%|
|Success@20|91.67%|91.67%|

Top1/MRR改善只由1题驱动。另12道正常或信息不足题仅作描述：Top1由25.00%降至16.67%，MRR由0.3167降至0.2528；这是证据相关性，不是风险判别误报率。辅助表达保持实验配置。电子代签题存在把具体手段当核心条件的疑似过严银标，冻结标签未事后改写。

**没有测得真实全库Recall。** pool-NDCG以两臂公共Top20池构造理想排序；池外没有完整标注。输入与辅助表同作者、重排与标注同模型家族；解析/传输协议在实测中有修订且完整披露，结果不冒充原协议完全不变、专家金标或官方竞赛成绩。不与旧90题/闭集成绩直接相减。

## 法规边界与未完成事项

24条配对合成输入、两臂48次判断：原解释卡和修订卡均23/24状态正确、21/24机制集合完全正确，**未显示修订卡增益**。两臂采用相同42条文与事实协议，只检验解释卡增量，不能推断整套法规库相对不使用法规的收益。

原始官方HTML/PDF取得0；保留官方阅读快照身份及待核状态，L011/L012仍有全文/效力待核。交付43条不是完整法规库，也没有补齐官方27类全部规则边界。新增事实契约只完成机械一致性检查，尚非Agent运行时实现或新模型效果证明。

## 下载后离线复算

保留本目录层级，执行：

```powershell
python -S -X utf8 -B 'releases/2026-10-18/reproduce.py'
```

只需Python标准库，不联网、不读取密钥、不收费。它从原始响应重建3411评分、48组排名、674对标注和原文引文，并重算两组指标、48边界判断及费用；先核验[发布manifest](manifest.json)。压缩文件解压后与原文件字节相同；[筛选与来源指纹](selection_provenance.json)说明保留范围和复算脚本仅增加gzip读取支持的改动。

本轮实验费用保守计入$0.740397141，含未知调用完整预留，非供应商账单；**本次GitHub整理上传新增模型调用0**。原始响应与费用账本采用gzip保留在audit，用于结果追溯；重复任务快照、临时目录、向量和完整本地执行历史未上传。重新计算BM25/BGE初检需另备原索引、已登记模型与依赖；本离线入口复算已保存的真实结果，不重跑模型。
