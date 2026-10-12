# 独立检索实验审核

审核范围：`runner.py`、`test_runner.py`，桌面 BM25 `src/retrieval/sparse.py` 与 `tokenization.py` 只读核对，本地 BGE 模型卡与配置核对。不读取 `.env`、360 盲验或比赛题答案；不修改 runner 实现。

## 1. 规格符合审核

最终复核结论：检索计算主链符合规格，初审发现的证据定位、截断审计和版本指纹问题已在当前代码修复；必须使用修订后代码重新 prepare。尚未在本审核环境完成真实 BGE 推理（隔离环境当时没有 numpy；真实模型运行由主任务验证），不能把代码核对当作模型执行成功。

已核对：实际导入桌面 `SparseRetrievalIndex.search`，没有调用桌面 TF-IDF `vector_search`；本地模型固定 snapshot、`local_files_only=True`，dense 使用末层 CLS + float32 L2 归一化，query 使用模型卡的中文 instruction，passage 不加 instruction；reranker 使用成对 query/document 输入的单 logit。两路各 Top100，等权 RRF `1/(60+rank)` 且 rank 从 1 开始，融合后 Top100 再 rerank。structured 默认四组、raw 默认两组；两 corpus 均来自同一 source manifest 的 full_text。case 和 file 采用 max，file Top20；SOURCE 保底块只进入 file，不伪造真实 case。summary、risk_tag、非引文值没有进入投影；未知角色保留“责任层次未知”；source_text 为原文精确子串，不精确引文记入审计。

- **P1：重复引文被伪装成唯一主体位置。** 初审 `project_document` 固定选 `positions[0]`。真实 F000330 最新 fix02 中 bank1_b1、bank2_b1、bank3_b1 的主体分别为尚朴路、凤城五路东段、梨园路支行，但三者 finding unit 的 `source_spans` 全为 134..159（首家主体的违法行为）；原文实际重复位置包括 262..287、386..411 等。仅保留 parent 的所有位置不能补救最终单一 span 的错误归属。实现任务已收到问题；可接受修法为保留所有精确候选位置并明确 ambiguity，不能猜最近主体并宣称确定归属；最终 files/cases 也必须传递 ambiguity。
- **P1：缓存命中缺少逐单元实际截断审计。** 初审 encode hit 只追加 token_summary，新的 token_audit sidecar 不重放 per-unit 输入/使用 token 数，cache meta 也没有可重放明细。需要保存和重放实际 token_audit；旧缺明细缓存不得冒充完整审计。
- **P1：并发改 runner 后 prepare 的版本指纹可能失真。** prepare 在结束时读取磁盘 `runner_sha256`，而执行函数是启动时载入的旧代码；本轮 fullprepare 与实现修订重叠，可能输出旧 span 投影却标注新 runner hash。本轮修后必须重 prepare；建议启动时固定 hash，并在完成前检查代码未变。

修复复核：重复引文现在保存全部精确 `source_spans`，并明确 `evidence_ambiguous`、`ambiguity_reason` 与 prefix 的歧义；`evidence_row` 将歧义传入 files/cases。再次重放真实 F000330 的 bank2_b1，12 个候选 span 全部逐字匹配，unit/file/case 均标记 ambiguous，不再声称唯一定点归属。缓存版本 2 保存逐条 token_audit，命中时检查数量、id 顺序与 token 数后重放；直接调用实际 `LocalModels.encode` 的命中分支（只替换向量读取，不做真实推理）验证输入 700 / 使用 512 的逐 unit 日志正确写出。启动时固定 RUNNER_SHA256，prepare/run 完成前检查磁盘代码未变；并发修改会失败而不能写 complete。

## 2. 代码质量审核

最终复核结论：主排序、去重、max 聚合、缓存文本顺序绑定没有发现会改变默认六组算法定义的错误。缓存键绑定有序 unit_id/text、模型文件完整指纹、tokenizer class、max_length、query instruction、pooling、normalization、框架版本、precision、query/document 类型与 token audit schema 版本；npy 使用 allow_pickle=False 且验证文件 hash 和行数。

- **已修复：同输出重跑会先覆盖已完成 token_audit 再拒绝结果覆盖。** 输出存在检查现已移至 run 首部，回归测试确认模型未被初始化，原 audit 内容保持不变。
- 最终测试复跑：工作区 TEMP/TMP 下执行 `.venv/Scripts/python.exe -m unittest discover -s work/finrisk_retrieval_20261012 -p test_runner.py -v`，**15 项通过**，退出码 0；包括重复位置歧义、逐 unit 缓存审计重放/顺序校验、输出审计保护、代码 hash 变化拒绝。现有测试和分支重放不代表真实 BGE、reranker、8509 全量和冷/热缓存已经执行成功。
- 当前无未解决的默认算法/缓存串错/唯一位置误归属关键代码问题。余下验收条件：修后重 prepare、8509 来源完整检查、真实本地模型六组运行及完整阶段日志。没有提出无关重构或删除死代码。
