# FinRisk 重建知识库

**当前版本：[V2 / 9639份知识库与召回复测](versions/v2-20261012)。** 关联应用：[finrisk-workbench](https://github.com/wzz356/finrisk-workbench)。

V2完成统一八表、稳定ID、原文证据绑定、阅读入口和两范围检索投影，修订157份有效候选，早期30份迁移官方27类标签。全量机械检查、8509主批次登记对账与保存输入恢复通过。当前9项展示字段/片段已人工判断，完整文书批准0；后续复核由用户委托助手，判断来源保持模型复核。应用默认库未切换。

## 当前数据与实验入口

- [9639份V2有效候选](versions/v2-20261012/data/candidates)、[文书定位索引](versions/v2-20261012/data/file_index.jsonl)、[共享原文](data/sources)。
- [V2重建与召回复测报告](versions/v2-20261012/V2重建与召回复测报告.md)、[任务清单进度](versions/v2-20261012/任务清单状态_V2.md)。
- [八表与阅读导航](versions/v2-20261012/normalized_final/INDEX.md)、[检索投影](versions/v2-20261012/indexes)、[完整实验结果](versions/v2-20261012/retrieval)、[完整评分与指标](versions/v2-20261012/metrics)。
- [人工验收记录](versions/v2-20261012/human_acceptance/验收进度.md)、[质量/登记/恢复及使用说明](versions/v2-20261012/README.md)。

| 全9639结构化方案 | 有用文件@5 | 有用片段@5 |
|---|---:|---:|
| BM25 | 78.4% | 78.8% |
| BGE | 67.2% | 61.2% |
| BM25+BGE→RRF | 77.6% | 73.6% |
| RRF→rerank | 74.8% | 72.8% |

50条开发查询、真实BGE及reranker；全文与实际片段分别模型评分。BM25改善，双路/Rerank回退，尚未切默认库。两范围V2共400结果，加V1六组后14组/700记录；1000个query-file配对、1670种片段。nDCG是池内条件指标，不能称全库Recall或官方竞赛成绩。

## 版本与校验

根目录data/candidates、indexes/2026-10-12、evaluation/2026-10-12及quality/2026-10-12保留V1基线；[V1历史说明](docs/V1_README_20261012.md)。读取当前候选请用versions/v2-20261012/data/candidates。V2原文共享根data/sources，字典仍是[官方27类](dictionary/risk_type_dictionary.csv)。

```powershell
python .\tools\verify_repository.py
python .\tools\verify_v2_release.py --repo .
```

大JSONL采用无损gzip分片，有同名目录及恢复工具，详见[V2使用说明](versions/v2-20261012/README.md)。[根发布清单](manifest.json)核验本仓库实际文件，[V2清单](versions/v2-20261012/publication_manifest.json)核验版本载荷。

360份预留正文、凭据、教材原PDF、模型权重、虚拟环境、向量缓存和本地SQLite备份不在新版本中。此版本是离线候选与实验归档，机械通过不等于全案语义审核或正式应用上线。
