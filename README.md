# FinRisk 重建知识库

**最新交付：[知识组织增强、67条法规统一读取与K/R实验（2026-10-18）](releases/2026-10-18-knowledge-organization)。基础案例仍为9639份，双路融合1:1；增强方案未达采用门槛，保持可选。** 关联应用：[finrisk-workbench](https://github.com/wzz356/finrisk-workbench)。

## 本轮知识组织与实验

[验收报告](releases/2026-10-18-knowledge-organization/验收报告.md) · [完整复核包](releases/2026-10-18-knowledge-organization/FinRisk_知识组织增强_交付_20261018_v2.zip) · [读取接口](releases/2026-10-18-knowledge-organization/contracts/read_api.md) · [离线复算](releases/2026-10-18-knowledge-organization/reproduce.py)

新增12机制卡、67条法规注册、分层导航、证据包与依赖影响检测。K保留12题正确数12→11，R定向前缀Top-1持平且MRR下降，两项均未过预设门槛；不替换现有默认。不宣称实测全库Recall或专家金标。完整包真实解压核验697载荷、旧960位置与全部指标通过；主测试60项通过。资料精读59份、便携读取481份与实际检索9639份分别报告。

```powershell
python -S -X utf8 -B 'releases/2026-10-18-knowledge-organization/reproduce.py'
```


## 最新增量成果与核验（2026-10-18）

[成果索引](releases/2026-10-18/README.md) · [验收报告](releases/2026-10-18/data/验收报告.md) · [接入说明](releases/2026-10-18/data/接入说明.md) · [离线复算](releases/2026-10-18/reproduce.py)

新增33条版本绑定修复、定向证据分层与57个原文区间、43条法规交付阅读包及事实证据契约。24条新业务输入在全9639篇检索，完成3411组重排和674对银标；12道风险题Top1为75%→83.33%、MRR@20为0.8194→0.8611、pool-NDCG@20为0.8565→0.9286。Top1/MRR仅1题改善，描述组存在退步，辅助表达保持实验配置。

法规卡对照两臂均23/24状态正确，未显示增益；官方原件取得0，待核来源不提升正式准入。全部结果均按小样本银标探索报告，**没有测得真实全库Recall**。基础候选仍用[10月17日交付](releases/2026-10-17)。

```powershell
python -S -X utf8 -B 'releases/2026-10-18/reproduce.py'
```

V2完成统一八表、稳定ID、原文证据绑定、阅读入口和两范围检索投影，修订157份有效候选，早期30份迁移官方27类标签。全量机械检查、8509主批次登记对账与保存输入恢复通过。当前9项展示字段/片段已人工判断，完整文书批准0；后续复核由用户委托助手，判断来源保持模型复核。应用默认库未切换。

## 基础交付与答辩入口（2026-10-17）

[交付说明](releases/2026-10-17/README.md) · [答辩索引与结果总览](releases/2026-10-17/答辩索引.md) · [正式90题](releases/2026-10-17/outputs/FinRisk_正式测试集V2_20261017/queries.jsonl) · [复算入口](releases/2026-10-17/reproduce.py)

V2.1将9639份当前候选和5份既有修正合并，原文与全量投影复用仓库V2。新增10份官方来源阅读快照、64条法规和24张条件卡。精简交付保留正式数据、冻结设计、实际排名、模型预测、逐题指标与复算代码，省去完整API日志、临时文件和重复大包。

24题×100篇文书的完整闭集，DeepSeek Recall@20=80.22%、MRR@20=0.7422、NDCG@20=0.7232、Top-1=70.83%。同24题扩大到9639篇后，Top-1=45.83%、MRR@20=0.5069，已知参考微平均覆盖39.39%，后者不是全库Recall。90题两臂未显示最终判断的RAG增益；法规快速修复在已见36题中正确29→34。不同实验范围分开报告，模型银标不当人工金标。

```powershell
python -S -X utf8 -B 'releases/2026-10-17/reproduce.py'
```

当前候选请读取[effective_candidates.jsonl.gz](releases/2026-10-17/outputs/FinRisk_知识库V2.1轻量收尾_20261015/effective_candidates.jsonl.gz)中每行的`draft`。旧V2、旧20题和旧开发实验保留为历史基线；现有应用默认未切换。

## 最新召回测试集与指标（2026-10-15）

[本次实验与全部结果](experiments/2026-10-15) · [完整指标报告](experiments/2026-10-15/outputs/FinRisk_可用测试集_v1_20261015/指标报告.md) · [下载可移植测试集](experiments/2026-10-15/outputs/FinRisk_可用测试集_v1_20261015/FinRisk_测试集_v1_可移植包.zip)

20条源机制合成业务输入、100份真实文书、2000个配对完整模型标注，两轮盲读和争议裁定；主指标只把3分“直接支撑”当相关。BM25+BGE按1:1 RRF融合，比较交叉编码器与真实deepseek-flash重排。完整参考、实际排名、API评分与独立评分工具已保存。

|闭集方法|Recall@20|MRR@20|NDCG@20|Top-1|
|---|---:|---:|---:|---:|
|1:1 RRF|86.71%|0.8350|0.7367|75%|
|RRF＋BGE交叉编码器|87.83%|0.8663|0.7734|80%|
|RRF＋DeepSeek Flash|90.73%|0.9375|0.8868|90%|

以上Recall仅针对封闭100份文书。全9639补充检索的DeepSeek Top20完整标注后，Top1=90%、MRR@20=0.95、Precision@20=65.25%；已知闭集参考覆盖@20=31.81%，不作为全库真实Recall。测试集是未经人工批准的模型银标诊断集，不是官方竞赛成绩，不与旧口径直接比较；没有切换应用默认库。

## 最新演示、实验与完整方案（2026-10-13）

[完整方案/任务清单进度](experiments/2026-10-13/outputs/FinRisk_E07_E06_E05探索_20261013/完整方案.md) · [最新实验总报告](experiments/2026-10-13/outputs/FinRisk_E07_E06_E05探索_20261013/实验总报告.md) · [全部五个实验封包](experiments/2026-10-13)

已保存E01–E04受控实验、1:1离线演示V3，以及E07→局部E06→小样本E05。当前保留1:1主流程；E07三态核查清单与E06关系注释为候选，自动事件后置补位与摘要树未启用，E08暂缓。

E06重复占位3→0，但有用位置53→51/80；E05统一新评原版47/80、目录和树45/80，宽核查口径均53/80持平，故没有扩量启用依据。指标口径和输入批次不同，不与下面V2历史50查询分数直接相减。480份原始载荷无损保存，完整结果/源审/判断/代码和SHA都可下载恢复。

```powershell
python .\tools\verify_experiments.py --repo .
```

## 历史V2基线数据与实验入口

- [9639份V2有效候选](versions/v2-20261012/data/candidates)、[文书定位索引](versions/v2-20261012/data/file_index.jsonl)、[共享原文](data/sources)。
- [V2重建与召回复测报告](versions/v2-20261012/V2重建与召回复测报告.md)、[任务清单进度](versions/v2-20261012/任务清单状态_V2.md)。
- [八表与阅读导航](versions/v2-20261012/normalized_final/INDEX.md)、[检索投影](versions/v2-20261012/indexes)、[完整实验结果](versions/v2-20261012/retrieval)、[完整评分与指标](versions/v2-20261012/metrics)。
- [人工验收记录](versions/v2-20261012/human_acceptance/验收进度.md)、[质量/登记/恢复及使用说明](versions/v2-20261012/README.md)。

以下为V2构建期50条开发查询的历史对照；最新演示与增强结论见上面的独立归档。

| 全9639结构化方案 | 有用文件@5 | 有用片段@5 |
|---|---:|---:|
| BM25 | 78.4% | 78.8% |
| BGE | 67.2% | 61.2% |
| BM25+BGE→RRF | 77.6% | 73.6% |
| RRF→rerank | 74.8% | 72.8% |

50条开发查询、真实BGE及reranker；全文与实际片段分别模型评分。BM25改善，双路/Rerank回退，尚未切默认库。两范围V2共400结果，加V1六组后14组/700记录；1000个query-file配对、1670种片段。nDCG是池内条件指标，不能称全库Recall或官方竞赛成绩。

## 版本与校验

根目录data/candidates、indexes/2026-10-12、evaluation/2026-10-12及quality/2026-10-12保留V1基线；[V1历史说明](docs/V1_README_20261012.md)。当前有效稿请用上方V2.1入口，versions/v2-20261012/data/candidates保留为基线。V2原文共享根data/sources，字典仍是[官方27类](dictionary/risk_type_dictionary.csv)。

```powershell
python .\tools\verify_repository.py
python .\tools\verify_v2_release.py --repo .
```

大JSONL采用无损gzip分片，有同名目录及恢复工具，详见[V2使用说明](versions/v2-20261012/README.md)。[根发布清单](manifest.json)核验本仓库实际文件，[V2清单](versions/v2-20261012/publication_manifest.json)核验版本载荷。

360份预留正文、凭据、教材原PDF、模型权重、虚拟环境、向量缓存和本地SQLite备份不在新版本中。此版本是离线候选与实验归档，机械通过不等于全案语义审核或正式应用上线。
