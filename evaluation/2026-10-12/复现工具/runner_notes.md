# 最小离线检索实验 runner

独立代码为 `runner.py`，测试为 `test_runner.py`。不写桌面项目、不写正式索引或账本、不读取 `.env`、不付费调用、不提交 Git。默认所有产物都在本实验目录内。

## 输入与投影

- 递归读取 `outputs/FinRisk_剩余全量运行_v2_20261011/authored`，每个 Fxxxxxx 选择数字最大的 `_r0_fixNN.json`；无修订使用 `_r0.json`。同修订存在不同内容时失败。默认要求 8,509 份。
- 原文来自 `outputs/FinRisk_剩余全量准备_20261011/tasks/Fxxxxxx.json` 的 `full_text`。使用文本 UTF-8 SHA256 与候选 JSON 字节 SHA256，写入每个单位和 manifest。
- structured：案例主体仅用 `party_quote`，行为背景仅用 `finding_quote` 的前 100 个原文字符，角色为保守的 `actor_role` 元数据。unknown 保持“责任层次未知”，responsible_person 不扩张为直接责任。任何未在原文找到的引用都不投影，并写审计。
- 行为支持片段读取真实字段 `finding_quote`、`risk_mechanism_quotes`、`material_function_quotes`、`product_quote`，以及 conditions/negations/exceptions/materials/factor_values 的 quote/quotes、匹配 behavior_keys 的 coverage.quote。不投影标签、推测 value、summary 或场景描述。同一行为内同一原文引文去重。
- 每个引文只接受 contiguous exact substring，禁止改标点、跨段拼接后冒充原文。多次出现时保留全部候选 source_spans，标 evidence_ambiguous=true 与 ambiguity_reason，不猜主体对应哪个位置；case_id 仅保留候选中的主体映射。prefix 引文多次出现另标 prefix_evidence_ambiguous。每个候选位置满足 `source_text == full_text[start:end]`。
- structured 另加入原文结构块作为保底，case_id 只能为 `fid:SOURCE`。raw 使用同一批原文结构块，不加前缀。SOURCE 不进入案例列表。
- 原文/长引文按约 300 字符、40 字符重叠切块，在后半块优先句号/换行/分号边界。每块保留原文位置、parent_id、parent_source_text、parent_source_spans；条件、否定和例外的精确引文另保留在 qualifier_quotes。原文父级保留完整文本，因此 JSONL 大于实际用于编码的 `text`。

单位共享字段：unit_id、file_id、case_id、behavior_id、prefix、source_text、text、source_spans、source_sha256、candidate_sha256、corpus；补充 behavior_key、evidence_kind、parent_*。单位 ID 含语料、文书、行为 local_key、引文与分块编号。

## 检索与模型

BM25 只读复用 `C:/Users/11051/Desktop/金融比赛/复赛/FinRisk_复赛改进/src/retrieval/sparse.py` 及 tokenization.py，sys.path 插入该 src。权重统一 1，k1=1.5、b=0.75。日志记录两份实际代码 SHA256。

Dense 使用本地 BAAI/bge-small-zh-v1.5，官方 AutoTokenizer + AutoModel，取 last_hidden_state[:,0]，float32 中做 L2 归一化，点积计算余弦分数。query 唯一增加前缀 `为这个句子生成表示以用于检索相关文章：`；文档不加任务指令。

Rerank 使用本地 BAAI/bge-reranker-base，官方 AutoTokenizer + AutoModelForSequenceClassification，输入 query/passagetext pair，按单个原始 logit 排序，不做 sigmoid/softmax。无替代模型或算法 fallback。

默认 structured 四路 bm25/dense/rrf/rrf_rerank，raw 两路 bm25/rrf_rerank。单路单位 Top100，RRF 等权、k=60、rank 从 1 开始，缺失路贡献 0；合并至多 200 个单位、按 RRF 取 Top100 进入 rerank。没有 query 生成扩展，没有标签或营销相关性 hard filter。

最终单位先按 case_id 取 max 得到案例指标输入；文书按 file_id 取 max。不同被处罚主体保留不同 case_id。SOURCE 可以提高文书排名但不会伪造案例。文件列表包含该文书所有召回案例 ID 与最高分的证据单元；按 Top20 导出，可直接评估 Top5/10/20。

## 命令（PowerShell，工作区根目录）

