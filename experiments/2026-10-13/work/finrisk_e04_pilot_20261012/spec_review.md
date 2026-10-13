# E04 独立规格审查

审查日期：2026-10-12。最终候选结论：**PASS**，两项初审 P1 已修复并复核，最终 SHA 和实际测试见末节。没有修改实现或冻结基线，没有调用 GPU，没有查看 confirmation_queries.jsonl 的查询内容或运行确认实验。

## 初审发现（最终均已关闭）

1. **P1：评分输出可覆盖旧池或旧评分。** 初审 `evaluate.py:429–474` 的 `prepare` 不限制目标目录，直接覆盖 `blind_judgment_pool.jsonl`、`cached_judgments.jsonl`、清单等；`evaluate.py:493–540` 的 `summarize` 同样直接覆盖 `validated_judgments.jsonl`、指标等。使用仅位于 E04 work 临时目录的合成数据实测：把旧池和旧评分放在 `old_metrics`，再把该目录同时设为 `output_dir` 和 `reuse_pool` 所在目录，调用被接受，旧池 SHA 改变，返回 `awaiting_judgments`。实际旧 V2 数据未被触碰。风险是误传旧 V2 metrics 目录或输入路径别名后，冻结评分/复用证据被改写。最小要求：生产输出限制在本轮新 phase 目录；经 resolve/samefile 拒绝任何目标输出与读取/复用输入别名；同 phase 恢复必须保留一致的输入绑定，跨 phase 用新目录引用旧数据。实现者正在修复，当前变化尚未复验。

2. **P1：确认编码缓存会写入旧实验目录。** `experiment.py:28` 的 `CACHE` 指向 `work/finrisk_retrieval_20261012/vector_cache`，`experiment.py:375` 传给冻结 `LocalModels`，`experiment.py:409` 对新确认查询调用 `encode`。冻结 `runner.py:405–450` 在缓存 miss 时建目录并写 `.npy` 和 `.json`；新确认文本会产生新 key，因此确认阶段会在旧 work 下写派生数据，违背本轮只在新 work/outputs 写入的边界。证据来自静态调用链，未执行编码。最小要求：缓存 miss 只能写 E04 新目录；可把必要的、经原 metadata/SHA 校验的历史文档缓存复制到新目录后复用，或在新目录重建，不修改冻结 runner。

## 已通过的计算与评分规格

- `experiment.py:34–37,83–113,157–175`：四配置 A0 1:1/100、A1 2:1/100、A2 1:1/200、A3 2:1/200；RRF k60 从 1 排名计分，忽略原始路分数，路内重复只计一次，分数降序/unit_id 升序稳定排序。每路限 Top100，候选限真实并集。
- `experiment.py:301–370,381–398,479–521`：开发只复用精确 ID/文本绑定的旧两路及旧 Top100 logits；校验 runner/adapter、投影、准备 corpus/source、tokenizer/BM25 代码和模型/运行参数；其余候选走原真实 rerank 接口，每题共用一个分数池。A0 的 files、cases 以及 bm25/dense/rrf_union/rrf_top100/rerank 五阶段用 canonical JSON 严格相等检查。原 V2 aggregate 直接调用，返回完整上下文规则未改。单元测试通过；本审查未另跑 9639 来源全量 preflight，主代理另有实现者的真实兼容核验记录。
- `experiment.py:161–169,486–489`：A2/A3 取同一个全并集并使用同一 logits 和稳定重排，最终 files/cases 相同，只有融合阶段分数/顺序存在差别；不能报告为两次独立收益。编排测试验证 A2/A3 files 相同和额外候选仅实际打分一次。
- `experiment.py:242–249`：只执行投影依赖检查，normalize 不在 retrieval 调用链中；保留 manifest 历史 normalize SHA 的准备来历合理，没有篡改冻结 manifest 或 baseline 代码来绕检。历史 normalize 已变化的测试通过。
- `experiment.py:210–225,445–450,539–540`：确认必须给 selection 文件和精确 SHA，arms 必须是 A0+selected；selected=A0 时只能 A0+A3。选择文件运行前/后校验。工具不读确认成绩选择参数。开发选择规则及其 selection.json 生成尚属于后续主代理流程，本文件不声称已完成配置选择。
- `evaluate.py:167–211,240–286` 初审版本：Top5 按 query-file 合并池，algorithm/arm/rank/raw score/unit_id/known positives 留在非盲 provenance；池只保留实际全文/返回文本及必要任务描述。复用精确 qid+query_text+source SHA/全文；上下文另按完整 text 及 context ID 精确匹配，新文本不继承旧片段评分。
- `evaluate.py:226–237,289–333,352–409,520–528` 初审版本及冻结 `eval_v2.py:184–214`：0–3 整数等级，>=2 必须有连续逐字原话；片段原话必须同时在实际片段和原文中。缺全文或片段评分保留 pending/incomplete，不默认 0、不出 complete 指标。全文低分/片段高分保留且单列分歧。每题固定 5 分母，缺返回位置无支持；片段与全文指标分别输出，known source 只是辅助，不声称真实召回率。
- `experiment.py:228–232,434–442,472–559`：已有结果/sidecar 拒绝覆盖；失败保留 failure 日志，结果先写 partial，完整且 SHA 再核对后才 rename 正式输出。该文件单独的开发计算规格通过；整体确认接口仍因上面的旧缓存写入缺口不放行。

## 名单、冻结和只读验证

