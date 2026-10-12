# FinRisk V2 检索适配器独立审查

日期：2026-10-12。最终结论：**adapter spec PASS，quality PASS**。本轮三个重要发现均经 root 修复并由本审查独立复验关闭；当前无重要未决问题。

首轮范围修复审查版本 SHA256：`53b0850a14fa0ea0a7235a509134ec85dd625cb277e6e31c36f66ddf2aeaa267`。

不可分词单元过滤集成追加复审版本 SHA256：`c846cac66071c7f83028d99fb5968332655d51bb550abe4047cf0505c5ad44d4`，本轮已实际读取源码 SHA。

只审 production `run_v2.py`；只写报告，未编辑实现／测试。未读凭据／360 盲验，未调用在线 Agent、模型或网络。先完成规格复审并向 root 明示 PASS，再开展代码质量检查。

## 规格复审

现有 9 tests 首轮均 PASS，但 production 投影到适配器组合反例发现两个重要缺口，因此未直接通过规格：

1. 同一行为的 finding 与独立条件各形成一个 unit，共享 qualifier link 字典；原 `normalize_unit_links` 就地改写第一份链接后，第二份再次按冒号拆 ID，实际触发 `IndexError`。root 新增 production 回归并修复。
2. 首次修复分别复制顶层链接与 associations 后，nested `associations[*].qualifier_source_links` 仍保留旧 ID；实际输出 TOP 为 `FRV2-CASE-F000001-stable`、NESTED 为 `F000001:c1`。root 增加 nested 断言并修复为整个引用图深拷贝、顶层与嵌套统一转换且按对象身份去重。

ID 修复阶段本轮独立重跑 **10 tests，0 failures，OK，退出码 0**。额外构造多 case 共享 finding、独立条件／否定、5 字符分块／1 字符重叠的 production 组合：12 units、12 个顶层／嵌套 link 均通过规范 case/behavior IDs、original IDs、逐位置精确回源与候选 draft 不变断言。原两处缺口已关闭，规格阶段 PASS，随后才开始质量审查。

其他独立断言：`normalized_identity` 对 case/behavior 的结果与 production `normalize_v2` 规范描述一致；overlay 重复 file、过期 candidate SHA、伪造 semantic approved 均拒绝，原稿不变。原有测试覆盖标签迁移不改事实、过期原文绑定、伪造人审批准、file-max/all-case 聚合和实际 context 与短 indexed_text 分离。

## 代码质量发现

**P2（已关闭）：run 入口静默忽略显式 scope，不能保证 8509／9639 对照参数一致。**

`run_gpu` 只校验 `args.expected_files == manifest['source_files']`，不校 `args.scope`。实际执行真实 `run_gpu` 守卫，替换 GPU 执行及文件读取为本地 mock：requested scope 为 `remaining8509`，prepared manifest.scope 为 `all`、source_files 为 9639，expected_files 保持 CLI 默认 9639，结果 `backend_invoked=True`。用户明确指定 8509 时仍可启动全 9639 检索。

root 新增 `validate_run_scope`，在真实 `run_gpu` 入口校请求 scope、prepared scope、两处文件数及 scope 固定的 8509／9639。最终独立重跑 **11 tests，0 failures，OK，退出码 0**。另通过真实入口（仅模型执行、磁盘读取与日志写入 mock）核对两种范围各自的一个有效组合、scope 冲突、prepared count 冲突、expected count 冲突，共 8 个组合：有效组合均启动后端并写入正确 adapter SHA／实际 scope；所有冲突组合均在 GPU 后端执行前拒绝。P2 关闭。

## 冻结检索接口核查

已实际核对 V1 `runner.py` SHA256 等于冻结常量 `7a05001beb6e611e47743ec420f70763f61fd106932b02d54f73e24d772da4cb`。适配器动态复用其生产 run，只替换 aggregate；BM25 使用原 sparse 实现，embedding／reranker 固定为 V1 本地默认模型，RRF 路由与 rerank 逻辑复用冻结后端，模型输入仍为 unit.text。后端保留 corpus／ordered text 哈希、查询／模型／分词／BM25 源码指纹和 token 截断审计，适配器完成日志另登记自身 SHA、投影 SHA、manifest 实际 scope 及 context 返回方式。

这些是代码路径与离线守卫验证，不表示已完成真实 GPU 检索、全量准备或收益验收。

## 不可分词单元过滤集成追加独立复审

追加结论：**filter spec PASS → filter quality PASS**。先向 root 明示本项 spec PASS，随后检查本项质量；原 ID／限定／上下文协议未调整，无新增重要未决问题。

本项背景为首次真实运行遇到冻结 BM25 不能处理正文 `/`。本审查没有重跑 GPU；通过原 production SparseRetrievalIndex 独立复现该输入 ValueError，并核对冻结 tokenizer 为 `chinese_unigram_bigram`，与 BM25 `_build` 的真实调用一致。SHA 实际为 `5c53e4fe5ebb47657bb6e191b56074889b571b6a85941da516a314d657518465`。

实际验证：

- 指定标准 Python 独立运行 **12 tests，0.037 秒，OK，退出码 0**。
- 对 `/`、`（+）`、破折号、emoji、中文、金额、全角拉丁字母数字、〇及混合文本等12种输入，真实冻结分词器判定7个可索引、5个无词元。partition 恰好按词元是否为空分组，全部原对象与元数据保留；可索引组成功构建真实 BM25 并搜索中文；原 slash 异常被复现。数字和金额未误排除。
- 用1份 synthetic fixture 走真实 `prepare_dataset` 每单元处理分支，只 mock 源集合加载与初始总体计数以到达该分支；末尾真实范围完整性检查按预期拒绝小 fixture，未构造伪全量完成 manifest。结构化／raw 两个 slash unit 均完整写入 `non_searchable_units.jsonl`，规范 case／behavior／qualifier IDs、context_segments、source_spans 和源文本 SHA 保留；audit 指向准确 unit IDs；两个索引文件中均无 slash；原 draft、wrapper、full_text 不变。临时目录自动清理。
- 独立核 frozen_tokenizer 源码 SHA 错误会拒绝；prepared tokenizer binding 错误会在真实 `run_gpu` 入口拒绝，GPU 后端未执行。只 mock 校验边界，未改磁盘源码或启动模型。

生产代码质量核对：过滤发生在 unit 已规范化之后，排除文件写入整个原 unit；audit 和关闭文件句柄进入现有准备流程。排除文件 SHA／count 写入 manifest，tokenizer SHA 同时绑定 prepare 与 run。过滤只影响参与检索的 unit，source_manifest 的每文件绑定仍在 unit 循环后保留，8509／9639 的范围校验继续执行；没有修改／删除来源文件或 draft，没有把 unit 排除冒称为来源文件排除。

判定口径应描述为“冻结 BM25 分词器无词元”，不应只按“标点”猜测。该分词器支持中文／拉丁字母／数字，其他脚本纯文本也可能无词元；这些 unit 同样完整留在排除归档。各检索臂共用过滤后正文池，不把这一变化误写成模型或分词器改版。保存的完整来源与上下文仍供回源；本次通过不等于已经验证检索收益。