```powershell
& 'work/finrisk_retrieval_20261012/.venv/Scripts/python.exe' -m unittest discover -s 'work/finrisk_retrieval_20261012' -p 'test_runner.py'

& 'work/finrisk_retrieval_20261012/.venv/Scripts/python.exe' 'work/finrisk_retrieval_20261012/runner.py' --prepare

# 重投影到新目录，保留旧结果以审计
& 'work/finrisk_retrieval_20261012/.venv/Scripts/python.exe' 'work/finrisk_retrieval_20261012/runner.py' --prepare --prepared 'work/finrisk_retrieval_20261012/prepared_v2'

# 不依赖torch先跑structured/raw两个BM25基线
& 'work/finrisk_retrieval_20261012/.venv/Scripts/python.exe' 'work/finrisk_retrieval_20261012/runner.py' --run --prepared 'work/finrisk_retrieval_20261012/prepared_v2' --queries 'work/finrisk_retrieval_20261012/queries.jsonl' --output 'work/finrisk_retrieval_20261012/results_bm25.jsonl' --arms bm25

& 'work/finrisk_retrieval_20261012/.venv/Scripts/python.exe' 'work/finrisk_retrieval_20261012/runner.py' --run --queries 'work/finrisk_retrieval_20261012/queries.jsonl' --output 'work/finrisk_retrieval_20261012/results.jsonl' --device cpu --batch-size 16 --max-length 512
```

queries.jsonl 每行至少含 query_id 与 text，ID 必须唯一。可用 `--corpora structured`、`--arms bm25` 做单路运行；`--arms` 对所选语料统一生效。可指定 `--embedding-model`、`--reranker-model`、`--prepared`、`--cache`、`--project-src`。默认模型路径是已指定官方缓存 snapshot，网络设置强制 offline、local_files_only=True、trust_remote_code=False。

CUDA 需显式 `--device cuda`；不存在 CUDA 时失败。默认 float32；使用 `--precision float16` 只支持 CUDA。max-length 必须 1–512。

## 缓存与审计

向量缓存为 JSON + NPY，allow_pickle=False。key 绑定有序 unit/query ID + 实际编码文本 SHA256、模型 revision、缓存所有文件 SHA256、tokenizer 类与文件、max_length、query 指令、CLS/L2 方式、torch/transformers 实际版本、精度与审计schema版本。加载时验证 NPY SHA256、行数、维度，并校验逐输入 token_audit 数量、ID顺序、token范围和截断标记。query 向量是两个语料共享缓存。

模型编码先统计未截断 input_ids 长度，再记录 attention_mask 实际使用长度。embedding/rerank 的输入数量、被截断数量、最大输入 token 长度与 max_length 写 `.run.json`；每个单位、query 和 rerank pair 的实际 token 长度与 truncated 标记写 `.token_audit.jsonl`。缓存 JSON 保存完整逐输入 token_audit；命中时重放原始长度审计并标 cache_hit 和 cache_key，不重复编码。

`manifest.json` 记录源文件清单、语料 JSONL SHA256、有序文本 SHA256、投影计数、引用审计与耗时。`projection_audit.jsonl` 记录未匹配引文与多位置引文。

结果每行含 corpus、arm、query_id、files[最多20]、cases[最多20]、timing、stages。各阶段单位列表包含 unit_id、score、rank；RRF 保留完整 union 和 Top100。files 每条含 file_id、score、unit_id、text、prefix、source_text、case_ids、behavior_id、source_spans，以及 evidence_ambiguous、ambiguity_reason、prefix_evidence_ambiguous；cases 同样保留歧义标记。

运行日志 `<output>.run.json` 记录完整配置、实际 Python/torch/transformers/numpy 版本、模型/缓存 SHA256、CPU/GPU、精度、线程数、模型加载与编码耗时、截断和缓存事件。结果先写 `.partial`，只有全部预期结果完成才改名为最终输出，日志 status 才为 complete。异常保留 partial，日志写 failed，进程非零退出。拒绝覆盖现有最终输出；该情况下另写 `.failure.json`。

runner SHA256 在进程启动时保存，prepare/run 开始与完成前校验代码未改；如执行期间 runner.py 改变则失败，不能用新代码 SHA 冒充旧投影的来源版本。实验执行期间应冻结 runner.py。

## 已验证范围

2026-10-12：15 项 unittest 通过，py_compile 通过；增加了重复引文全部位置与歧义、token缓存审计重放/顺序校验、已有输出保护、进程内代码版本变化拒绝等测试。此前实跑了 1 份合成原文 prepare + 桌面 BM25 + structured/raw 结果，核对来源、案例列表与 complete 状态。独立环境在该次验证时尚未安装 torch/transformers/numpy，BGE 和 reranker 的实际模型运行由主代理安装环境后执行，不能将逻辑测试当成模型运行通过。
