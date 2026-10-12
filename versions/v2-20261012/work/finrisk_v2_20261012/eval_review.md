# V2 评价工具独立审查

审查日期：2026-10-12。审查顺序为先规格、规格通过后再代码质量。范围为 `eval_v2.py`、`test_eval_v2.py`、`eval_notes.md`，只读冻结 V1 查询、结果、判池、已验证评价和聚合指标，以及显式 `finrisk-knowledge-base/data/sources`。未读取盲验凭据，未修改实现、旧源或既有评价；验证的临时目录已自动清理。

## 规格审查：PASS

未发现阻断项。

- `variant=path` 明确绑定结果来源；按 variant/corpus/arm 检查每组冻结 50 个查询、查询文本、唯一 query/group、文件去重与连续排名。组名没有写死，可容纳 V1 六组 300 行、每个 V2 scope 四组 200 行。
- 仅从显式 repo 的 `data/sources/*.jsonl` 加载完整原文，逐条核对全文 SHA；联合池仅取各组 Top5。pair/context ID 分别为规定的 query/file 与 exact text SHA 前 12 位。判池和待判分片采用字段白名单，不包含 variant、corpus、arm、rank、score 或已知来源，来源与排名独立存放于 provenance。
- V2 每个 segment/span 与原文逐字切片相等，source_spans 与 segments 逐项绑定；source_text 为无标记拼接，text 为规定间隔标记串接。V1 保留 prefix 与换行及每个 span 对应整个 source_text 的旧规则。
- 缓存先校验完整 ID、rubric 和引用；查询文件字节 SHA、query_text 与全文 SHA 全部一致才复用文件字段，context 另须 exact text 一致。query 字节变化或全文变化均停止相应复用；文件评分复用时，仅缺失的新 contexts 进入待判，缓存分值不暴露给评审。
- merge 严格检查待判 pair/context 覆盖、重复和未知 ID、0..3 整数评分、必要理由、布尔误导字段以及精确连续引用。正分 >=2 需要非空引用；context 引用必须同时连续存在于可见 text 和完整原文。已缓存文件字段不可由新判断覆盖。
- metrics 重新核对 Top5 query/file/context/unit/rank 与 provenance；文件帮助度与实际 context 帮助度分开计算，缺失 Top5 槽补零且分母固定 5。覆盖、强覆盖、均分、误导率与 union-pool conditional nDCG 定义一致；没有正 ideal 时为 null 并记录有效样本数。known-source Hit5/10/20、RR20 只对有已知来源的查询汇总，没有将判池指标宣称为全语料 Recall。
- 原始查询、结果、原文分片、rubric、工具自身、判池产物和新判断输入 SHA 经 manifest 继承并复核到最终 metrics；评价标明模型辅助、human_judgments=0、非人工批准。

## 代码质量审查：PASS

未发现需要修复的实际代码质量问题。验证逻辑集中于共享校验函数，build/cache/merge/metrics 均重新检查各阶段所需绑定；缓存和盲评待判的字段分离清楚，指标入口不会依据相似度或标签自动生成语义评分。没有提出无关重构或优化。

实际独立验证：

1. 使用指定 Python、`-B -m unittest discover -s work/finrisk_v2_20261012 -p test_eval_v2.py -v`：13/13 通过。
2. 在自动清理的工作目录临时夹，独立执行 build_pool → cache-only merge → compute_metrics，复现冻结 V1：来源 9639、结果 300、组 6、query/file pairs 671、contexts 945，缓存文件 671、缓存 contexts 945，pending=0，逐查询指标 300 行。13 个公共指标及旧 pool_ndcg_at5 映射至 pool_conditional_ndcg_at5，共 6×14=84 个聚合值与冻结结果逐项完全相等。
3. 额外针对文件评分已缓存但新增 context 的情形，分别提交更改缓存 help_grade、未知 context_id、help_grade=4：三者均抛出 ValueError，未被接受。

本结论证明评价工具和冻结 V1 的兼容性；没有将尚未生成的真实 V2 结果视为已完成实验，也没有据机械校验断言语义判断正确。

## 附加只读核查

`check_all.py` 的 task_for 使用明确 batch/raw 路径并先核对原始文件字节 SHA；冻结结构校验随后重新解码原始字节，检查解码全文及 raw SHA 与 document 一致，兼容包装器另核对 text SHA 和 task/document 绑定。`rebind_coverage.py` 只追加逐字 finding_quote 的自身行为 coverage 指针，先检查 quote 原文包含及 case 存在，深拷贝且逐值断言 coverage 之外字段保持，保留 candidate/pending。`test_rebind_coverage.py` 2/2 通过，覆盖原对象与其他记录不变、幂等、原文不匹配拒绝以及共享引文各行为自身绑定。此次核查未执行全量机械检查或重新生成 overlays，不代表新增全文语义审核或人工批准。
