# E04 工具实现与验证

实现只在本实验目录，冻结 runner/adapter、知识库、应用源码和旧 outputs 均未修改。没有运行 GPU 实验、付费 API 或读取 360 份预留正文。

## 接口

在工作区根运行开发集：

```powershell
& 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_retrieval_20261012/.venv/Scripts/python.exe' -X utf8 -B 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_e04_pilot_20261012/experiment.py' --mode dev --queries 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E04小批量实验_20261012/dev_queries.jsonl' --output 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E04小批量实验_20261012/dev_results.jsonl' --arms A0 A1 A2 A3
```

确认集先由主任务完成选择，选择文件需包含 `confirmation_arms` 及 `chosen_arm` 或 `selected_arm`。两名称都存在时必须相同；选择非 A0 时确认两配置为 `[A0,选择配置]`；选择 A0 时固定 `[A0,A3]` 探索对照。读取选择文件只提取配置和 SHA：

```powershell
$selectionPath = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E04小批量实验_20261012/selection.json'
$selectionSha = (Get-FileHash -LiteralPath $selectionPath -Algorithm SHA256).Hash.ToLowerInvariant()
$confirmationArms = (Get-Content -LiteralPath $selectionPath -Raw | ConvertFrom-Json).confirmation_arms
& 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_retrieval_20261012/.venv/Scripts/python.exe' -X utf8 -B 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_e04_pilot_20261012/experiment.py' --mode confirmation --queries 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E04小批量实验_20261012/confirmation_queries.jsonl' --output 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E04小批量实验_20261012/confirmation_results.jsonl' --arms $confirmationArms --selection $selectionPath --selection-sha256 $selectionSha
```

结果文件及 `.partial`、`.run.json`、`.failure.json`、`.token_audit.jsonl`、`.score_pool.jsonl` 任一已存在均拒绝覆盖。失败保留部分结果和明确失败记录；不要把旧部分文件移除后假称同一运行成功，应换新输出路径。

## 输入、模型与阶段

- 四配置固定 A0=1:1/100，A1=2:1/100，A2=1:1/200，A3=2:1/200；RRF k60、每路 Top100。路内重复不加分、不占后续名次；排名从1开始、分数降序和 unit_id 稳定排序；不混合两路原始分数。
- 固定真实来源：runner SHA `7a05001beb6e611e47743ec420f70763f61fd106932b02d54f73e24d772da4cb`；adapter SHA `c846cac66071c7f83028d99fb5968332655d51bb550abe4047cf0505c5ad44d4`；prepared manifest、旧结果、旧运行记录均固定完整 SHA。
- 开发运行首先核精确旧查询、旧模型参数、源文件与 prepared 单位绑定、BM25/分词器/投影代码、旧阶段一致性及 A0 完整结果。9639 份源只从 manifest 明确列出的 `finrisk-knowledge-base/data/sources/part-*.jsonl` 读取并核 hash，未遍历其他数据目录。
- manifest 历史 `normalization_sha256=814006...` 与当前规范化工具 `650f294...` 不同。只读检索不执行规范化工具，保留历史 SHA，不把未调用工具的现行版本当检索运行依赖；投影、adapter、backend、分词器、索引和源绑定仍严格核对。
- 模型使用原 `LocalModels`，CUDA、float16、batch16、max_length512，模型目录和 tokenizer 文件指纹、Torch/Transformers/NumPy、指令均要求与旧记录相同；实际读写缓存目录为新建 `work/finrisk_e04_pilot_20261012/vector_cache`。模型只使用 `local_files_only=True`。
- 旧 `work/finrisk_retrieval_20261012/vector_cache` 仅只读：确认运行从冻结旧日志明确的 structured/document key `5439ca546467f0674ef4a3de046941defb3c2268072fdf4927d583702ae76c07` 选择对应 `.json/.npy` 两文件，校验 metadata.key、模型/分词器/参数绑定、当前单位文本顺序 SHA、npy 内容 SHA、形状/float32及 token audit 后复制到新目录，再逐文件核 SHA。没有复制其他缓存；新目录相同文件可复用，不同内容拒绝覆盖。所有 query/cache miss 只由原 `encode` 写新 E04 目录。dev只 rerank，不复制文档缓存。记录保存在运行日志 `document_cache_seed`。
- 每条开发题复用旧真实 Top100 rerank logit，分数绑定查询、原始 indexed text、源 SHA、manifest 和模型运行参数。真实两路并集的缺分候选一次调用原 reranker，不因融合次序变化重算已有 logit。所有配置共用该查询分数池。
- 确认模式真实建立原 BM25 内存索引、原 BGE 查询/文档编码，获得两路各 Top100；真实并集只做一次 rerank。分数池最大200，实际数量不足200时按实际并集；A2/A3相同候选可产生相同最终结果，共享池不能解释为独立重复。
- 各行保存 `bm25/dense/rrf_union/rrf_top100/rerank_candidates/rerank`、files/cases、配置、来历和共享耗时。V2 aggregate 直接来自冻结 adapter，完整上下文与原 indexed text 分别保留，Top20 文书/案例聚合没有新增裁剪。
- `.score_pool.jsonl` 每单位写真实分数、来源和输入绑定；旧分数标 `frozen_same_input_rerank`，差集分数标 `actual_local_gpu_rerank`。`.token_audit.jsonl` 和模型日志保留新评分的截断/缓存信息；旧评分的截断来历由固定旧运行记录指纹关联。
- `shared_pool_rerank_seconds` 是真实本地 GPU rerank 调用的墙钟耗时，包含分词、传输和结果回传；每配置标明 `gpu_seconds_shared_by_arms=True`，不能将它按配置累加成独立 GPU 调用。准备、加载、评分和每条查询均输出进度。

