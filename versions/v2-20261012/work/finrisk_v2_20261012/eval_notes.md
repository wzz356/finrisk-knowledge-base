# V2 独立实验评价工具

仅新增 `eval_v2.py`、`test_eval_v2.py` 和本文件。未修改 runner、run_v2、projection、normalize 或冻结 V1 评价源。工具不判断帮助度，不调用模型/API，不按关键词、相似度或标签自动给分；语义判断只来自读原文的模型辅助评审，human_judgments=0。

## 接口

PowerShell 中使用已批准 Python 运行 `work/finrisk_v2_20261012/eval_v2.py`：

```powershell
& 'C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' 'work/finrisk_v2_20261012/eval_v2.py' build-pool --results 'v1=outputs/FinRisk_召回实验_20261012/retrieval_results.jsonl' 'v2_same8509=实际V2结果文件路径' 'v2_all9639=实际V2结果文件路径' --queries 'outputs/FinRisk_召回实验_20261012/queries.jsonl' --repo 'finrisk-knowledge-base' --cache-pool 'outputs/FinRisk_召回实验_20261012/评估标注/blind_judgment_pool.jsonl' --cache-judgments 'outputs/FinRisk_召回实验_20261012/指标/validated_judgments.jsonl' --cache-queries 'outputs/FinRisk_召回实验_20261012/queries.jsonl' --output '实际V2评估标注目录'
```

`--results` 为任意明确命名的 `variant=path` 列表；不得将示例中的占位路径当成实际文件。每个 variant/corpus/arm 必须完整覆盖冻结 50 查询。V1 可有 300 行6组，两个 V2 可各有 200 行4组；代码不硬编码具体组名。全部 rank 连续、查询文本一致、返回文件不重复。只加载显式 repo/data/sources 分片，不加载候选集、不依赖旧 TASKS8509；记录实际源数量。

build-pool 输出 blind_judgment_pool.jsonl、独立 judgment_provenance.jsonl、cached_judgments.jsonl、judgment_pool_manifest.json 和 judgment_part_1..3.jsonl。pair_id=`J+SHA256(query_id:file_id)[:12]`，context_id=`C+SHA256(exact_text)[:12]`。判池和待判分片不暴露 variant、corpus、arm、rank、score 或已知来源；待判保留完整原文、查询与尚缺判断的 contexts，needs_file_judgment 标明文件评分是否需要新判。已缓存分数只存在 cached_judgments，不进入待判分片。评审只读取指定待判分片和原有 judging_instructions.md，不读取缓存、provenance 或 results。

V2 每个 source_segment 与自己的全文 span 完全相等，source_spans 逐项对应；source_text 为无标记拼接，text 为 `\n\n[原文间隔，分段摘录]\n\n` 分隔。V1 保留 prefix + 换行 + source_text 和每个 span 等于整个 source_text 的规则。context ID 可以跨方法复用，原文间隔标记不能充当引文，也不能将不连续片段拼接后的字符串当成连续原文证据。

缓存必须同时提供旧判池、已验证 judgments 和旧冻结 queries。只有 query 文件字节 SHA 完全相同、query_text 完全相同、全文 SHA 完全相同时复用文件评分；context 另须 exact text 相同。缓存本身先做完整 ID、rubric、原文引用校验。改变 query 文件字节即关闭全部复用；源 SHA 变化则该文件需重判。新 context 仍需重判，即使文件评分已缓存。

```powershell
& 'C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' 'work/finrisk_v2_20261012/eval_v2.py' merge --review '实际V2评估标注目录' --judgments '新判断1.jsonl' '新判断2.jsonl' '新判断3.jsonl' --output '实际V2指标目录'
& 'C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' 'work/finrisk_v2_20261012/eval_v2.py' metrics --review '实际V2评估标注目录' --judgments '实际V2指标目录/validated_judgments.jsonl' --output '实际V2指标目录'
```

needs_file_judgment=false 时评审只需 pair_id 和 contexts。新文件必须完整 rubric。合并拒绝缺失、重复、未知 pair/context、覆盖不足、缓存评分被覆盖、类型错误，以及 grade>=2 没有非空精确连续原文引用。context 引文必须同时连续出现于可见 text 和完整原文。0/1 分仍按原 rubric 可留空引文；任何非空引文均必须来自原文。

metrics 输出 validated_judgments.jsonl、per_query_metrics.jsonl、metrics.json；merge 额外输出 judgment_merge_manifest.json。所有原始输入、原文分片、rubric、工具自身、判池产物及新判断输入 SHA 均记录并复查。原始输入或 provenance 更改拒绝运行。metrics 校验结果的每个 Top5 query/file/context/unit/rank 与 provenance 一一相符。

主指标含全文和实际 context 的 help>=2 比例/覆盖、help=3 强覆盖、平均帮助度、误导率，以及 union Top5 判池 conditional nDCG；context ideal 取每个 query/file 的最佳已判 context，避免重复上下文膨胀 ideal。无有用判池 ideal 时 nDCG=null，并记录有效 n。已知来源 Hit5/10/20 和 RR20 仅对有已知来源的查询汇总。所有 Top5 分母固定5，缺位补0。不能据这些指标宣称全语料 Recall；这里只覆盖检索得到的联合判池。

## 实际验证

- 测试先行：新增实现前9项测试因实现缺失失败；实现后9项通过。后续新增全输入 SHA 继承测试先失败，修复后全部13项通过。
- 13项 fixtures 覆盖多段原文与标记、V1片段规则、任意 variant/group、50查询/排名/重复完整性、缓存文件与exact context、query SHA变化、source SHA变化、待判仅新contexts、最简新增context judgments、缺/重复/伪造ID及引用拒绝、provenance篡改、无正 ideal 的 null/n、稀疏Top5。
- 真实冻结V1只读兼容实跑：显式来源9639，300结果6组，671 query/file pairs、945 contexts全部复用，pending=0；缓存合并完整覆盖，生成300逐查询指标。已有公共聚合指标和原 pool_ndcg_at5 的84个值与冻结V1结果逐项相等。
- 真实兼容检查产物只存在工作目录内自动清理的临时夹；没有改动冻结交付。真实V2结果未生成前未声称V2实验完成。

测试命令：

```powershell
& 'C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m unittest discover -s 'work/finrisk_v2_20261012' -p 'test_eval_v2.py' -v
```
