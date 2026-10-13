# FinRisk 1:1离线演示V3

本轮完成16条文字的真实检索、原文证据返回和当前会话判别。用户指定的1:1融合为当前采用参数，2:1历史实验继续保留。

先看[三类典型展示](三类典型展示.md)，再看[演示报告](演示报告.md)、[全部16条实际输入输出](全部输入输出.md)和[当前采用方案/流程图](当前采用方案.md)。

## 实际落地

- 全9639份文书/65475单元；BM25/BGE各Top100，等权RRF k60，rerank100，文书Top5。
- 21个此前模型审核单元具备范围返回；本轮3处曝光，其他单元原样。显示修正不改排序或实际模型文本。
- 16条会话判断：6风险表述、6本段未见明显风险、4信息不足；80位置中53个被模型认为有判断帮助，14输入至少一段有用。D002/D013仍无有用Top5。
- 12项必要测试及[最终整体核验](verification_final.json)、[判断引用核验](judgment_verification.json)通过。全部输入、源区间、实际阶段、模型/token运行记录和判断均保存。

这些是同会话构造并判断的演示结果，非独立人工金标/准确率。多文书同事件、跨产品类比及历史规则限制逐条披露。本轮没有同输入的旧显示判别对照，不宣称检索效果提升。

CLI自动执行到检索和证据包；最后风险判别由当前会话逐段阅读完成。现有应用/在线自动判别API尚未接入。官方27类来自原字典，候选标签不改源事实。

## 保存了哪些文件

queries.jsonl、adoption.json、input_freeze.json是本轮固定输入和采用记录；retrieval_results.jsonl及其.run/.token_audit侧车是真实后台结果；display_results.jsonl和evidence_packets.jsonl是实际显示及证据包；model_judgments.jsonl是最终会话判断。reading_record说明判读范围与同作者偏差。

model_judgments_initial.jsonl只保留一处引用换行修正前的历史稿，不是最终可用判断；quote_correction.json记录仅该引文修正，其他语义字段没变。judgment_verification及verification均针对最终model_judgments。

verification.json是入口补齐校验前针对实际16条数据的核验；verification_final.json是最终版本。独立复核发现prepare原先没有核对父结果SHA与完整参数，已修复并新增拒绝测试。demo_initial.py和input_freeze_initial.json保留本次真实运行的初始代码/67依赖绑定，code_repair记录入口版本修订；其余66项原依赖未变，最终71项依赖核对一致。未改实际运行/证据/语义判断，未重复GPU。

工具在work/finrisk_demo_v3_20261013；最终SHA清单为delivery_manifest.json，权重/源/审核依赖见input_freeze。模型权重、向量缓存、原库等外部依赖未复制进交付；需在本机既有环境复跑。

## 复跑新输入

默认本轮输出已保存，入口拒绝覆盖。新输入和结果使用新批次目录，不要改本轮冻结queries或往冻结交付目录追加结果。PowerShell示例（批次002目录/缓存须尚不存在，输入文件先保存为UTF-8 JSONL）：

```powershell
$demoRoot = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai'
$demoWork = Join-Path $demoRoot 'work/finrisk_demo_v3_20261013'
$demoPython = 'C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$demoNewRun = Join-Path $demoRoot 'outputs/FinRisk_演示新输入_批次002'
$demoQueries = Join-Path $demoNewRun 'queries.jsonl'
$demoResults = Join-Path $demoNewRun 'retrieval_results.jsonl'
$demoCache = Join-Path $demoWork 'vector_cache_new002'
& $demoPython -X utf8 -B (Join-Path $demoWork 'demo.py') retrieve `
  --queries $demoQueries --output $demoResults --cache $demoCache
& $demoPython -X utf8 -B (Join-Path $demoWork 'demo.py') prepare `
  --queries $demoQueries --results $demoResults --packet-dir $demoNewRun
```

输入每行仅需唯一query_id与非空text，例如：

```json
{"query_id":"NEW001","text":"销售人员承诺投保后返还合同外现金。"}
```

retrieve会实际调用既有本机CUDA模型，只复制经SHA核对的文档向量；旧缓存只读，新查询与rerank实际执行。prepare输出新证据包，按[判别规范](判别规范.md)让当前会话阅读并写新model_judgments.jsonl，然后检查：

```powershell
& $demoPython -X utf8 -B (Join-Path $demoWork 'demo.py') verify-judgments `
  --packets (Join-Path $demoNewRun 'evidence_packets.jsonl') `
  --judgments (Join-Path $demoNewRun 'model_judgments.jsonl') `
  --output (Join-Path $demoNewRun 'judgment_verification.json')
```

该命令不自动给风险标签，也不填补缺失判断。新包SHA由JSON规范化计算，字典字段、source span和实际显示引文须一致；不同包不能继承本轮判断。新批次任意输入不受本轮16条限制，但不能将新批次套用本轮已通过的verification。

## 只读核对本轮交付

```powershell
& $demoPython -X utf8 -B (Join-Path $demoWork 'package_delivery.py') --check
```

这是最终文件字节核对。verify_demo.py、build_judgments.py和render_demo.py是本轮构建/核验入口，拒绝覆盖已有产物，不要重复执行去改本轮版本。demo_initial.py是历史代码，不是当前入口。旧五小时实验封包核对通过，新版记录另存；不改旧实验报告的采用建议历史。
