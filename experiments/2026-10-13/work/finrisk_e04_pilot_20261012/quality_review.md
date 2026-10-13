# E04 独立代码质量审查

日期：2026-10-12。结论：**PASS，无需阻止本轮实验的剩余 P1/P2 问题**。本审查在最终候选规格 PASS 并报告主代理后进行；只读实现和既有调用接口，没有修改代码，没有构造/读取确认查询，没有运行 GPU。

## 审查范围

按用户约束检查改动最小化、冻结代码/旧数据只读、真实来源/API/参数校验和实际验证。审查 `experiment.py`、`evaluate.py` 及两套完整测试；进一步核对冻结 `runner.LocalModels.encode/rerank` 的参数和缓存读写行为、V2 aggregate 的调用方式，以及旧 eval 的来源区间和评分验证接口。两项初审只读边界缺口的修复已在 spec_review.md 记录，此处不再列为未解决发现。

## 质量核对

- 融合函数、候选选择、分数补齐、记录聚合、来源核验和 orchestration 分开；数值输入拒绝布尔/非有限值，路内重复不会叠分，实际模型输出要求完整唯一候选。不同配置只消费同一题的分数池，未引入规则评分或模拟正式结果。
- 冻结模块和准备产物保留原 SHA 约束；历史未执行 normalize 的来历和当前实际执行 projection 分开，没有通过修改旧 manifest 或旧代码掩盖差异。A0 内容与五阶段的严格重现能在结果写出前拦截不兼容。
- 缓存修复只新增最小的文档缓存 seed 调用，没有复制整个缓存或改变冻结模型实现。复制前校验模型/tokenizer/单位顺序/key/元信息/向量文件/类型和形状/token audit，目标不同内容不覆盖；失败会中止确认 run。旧源只读，写入限制在新 cache。
- 实验输出区分 partial/failure/complete，完整结果发布前重新校验实验代码、旧代码、查询和 selection SHA；已有结果及 sidecar 不覆盖。结果、分数池和 token 审计具有各自 SHA 来历。时长记录明确共享候选池，不能用于声称四次独立 arm 的 GPU 性能。
- 评分输入验证在写入前完成；输出目录和固定文件名统一隔离校验。恢复时输入 SHA、准备 artifacts、复用证据和 validated 行的绑定都先检查；改 phase 使用新目录，保留旧记录。同一 query/source 的全文旧评分可保留，新上下文单独补分，引用逐字校验，缺评分显式待办。
- 指标中的片段/全文分数及误导标记各自保留，固定五位置分母、known-source 空缺和低全文/高片段分歧有明确处理。盲包与含 arm/rank 的 provenance 分开，待补片段包不暴露缓存全文分值。
- 回归覆盖实际失败模式：旧目录/输入别名覆盖、未知同名 artifact、同 phase 漂移拒绝、复用评分漂移、恢复 validated 漂移、文档缓存错误绑定和不同目标拒绝。未为本轮增加无关重构或产品功能。

## 实际验证与边界

本人最终候选标准 Python `-X utf8 -B` 验证：实验 27 项，26 通过、1 因缺 Torch 跳过；评分 28 项，27 通过、1 因 Windows 沙箱禁止创建真实硬链接跳过。没有失败。硬链接防护函数经静态检查包含 samefile 及 st_nlink 检查，实际建链分支在本环境未完成。原 encode 文档 hit/新 query miss 的 CPU 合成测试由实验实现者在已有 GPU Python 下另跑通过，本人仅将其视为补充证据。没有把合成测试当作实际 GPU 成绩或语义评分。

审查结束再次核对四个候选 SHA，均与规格放行版本一致：

|文件|SHA256|
|---|---|
|experiment.py|dc2269e588af38966be1e2675fb7c86f1caab60f0e11e88e535574cd3a07c46e|
|test_experiment.py|816cb054ba23c552b2f46345eee2e7da85377b47dea1a82f66f43dc9a6d617c9|
|evaluate.py|4f76a7f0655c0db95f9033aa0b74c11ef467cddf707275a40059da4c525a3e0c|
|test_evaluate.py|4a82ae5bee5ca0834826a6d490b7a8cac5e392b2466530a1dfc4a5e698091c6f|

实际开发 GPU、模型盲评、按片段主指标选择并冻结 selection、确认 A0+selected/A3 及最终保护指纹检查由主代理继续执行。A2/A3 最终结果相同的数学约束和共享时长口径在报告中必须保留。
