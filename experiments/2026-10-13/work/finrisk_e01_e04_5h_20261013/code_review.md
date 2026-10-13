# 五小时实验独立代码审查

审查时刻：2026-10-12 18:41 UTC。结论：**PASS（代码及低成本契约验证）**。未发现新增、需在真实运行前修复的实质 P1/P2。此结论不等于 GPU 实验完成、来源语义获批或新评分完成。

范围：只读审查本轮 `experiment.py`、`evaluate.py`、两份测试、来源构建辅助代码，以及必要的冻结 E04/V2/backend 依赖；仅新增本报告。未改实现、原数据、旧 outputs 或旧 cache；未调用 GPU/API，未读取 .env、教材或360预留正文。

## 验证结果

- 作者 final 后独立执行：`work/finrisk_retrieval_20261012/.venv/Scripts/python.exe -Xutf8 -B -m unittest discover -s work/finrisk_e01_e04_5h_20261013 -p test_*.py -v`。**32 tests，1.747s，OK，退出码0**。测试中合成模型仅验证编排契约，不能作为真实 GPU 分数或收益。
- 真实查询文件通过契约：42条、42个唯一 text；旧回放22条；新风险10条、新边界10条。实际20条新输入的 origin 均为 `new_business_text_not_human_gold`。
- 旧 E02 清单79项、旧 E04 清单96项文件 SHA 全部一致。全库准备 manifest 的 SHA 为 `9f7f2d8cdbc621cfa577d8c5ffac439be3aeeeccc2f0e487cd1210bd78487a8d`，与固定值一致；声明人口9639文书、65475结构单元。
- 对真实24条 scope、4张 card 使用内存中的 rejected review 进行结构校验，均通过且批准数为0。该检查不创建、不继承语义批准。

## 关键实现检查

- 评价器逐段检验原文 span 与显示文本，要求命中原话存在于对应原文，背景为1–3条带来源区间的摘录，限定180字；字段标题不能作为不在原文中的监管引文。scope/background 的审核状态及 unit 关联受检验。
- 评分池去除作者预期、算法、排名、unit、score 等字段；同 query/file 共用全文分，同 query/file/实际显示文本共用片段分。五个 arm 均须覆盖全部输入；每题分母固定5；缺全文或片段判断时保留 incomplete，不按0完成指标。新业务与旧回放分层统计。
- B0/S1/C2/W4/M3均走实际全人口 BM25+BGE 候选路径，每路Top100、RRF k60、rerank100。B0/W4/M3共用原版 view，W4仅改权重为2:1；S1/C2按原文档顺序局部覆盖，未改单元复用原向量。
- 原文档向量只经旧 cache 的模型、文本顺序、key、元数据、npy SHA 与token审计校验后复制到新隔离cache。查询、改变表示、机制卡要求本轮真实编码；改变文本的分数不能复用。分数池绑定 query、unit/file/source、实际索引文本、runtime、manifest及实验输入 SHA，并落盘共享来源。
- M3用真实BGE相似度选固定Top2张已审核候选卡；第三路仅展开合法、源区间相交的支持unit并去重。最终重排与返回原案例，不将生成卡片当引文。记录明确说明Top2可能暴露多张卡的大量共有supports，不能外推为全库机制图收益。
- 拒绝旧目录cache及已有结果/sidecar覆盖；未知或未批准scope保持原版。重复命中保留全部原文位置，分段显示不自动合并主体。

## 运行前后仍需完成的验收

这些是主任务后续执行，非本次代码缺陷：确认最终 scope/card 审核文件的整文件与逐行 SHA；最终 execution_freeze 明确纳入原文档cache `.json/.npy` 及旧输入指纹；代码冻结后进行实际 GPU 42×5运行；检查210条结果、完整实际分数账本、token审计、旧cache末尾指纹；统一本轮新评全部Top5后再形成收益和采用结论。当前测试及tokenizer预检不能代替这些实测。

审查绑定 SHA256：

|文件|SHA256|
|---|---|
|experiment.py|e34f0f978ed731e29e9e1bf47df4ef2c67d3553d999c788c8a20b401234914e9|
|evaluate.py|9226d3785cbbb1271fee40eaced5f6dff723b1a26463cd396f82b76df7ff44a1|
|test_experiment.py|e35e3ad1906c77d3c048fc4da165731794f80d85978f94a4b5ff2996d2166561|
|test_evaluate.py|a2e708a419beae7e5829f2581bc27f9794039f2bb302779365d05d529eb371a8|