- 已读 task_plan.md、design.md、两工具与全部测试、被调用的旧评分验证函数和模型缓存接口。没有读取 360 预留正文、确认查询正文、确认结果或确认评分。
- `input_freeze.json` 的 13 个 protected_input_sha256 均与当前字节一致。冻结开发名单共 12：营销 5、其他业务 4、边界 3，含 Q009/Q012；种子 20261012。
- 只对白名单 manifest 元信息/名单做确认核验：confirmation_queries.jsonl、confirmation_source_manifest.json、confirmation_design_notes.md 的实际字节 SHA 均与 confirmation_freeze 一致（未输出查询正文）。source manifest 为 10 个独立来源、6 风险/4 边界，旧 50 题 anchor/known-positive 的去重排除集合共 27，manifest 排除名单与实际旧题来源集合一致；10 个确认来源都在冻结 9639 source manifest 中，ID 交集为 0，按冻结 source_manifest 的原全文 SHA 交集也为 0。此核验无需读取确认查询或其原全文正文；构造与引文检查依赖独立 query worker 的冻结记录。

## 实际测试与 SHA

标准 Python `C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8 -B`：`test_experiment.py` 23/23 通过（0.389s），`test_evaluate.py` 20/20 通过（0.883s）；均为 CPU 合成夹具，无模型/GPU。另有上述临时池覆盖反例，执行后临时目录删除。

初审 SHA（测试运行时）：

|文件|SHA256|
|---|---|
|experiment.py|b427ef92773847d486df77dd8c914f70e253e97e8f24ea7a5148e4996d2ffe11|
|test_experiment.py|9df29319487548a0b4c98f343d0df04a6b6120d8f7e412a9da14e7aa71d085ae|
|evaluate.py|e67a91d085d8ad825392efcf6d7f5b25c3f8ef5cb24f31f1ee0061077c10a45e|
|test_evaluate.py|2d3a2e25a0074b2720eba9058aabf8b3c14cc48ef88b0c4d2514af9500b3f417|

审查中评估实现者发生重要 SHA 变化，后测必须以最终冻结版本为准：最近观察 evaluate.py `49ae3175d3fab85ff05707fe0ee9c841f5feaf9bc89b451af98932c5259fee79`，test_evaluate.py `014726e0554249c4741c980dbe3e1b206189adec1c0dbe86c58a1d55198e8f50`。本结论不把初审 20 测试通过套用到这些变化后的代码。

## 最终候选复核

本节覆盖上文初审 FAIL；以下 SHA 的两模块规格已放行，并已先报告主代理后进入独立质量审查。

|文件|最终候选 SHA256|
|---|---|
|experiment.py|dc2269e588af38966be1e2675fb7c86f1caab60f0e11e88e535574cd3a07c46e|
|test_experiment.py|816cb054ba23c552b2f46345eee2e7da85377b47dea1a82f66f43dc9a6d617c9|
|evaluate.py|4f76a7f0655c0db95f9033aa0b74c11ef467cddf707275a40059da4c525a3e0c|
|test_evaluate.py|4a82ae5bee5ca0834826a6d490b7a8cac5e392b2466530a1dfc4a5e698091c6f|

- P1 评分覆盖已关闭：`evaluate.py:89–136,474–489,568–581` 统一先验证真实 phase 路径在本轮 E04 outputs 下，拒绝输出根本身/旧目录、目标逃逸、所有显式输入的 resolve/samefile 别名及现存多链接文件。没有绑定 manifest 却已有固定同名输出则拒绝；恢复核验原输入、复用输入、准备 artifacts 和 validated 行 SHA。同 phase 输入变化时先拒绝，不改旧 complete 指标/评分；新 phase 正常复用同全文旧分，只补新的独立上下文。实际回归已覆盖旧根、输入路径碰撞、未知输出、同 phase 输入漂移、旧评分 SHA 漂移和新 phase 补上下文。
- P1 旧缓存写入已关闭：`experiment.py:29–30,375–379,403–462,534–537` 把 cache 改为新 E04 work/vector_cache，仅以冻结旧日志的一个 structured/document key 复制该对 `.json/.npy`，检验当前单位顺序/数量、精确模型及 tokenizer binding、key、npy SHA、float32/shape、token audit。复制前核对两个目标无冲突，旧源只以只读方式打开；复制后源/目标 SHA 再核对。后续原 LocalModels 的 query miss 使用新 cache。没有改冻结 runner，也没有复制整个旧缓存。
- 本人再次使用标准 Python `-X utf8 -B` 实跑最终测试：实验 27 项，26 通过、1 因该标准运行时缺 Torch 跳过（0.921s）；评分 28 项，27 通过、1 因 Windows 沙箱 WinError 5 禁止实际建硬链接跳过（5.794s）。零失败。实验实现者另报告使用已有 GPU Python 执行原 encode 的 CPU 合成文档 hit/新 query miss 测试，27 项通过；该记录是实现者补充证据，本人未运行该运行时或 GPU。
- 审查中 test_experiment.py 曾出现中间 SHA `d31e8ecced7ca34cf0cf2f8e2a26128bf43dcb4fefd5479835d4d1b9429ffa5e`，最终以 `816cb054…` 再跑，不把中间测试结论冒充最终版本结果。

后续实际 GPU、配置选择、确认评分和报告产物仍须由主代理按冻结流程完成；本 PASS 只覆盖本轮工具规格与上述实际验证范围。
