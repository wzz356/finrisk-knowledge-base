# E04离线盲评工具

本模块只准备评分材料、核验现有模型判断和统计结果；不调用API/GPU，不生成语义分数。评分是模型意见，不代表人工验收。开发集配置选择由协调者按冻结规则执行，本模块不修改选择规则、不根据确认成绩重新选配置。

## 实际入口

使用指定的标准Python，参数中的路径可为相对当前工作区的路径；包含空格或中文时保持引号。

```powershell
& 'C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -B './work/finrisk_e04_pilot_20261012/evaluate.py' prepare --queries './outputs/FinRisk_E04小批量实验_20261012/dev_queries.jsonl' --results '<真实实验结果JSONL>' --output-dir './outputs/FinRisk_E04小批量实验_20261012/dev_evaluation' --reuse-pool './outputs/FinRisk_知识库V2_20261012/evaluation/all_pool/blind_judgment_pool.jsonl' --reuse-judgments './outputs/FinRisk_知识库V2_20261012/metrics/validated_judgments.jsonl'

& 'C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -B './work/finrisk_e04_pilot_20261012/evaluate.py' summarize --queries './outputs/FinRisk_E04小批量实验_20261012/dev_queries.jsonl' --results '<同一真实实验结果JSONL>' --output-dir './outputs/FinRisk_E04小批量实验_20261012/dev_evaluation' --judgments '<实际模型判断JSONL>'
```

`--results`支持多个结果文件，行内必须有`arm=A0|A1|A2|A3`，以及`query_id/text/files`。每个出现的arm须覆盖当前全部query，不能省略整道题；真正无命中时保留`files=[]`。hit格式沿用原`run_v2.evidence_row`，须有连续`rank`、`file_id/unit_id`、`text/source_text/source_spans`及真实`source_segments`。每个query-file合并所有arm的Top5实际上下文，文书聚合及上下文不由评估器重新构造。

`--reuse-pool`和`--reuse-judgments`须同时提供。一个公共pool可对应多个判断文件；多个pool与多个判断文件按顺序配对。旧真实完整池路径已通过文件检索确认，未猜测路径。确认阶段可引用既有新阶段pool及validated判断，以相同精确绑定原则复用。

`--sources`为可选显式只读源参数；生产默认固定为`outputs/FinRisk_知识库V2_20261012/normalized_final/data/documents.jsonl`。源ID取`official_file_id`，同时核验`full_text`与`text_sha256/source_sha256`。测试使用单独的合成源文件，不读取预留360正文、环境秘密或测试答案。

Python接口：

```text
prepare(queries_path, results_paths, output_dir,
        reuse_pool=None, reuse_judgment_paths=None, *, sources_path=SOURCES) -> manifest
summarize(queries_path, results_paths, output_dir,
          judgment_paths=(), *, sources_path=SOURCES) -> metrics_or_incomplete
build_pool(queries_by_id, result_rows, sources_by_file_id) -> (pool_by_pair_id, provenance_rows)
reuse_judgments(pool_by_pair_id, old_pool_rows, old_judgment_rows, origin='') -> (cached_by_pair_id, log)
merge_judgments(pool_by_pair_id, cached_by_pair_id, submitted_rows) -> (validated_by_pair_id, remaining_rows, disagreement_rows)
compute_metrics(queries_by_id, result_rows, pool_by_pair_id, validated_by_pair_id) -> (metrics, per_query_rows)
```

## 评分与复用

文件评分字段沿用旧校验器：`pair_id/help_grade/help_type/mechanism_match/conditions_match/source_quote/reason/limitations/misleading_risk`，`contexts`逐项含`context_id/help_grade/evidence_quote/reason/misleading_risk`。分数为整数0–3；类型枚举保留原约束；风险为布尔值；limitations为字符串数组。任何非空引用必须逐字存在于对应文本，>=2分必须提供非空逐字原话。片段引用须同时连续出现在当前片段和完整源中，跨分段拼接或改写会被拒绝。