## 实际验证

- TDD 初始18项均因工具尚不存在失败：`tests_red.log`。
- 选择字段与历史未调用工具的两项预期失败：`tests_red_dependencies.log`；预检失败日志回归先失败：`tests_red_preflight.log`。
- 当前23项通过：`tests_green.log`。包含加权/重复/缺失路/参数非法/深度差集、过时查询与源绑定、V2完整聚合、缺分拒绝、确认选择SHA锁定、输出拒覆盖、预检失败记录及四配置整体合成流程。GPU接口合成替身只用于无法在逻辑测试中加载模型的编排验证，临时结果均已删除。
- 在指定 GPU Python 环境复跑同23项也全部通过：`tests_gpu_runtime.log`，0.388秒；依然未加载模型/启动GPU评分。
- 缓存边界修复补4项TDD测试：先在 `tests_red_cache.log` 观察4项预期失败，再在 `tests_green_cache.log` 最终复跑27项全部通过（15.642秒）。合成回归直接调用冻结 `LocalModels.encode`、使用小型CPU合成张量，验证复制文档仍hit、新query miss只写新目录、旧缓存全部文件指纹不变、无关缓存不复制、不同现有文件及过时metadata/token audit/shape拒绝。未加载真实模型、未做GPU评分。
- 标准 Python 缓存回归 `tests_standard_cache.log`：27项中26通过、1项因该环境没有Torch而跳过；需要Torch的原encode CPU合成回归已在指定GPU Python环境实际通过。
- 真实只读核验：`tests_provenance.log`，核9639源、65475索引单位，12/12开发题 A0 files/cases及旧5个stage逐字段精确复现（含Top5完整上下文）；83.53秒，`gpu_model_loaded=false`。
- 没有执行整轮 GPU 开发/确认实验。主任务统一调度真实评分，避免GPU并发冲突。

缓存修复版指纹：`experiment.py=dc2269e588af38966be1e2675fb7c86f1caab60f0e11e88e535574cd3a07c46e`；`test_experiment.py=816cb054ba23c552b2f46345eee2e7da85377b47dea1a82f66f43dc9a6d617c9`。

复跑逻辑测试：

```powershell
& 'C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -B 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_e04_pilot_20261012/test_experiment.py'
```
