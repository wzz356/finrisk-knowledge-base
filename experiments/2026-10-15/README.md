# 20题×100源文书：可用测试集v1与真实召回实验

2026-10-15发布。20条业务输入、100份真实完整文书，2000个问题—文书配对穷尽标注；另在9639份现有知识库上补充检索，并标注DeepSeek实际Top20的400配对。本次新增模型判断均为human_approved=false，不更改现有知识库的候选/批准状态。

- [实验完整报告](outputs/FinRisk_可用测试集_v1_20261015/指标报告.md)
- [测试集说明与独立评分入口](outputs/FinRisk_可用测试集_v1_20261015/README.md)
- [下载约1MB可移植包](outputs/FinRisk_可用测试集_v1_20261015/FinRisk_测试集_v1_可移植包.zip)
- [5个人工验收样例](outputs/FinRisk_可用测试集_v1_20261015/人工验收样例.md)
- [20条问题](outputs/FinRisk_可用测试集_v1_20261015/queries.jsonl)、[100份完整源文书](outputs/FinRisk_可用测试集_v1_20261015/corpus.jsonl)、[2000条最终参考](outputs/FinRisk_可用测试集_v1_20261015/qrels.jsonl)
- [五阶段实际文书排名](outputs/FinRisk_可用测试集_v1_20261015/rankings)、[逐题指标](outputs/FinRisk_可用测试集_v1_20261015/metrics)、[全库Top20补标](outputs/FinRisk_可用测试集_v1_20261015/supplement_qrels.jsonl)

## 封闭100文书：主指标

全部采用3分“同机制直接支撑”，20题等权宏平均。Recall分母完整，但只限这100份文书。主NDCG使用二值相关性；附分级NDCG和Recall@5/10见完整报告。

|方法|Recall@20|MRR@20|NDCG@20|Top-1|
|---|---:|---:|---:|---:|
|BM25|86.40%|0.8612|0.7762|80%|
|BGE向量|74.25%|0.7806|0.6331|65%|
|1:1 RRF|86.71%|0.8350|0.7367|75%|
|RRF＋BGE交叉编码器|87.83%|0.8663|0.7734|80%|
|RRF＋DeepSeek Flash|90.73%|0.9375|0.8868|90%|

两路各100单元，RRF权重1:1、k=60，前100候选单元分别交给交叉编码器与真实deepseek-flash API重排，按文书最高单元分聚合。原参数和模型保持不变。

## 全9639份补充检索

DeepSeek实际Top20完整判断后：Top1=90%（18/20）、MRR@20=0.95、Precision@5=87%、Precision@10=78.5%、Precision@20=65.25%、Success@20=100%。其中365个库外配对涉及281份原文，35对复用闭集既有参考。

全库已知闭集参考覆盖@20为31.81%，它不是全库真实Recall。全9639×20没有穷尽标注，不能用Top20已见相关数充当全库分母，也不能用池内理想排名冒充完整NDCG。精选小库、源机制合成问题、成对机制和模型银标存在偏差；本轮成绩不能与旧50题、官方题或不同相关性口径直接相减。

## 下载后复算

在仓库根目录执行，不调用模型或API，只需要Python标准库：

```powershell
python '.\experiments\2026-10-15\outputs\FinRisk_可用测试集_v1_20261015\evaluate.py' --dataset '.\experiments\2026-10-15\outputs\FinRisk_可用测试集_v1_20261015' --rankings '.\experiments\2026-10-15\outputs\FinRisk_可用测试集_v1_20261015\rankings\closed100_ND.jsonl' --output '.\replay_closed100_ND.json'
```

或者下载上面的ZIP，在解压目录按其README复算。输出文件须尚不存在。排名必须逐题精确覆盖20题、使用去重F编号，闭集之外的文书会被拒绝，不默认填0。ZIP已在独立目录实际复算五种排名，指标完全一致。

## 归档范围与恢复

本次按原字节保存177个原始载荷，约196.6MiB，公开载荷约51.2MiB。包含完整问题/源全文、两轮闭集标签与裁定、全库补充标签、真实API输入/响应/评分/费用、阶段排名、评估/检索脚本、验证和原始封存记录。没有重新跑推理或产生新的API费用。

超过20MiB的JSONL按仓库既有格式无损gzip分片，表现为同名目录，内有parts.json及分片。按[载荷映射](payload_map.json)和现有工具恢复原文件；恢复结果均核对原SHA：

```powershell
python '.\tools\v2_payloads.py' --version '.\experiments\2026-10-15' --destination '.\restored-evalset-20261015'
```

恢复目标需为空。独立评分所需的48文件核心集都可直接使用；大阶段结果、token审核等审计载荷需上述恢复。原执行脚本的GPU、模型、旧索引和桌面项目依赖仍需相应本地环境，不能把恢复文件等同已安装运行依赖。

[发布范围与排除清单](publication_scope.json)列出6个未上传本地载荷：4个向量/缓存文件、1个首次失败token镜像、1个未使用续跑副本。凭据、模型权重、虚拟环境、教材原文和360预留正文均不上传。原delivery_manifest是本地完整记录，包含这些本地排除项；公共publication_manifest与payload_map才是本次上传全集，不冒充完整本地运行环境。

原封存记录保留生成时的github_pushed=false，不追改历史。本次公开发布状态由publication_scope、publication_manifest及仓库提交记录说明。旧知识库、旧实验、融合权重、应用默认和真实人工批准范围保持原样。