复用按单条`query_id`、完整query文本、源全文/SHA和完整context文本匹配；不要求开发12题文件与旧50题文件的整体SHA相同。相同文件不同query、同ID不同文本、源漂移和新片段均不得继承旧片段判断。所有区间还要切片验证，不仅比较hash。只有全文一致时可以单独复用文件意见；已复用全文但有新增contexts时，盲任务只要求补片段，`needs_file_judgment=false`，不会向评分者泄漏旧grade。

同一pair允许多个输入文件补充不同contexts；重复意见必须完全一致。旧文件评分与已评分片段不得被后续意见静默覆盖。全文<2而片段>=2的分歧单列，保留原全文意见。

## 输出与恢复保护

生产API/CLI只允许`outputs/FinRisk_E04小批量实验_20261012`下真正的阶段子目录；禁止直接写该根或任何旧V2目录。目录及固定输出名均解析真实路径，跨阶段链接、与显式输入相同的解析路径/硬链接、具有多个硬链接的输出文件均拒绝。无manifest却已有同名产物的目录也拒绝写入。

同一输出阶段仅在query/result/source/tool及复用输入SHA、池和缓存产物SHA完全一致时恢复。跨阶段或改变结果需新建阶段子目录，再用`--reuse-*`显式引用旧阶段。同阶段输入漂移会在写入前拒绝，已完成的评分和指标不会被异源覆盖。`validated_judgments.jsonl`恢复时还与上一轮保存的SHA核对。再次prepare从自身已验证判断恢复，重新生成待办；需再次summarize才有完整指标。

生成的配套产物：

- `blind_judgment_pool.jsonl`：每pair完整原文及全部实际contexts；不含算法、排名、方法、已知正例、题目anchor或缓存grade。
- `remaining_pool.jsonl`：仅剩全文/片段任务，仍包含完整源及具体上下文。
- `cached_judgments.jsonl`、`validated_judgments.jsonl`：源绑定的复用/校验判断，可包含尚待补片段的部分记录；完整性由待办和指标status明确标记。
- `judgment_provenance.jsonl`：真实arm/rank/unit_id、源SHA、实际完整hit与返回区间，用于回查，不是盲评分包。
- `reuse_provenance.json`、`judgment_pool_manifest.json`：复用来源、接受/拒绝原因、精确绑定和输入/产物SHA。
- `metrics.json`、`metrics.md`、`per_query_metrics.jsonl`：完整时的配置、分组、逐题帮助度与误导指标。
- `file_context_disagreements.jsonl`：低全文/高片段分歧及原意见，不改分。

缺任一实际Top5全文或context评分时，`summarize`仍保存已核验意见及完整待办，但`metrics=[]/status=incomplete`，不生成逐题完整成绩，CLI退出码为2。prepare有待办为`awaiting_judgments`；无待办为`ready_for_metrics`。只有所有实际评分齐全并核验后，summarize才输出`complete`和退出码0。

每个arm分母固定为题数×5；缺席位置按无支持计算，缺评分拒绝完整指标。主指标`context_useful_at5`为片段>=2率，另有片段覆盖、全文有用率/覆盖、全文和片段均分、全文和片段误导率，以及group与逐题详情。`support_coverage_at5`为兼容旧接口的全文有用覆盖名，包含有用的边界对照。已知来源@5/@10/@20仅对实际有`known_positive_file_ids`的题计算，其他题为null且不进入其分母，不称真实召回率或全局金标。

## 实际验证

- TDD初始：20测试全部因评估模块尚未实现失败，见`eval_tests_red.log`。
- 防恢复漂移回归：新增4项先失败，再修复，见`eval_tests_regression_red.log`。
- 防覆盖回归：实际别名覆盖、无绑定同名artifact和阶段输入漂移先失败，再修复，见`eval_tests_isolation_red.log`。
- 最终标准Python：28项中27通过，1项实际硬链接建链测试因Windows沙箱WinError5无法创建链接而跳过；没有将跳过项报告为通过。`resolve/samefile/st_nlink`拒绝逻辑已实现。见`eval_tests_green.log`。
- 真实旧数据只读兼容核验：9639允许源；开发12题A0的60个pair、60个context均精确复用旧评分，0拒绝；未写旧数据、未调用GPU或生成判断。见`eval_legacy_compatibility.log`。
