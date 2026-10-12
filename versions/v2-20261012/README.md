# FinRisk V2：9639份离线候选知识库与复测

这是V2发布版本。统一9639份文书、15620个主体案件、25186条行为，157份有效修订；早期30份已迁移官方27类召回优先标签。全量机械检查、登记对账和保存输入恢复通过。当前有9项展示字段/片段的人工判断，完整文书批准0，应用默认库未切换。

## 直接阅读

- [9639份有效候选](data/candidates)、[文书定位索引](data/file_index.jsonl)。每份候选直接包含当前有效draft，保留基线稿/来源/版本SHA与相对定位。
- 原文共享仓库根目录[data/sources](../../data/sources)，原稿共享[data/candidates](../../data/candidates)。版本索引source/base_candidate的path均相对仓库根目录。
- [V2重建与召回复测报告](V2重建与召回复测报告.md)、[任务清单](任务清单状态_V2.md)、[阅读导航](normalized_final/INDEX.md)。
- [14组指标](metrics/metrics.json)、[逐查询指标](metrics/per_query_metrics.jsonl)、[固定50查询](evaluation/queries.jsonl)。
- [同8509结果](retrieval/same8509_final_results.jsonl)、[全9639结果](retrieval/all9639_results.jsonl)。两范围各200条真实结果。
- [质量冻结](quality/input_freeze.json)、[登记对账](registration_final/registration_verification.json)、[恢复报告](recovery/recovery_report.json)。
- [最新人工验收记录](human_acceptance/验收进度.md)、[后续模型审核委托](human_acceptance/delegated_review_authorization.json)。

冻结报告中的human0/尚未发布是当时历史状态；以上最新人工记录和本发布版本说明当前状态，不覆盖原证据。

## 当前检索效果

| 全9639结构化方案 | 有用文件@5 | 有用片段@5 |
|---|---:|---:|
| BM25 | 78.4% | 78.8% |
| BGE | 67.2% | 61.2% |
| 双路RRF | 77.6% | 73.6% |
| RRF＋rerank | 74.8% | 72.8% |

BM25改善，RRF/rerank相对V1回退。同8509受控范围也显示回退，原基线保留。50条是开发查询，模型评分不是全库人工金标；nDCG只针对联合已评池，不能称全库Recall。9项人工核定不会自动改写冻结指标。16处全文/片段判断分歧、旧关注队列未全审、责任关系表0等限制详见总报告。

## 大文件读取与无损恢复

超过20MiB的JSONL以“同名目录”保存，目录内是按原行顺序的gzip分片和parts.json；因此上面的同名链接可以直接打开分片目录。所有八表、引用/ID映射、阅读索引、两范围raw/structured投影、完整结果及评分内容均已保存，没有只上传摘要。

克隆整个仓库后，核验本版本：

```powershell
python .\tools\verify_v2_release.py --repo .
```

恢复原始文件名、逐字节内容及SHA到一个空目录：

```powershell
python .\tools\v2_payloads.py --version .\versions\v2-20261012 --destination .\restored-v2
```

恢复只用Python标准库。恢复输出仍保留原运行时点的绝对路径等历史元数据；跨机器GPU复跑需安装依赖、取得对应BGE/reranker和配置路径，仓库不含模型权重或向量缓存。候选与共享原文直接从整个仓库读取，无需为了单份候选恢复全部大文件。

[公开文件清单](publication_manifest.json)核验本目录实际公开文件；[原始载荷映射](payload_map.json)核验拆分前SHA；[本地原冻结清单](baseline/delivery_manifest.json)包含未发布的本地冗余/SQLite资产，仅作历史证据，不把它当公开文件全集。
