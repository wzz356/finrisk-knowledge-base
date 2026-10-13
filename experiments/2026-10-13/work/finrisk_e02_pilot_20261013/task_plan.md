# E02有证据背景前缀小批量实验 Implementation Plan

> **For agentic workers:** Use executing-plans to execute this plan. Independent prefix preparation and retrieval implementation use dispatching-parallel-agents with isolated context and disjoint files. Verify meaningful failure modes before implementation, then review the code and evidence once before GPU execution.

**Goal:** 在24份文书各一个代表检索片段上，验证有原文支持的背景是否改善对业务输入的判断帮助。

**Architecture:** V2全9639文书/65475单元只读。仅24个单元有背景候选，原文、派生前缀及其支持区间分存。固定22条旧输入回放，比较P0原基线、P1索引/重排/返回均带背景、P2只给P0返回片段补背景。两组全量检索集合相同；新表示只更新24个文本的真实BGE向量，余者从精确匹配的冻结文档向量复制；BM25在完整集合重建。P0/P2同排名，P1固定双路Top100、RRF1:1/k60、rerank100。新池隐藏方法、排名及查询作者预期帮助，所有实际Top5全文/片段用统一尺度重新判断。

**Tech Stack:** 既有本地CUDA BGE模型及检索模块；Python标准库、numpy；JSONL、SHA256及原文区间。

## 用户授权与设计取舍

用户“继续下一步”承接E04报告中已提出的20–30份文书背景实验；范围明确，不再次索要同一小样本实验批准。采用24份、每份一个代表单元，优先可追溯的原文摘录式背景；不做无证自由摘要，不同时去重或调RRF权重。文书和片段是有目的的诊断抽样，不能声称全库/独立确认收益。22条旧输入已经用于E04，均称回放，不再称新确认。

上下文设计与测试遵循brainstorming、writing-plans、planning-with-files及TDD。新work/outputs目录隔离，不修改Git仓库，因此不需要另建Git worktree。无付费项目API、无应用接入、无GitHub发布、无预留360正文。

## Task 1 冻结及选片段

Files: outputs/FinRisk_E02小批量实验_20261013/design.md、cohort.json、prefix_inputs_p1.jsonl、prefix_inputs_p2.jsonl、queries.jsonl、input_freeze.json。

- [x] 核对E04交付SHA及V2绑定；记录旧库/代码/缓存保护指纹。
- [x] 选24文书/24单元：明确的主体/条件问题及Q009/Q012锚点8份；短弱片段8份；有用对照8份，固定种子20261013。每份一个单元，记录完整来源及选取规则。
- [x] 保存22条查询仅query_id/text/group/query_role，不携带anchor/expected_help。评分包不携带作者条件说明。

## Task 2 背景生成与审核

Files: outputs下prefixes_p1.jsonl、prefixes_p2.jsonl、prefixes.jsonl、prefix_review.jsonl、prefix_quality.json。

- [x] 两个独立任务各12单元，只看全文与对应单元；选择1–3段连续原文摘录及适当字段标签，整段前缀不超过180字符，不能依据查询改写。
- [x] 每条摘录有原文区间和语义关联理由；分清文书主体、片段主体、个人责任、行为与日期。未知保留未知，不以监管处罚日期填行为日期。
- [x] 独立审核每条新前缀的同主体/同行为关联；来源逐字匹配只是必要条件。最多一轮修复，实质不确定则该条不用于P1/P2并如实缩小剂量。

Prefix row contract: unit_id、file_id、source_sha256、base_unit_text_sha256、claims（label、quote、span{start,end}、link_reason）、prefix_text、notes。prefix_text严格等于逐行“label：quote”，label仅可用文书主体、片段主体、责任角色、行为背景、适用条件、材料用途、产品背景；不能另加无引文断言。status均为model_review候选，不继承human批准。

## Task 3 对照工具

Files: work/finrisk_e02_pilot_20261013/experiment.py、test_experiment.py、evaluate.py、test_evaluate.py。

- [x] 先失败测试：前缀区间/文本SHA、非法标签、重复单元、语义审核缺席、正文未改、旧缓存不写、变化向量仅更新对应位置、P2同排名、查询/选择漂移和已有输出拒绝覆盖。
- [x] 真实运行P1：相同65475单元，只对审核通过的单元改变索引文本；24个新文本实际BGE编码，完整BM25重建，实际rerank100，不用关键词规则或模拟模型替代。
- [x] 返回文本格式为明确的“背景说明（原文摘录，候选）”+前缀+“原文片段”+旧context；保存两种文本和支持链接，保持unit/file/case身份及原源区间。
- [x] P0严格复现E04 A0，P2仅改变已选单元的返回文本。模型输入及实际返回上下文分别记指纹。
- [x] 全新评价器仅提取输入文字、全文与实际片段；逐字来源验证；固定每题5位置、缺评分拒绝完整统计；缓存原评分不用作本轮语义成绩。
- [x] 必要测试和只读审查通过后冻结代码，再由主代理统一执行GPU。

## Task 4 评分与交付

Files: outputs下results.jsonl及运行侧车、evaluation/、judgments/、实验报告.md、样例对比.md、verification.json、delivery_manifest.json。

- [x] 跑22回放×3方案，保存完整阶段、候选、分数来历、真实耗时和截断审计。
- [x] 全部Top5按统一0–3尺度重新评分，>=2有用；原文摘录可引用、推断不当作原文。隐藏配置/排名/作者预期，模型评分仍非独立人工金标。
- [x] 主指标有用片段@5、至少一段有用覆盖；同时列模型误用警示、全文帮助、弱/无关、排名/上下文的区别和前缀实际出现在Top5的剂量。
- [x] 预定采纳条件：有用片段提高、覆盖不下降、模型警示不增加，主体/条件审核无未解决错误；没有改善则不扩量。P1/P2用于区分检索变化与纯返回背景帮助，不事后调参。
- [x] 核验旧16保护输入/E04交付/旧12缓存及E04的4缓存未变、新记录完整、引文和指标重算一致，保存报告及复跑说明。不直接升级默认或改写全库。

## 当前阶段

本轮E02实验已完成运行、评分、核验和报告独立审核；P1只有1/110配对增量，覆盖不变，2返回范围hold尚未修，决定不全量铺开/不改A0。实验报告、样例及复跑说明已保存，交付清单由package_delivery.py记录并逐文件核验。实验完成不等于前缀生产采用通过；范围修正及独立新输入确认是下一阶段工作。
