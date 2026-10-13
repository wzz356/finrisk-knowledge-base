# E02工具与验证说明

仅新增本轮 `experiment.py`、`test_experiment.py` 及验证日志；旧E04、V2、应用和仓库文件不改写。真实GPU由主代理统一执行。

## 检索与返回

- 固定22条E04已用输入回放：ID、文本、group、query_role均与冻结来源一致；不接受anchor或作者预期字段。保留准备器已写的replay_origin说明。
- P0直接复制E04开发/确认结果的A0，重新用冻结aggregate重建并逐字段比较query/text/files/cases/全部stages，含rerank_candidates；旧推理耗时放在old_real_inference_timing，新推理耗时0。
- P1保留全部9639文书/65475单元，仅通过审核的候选单元改变索引文本。每路Top100，RRF1:1/k60取100，真实本地rerank100。先按原unit_map聚合，再按每条获胜unit_id装饰，避免同文书其他单元借用前缀。
- P2完全复制P0阶段、排名、分数，仅对获胜且入选的单元增加相同背景。indexed_text保持旧索引文本。
- 带背景返回为明确的候选摘录标签、逐字前缀及旧context_text。source_text/source_spans/source_segments/indexed_source_text/indexed_source_spans、身份和歧义字段均保留；新增original_unit_text、base_context_text、prefix_claims、prefix_source_unit_id、prefix_profile和approved_model_review标记，不改人工审核状态。

## 审核、绑定与缓存

- Prefix每条1–3个摘录，标签在预定7类内，逐字原文区间、来源SHA、原索引文本SHA、cohort身份一致；前缀严格等于“label：quote”换行连接且≤180字符。
- Review必须逐单元齐全、唯一、status明确，prefix字节SHA和来源SHA一致。拒绝项不参与P1/P2；实际剂量写approved/rejected/changed_units和各结果prefix_dose。
- prefix_quality.json绑定prefixes.jsonl与prefix_review.jsonl完整字节SHA，覆盖仅改span/link_reason但不改quote/prefix_text的漂移；quality与所有本轮输入及代码在启动/结束均核SHA。
- cache只能是本E02 work目录内的子目录，运行开始须为空。真实文档向量只复制冻结原缓存明确识别的json/npy二文件；复用E04 seed函数核模型、ordered_text、npy SHA、shape/float32与旧token audit。旧缓存只读。
- 原65475行必须命中已核seed，禁止整库重编码；相同22条新query真实编码一次，仅审核通过的overlay新文本真实编码并覆盖原向量对应行。日志记录行号、两数组内容SHA、shape/dtype与真实模型cache_events。
- 完整BM25在实际overlay文字上重建。Rerank分数池每query保存P0冻结真实分数、P1新真实分数及输入/代码/模型/来源绑定；P2指向P0分数。
- 真实tokenizer先在truncation=False下量测query、overlay及每批rerank完整文字。超过512立即保存拒绝审计并报错；基向量继承审计也不得有truncated行。原LocalModels仍保存真实模型使用的token audit。
- 输出、partial、run、failure、score_pool、token_audit任一已存在拒绝覆盖。失败保留明确日志，成功必须22×3=66条。共享query/overlay/BM25耗时如实标注，不把P0/P2旧分复用解释为新推理。

## 已执行验证

- tests_runner_red.log：最初20项因工具缺失按预期失败。
- tests_runner_review_red.log：prefix_review_status缺失按预期失败后修复。
- tests_runner_quality_red.log：完整审核文件绑定缺失按预期失败后修复。
- tests_runner_green.log：最终23项全部通过，使用既有CUDA Python环境，但没有加载模型/调用GPU。
- tests_runner_integration.log：22项阶段的完整编排通过。模型替身只用于逻辑验证，不能代表实验成绩；检查66结果、query22/overlay24调用、100候选×22重排、4400分数池行、P0严格复现和P2同身份/同排名/同分数。
- seed隔离测试直接执行冻结E04 seed函数：只复制指定二文件，无关缓存不复制，旧缓存指纹不变，目标不同内容拒绝覆盖。
- tests_runner_frozen_inputs.log：真实候选输入轻量只读核验24/24通过、45摘录、最长176字符；22查询与冻结来源契约一致；E04/backend/adapter代码SHA一致。未做完整源集合扫描或GPU。

## 运行入口

工作区根目录执行以下PowerShell。正式运行前由主代理冻结最终代码/质量文件并完成保护指纹审查。新运行须使用新的output与空cache。

```powershell
& 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_retrieval_20261012/.venv/Scripts/python.exe' -X utf8 -B 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_e02_pilot_20261013/experiment.py' --queries 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E02小批量实验_20261013/queries.jsonl' --prefixes 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E02小批量实验_20261013/prefixes.jsonl' --reviews 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E02小批量实验_20261013/prefix_review.jsonl' --output 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E02小批量实验_20261013/results.jsonl'
```

逻辑回归：

```powershell
& 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_retrieval_20261012/.venv/Scripts/python.exe' -X utf8 -B 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_e02_pilot_20261013/test_experiment.py'
```

完整源核验、真实推理、最终检索记录完整性和成绩由主代理正式执行后报告。本工具验证不构成真实检索收益。
