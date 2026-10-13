# E01–E04五小时受控实验 Implementation Plan

> **For agentic workers:** Use dispatching-parallel-agents for disjoint source preparation and runner implementation; root integrates, reviews and runs GPU. Do not modify frozen previous experiments.

**Goal:** 五小时内交付E01切分、E02背景、E03轻量机制卡、E04检索权重的真实小实验结果与采用/后置结论。

**Architecture:** 全9639文书/65475单元竞争，源及旧候选只读。仅24代表单元创建可回源的实验表示；B0原版、S1主体/行为范围切分、C2切分+限定背景、W4原版BM25:BGE=2:1、M3原版+机制卡候选路，逐项配对比较。不做全库摘要、完整图谱、ANN或应用接入。

**Tech Stack:** 已有本地BGE与reranker、CUDA、numpy、Python标准库；源区间、SHA、JSONL；当前会话模型新评分。

## 时间及边界

- 开始UTC：2026-10-12 18:16:39；截止UTC：2026-10-12 23:16:39（北京时间2026-10-13 07:16:39）。五小时是上限，可以提前交付。
- 前90分钟：24份结构/背景修正、3–5张机制卡、最小检索编排与必要测试；卡不足可缩量如实报告。
- 90–180分钟：审核源与范围、冻结输入代码、真实GPU对照；不同时修改模型/候选池深度。
- 180–270分钟：同一评价协议新评全部Top5，缺项不算0；记录未知与模型偏差。
- 最后30分钟：重算、证据核验、四项报告和总报告。巨大子任务列后置，不拖过截止。
- 所有新文件只写本work及outputs/FinRisk_E01-E04五小时实验_20261013。无付费项目API、无GitHub推送、无360预留正文、无教材PDF或.env读取。

## 实验契约

作用对象：原E02的24单元，unit_id为源单元引用，不冒称新永久ID；representation_id由实验文本SHA派生。每行保留source_sha256、base_unit_text_sha256、实际源segments与语义范围理由。多位置不确定保留歧义，不能挑有利位置。

scope_units.jsonl每行：unit_id、file_id、source_sha256、base_unit_text_sha256、segments[{text,span{start,end},role,reason}]、indexed_text（严格等于segments.text以换行连接）、scope_status（scoped/single_subject/ambiguous_unchanged）、scope_reason、prefix_claims（原E02标签+quote+span+link_reason）、prefix_text（标签+原话逐行）、notes。全部24行，未知不编，段数1–4；单段必须连续逐字原文；ambiguous_unchanged保留原索引文字及全部匹配位置，返回不使用片段主体排他性前缀。

E01只改scope文本与返回边界；E02对同样scope单元补审核通过的短背景，索引/重排/返回均使用，前缀限定到当前命中片段；字段标签与原文分开。所有可见内容需回源；派生说明不能成为监管引文。

mechanism_cards.jsonl每行：card_id、title、mechanism、conditions、boundary_notes、limitations、supports[{file_id,unit_id,source_sha256,quote,span{start,end},role}]、retrieval_text、status=candidate_model、human_approved=false。3–5张，每张至少2份来源；只能称候选机制/核查提示，不能补造反例或法规。作者不看查询或旧成绩。M3真实BGE编码机制卡，按相似度取Top2张，展开经审核supports单元形成第三候选路，RRF等权/k60；最终rerank原单元并返回原案例，不把卡片生成文字当证据或风险答案。

## Task 1 冻结与样本

- [x] 读取旧模块/契约；核对旧E02/E04交付SHA；冻结代码依赖与旧缓存指纹。
- [x] 复用24来源工作包；另冻结20条未用业务输入（10风险+10改变关键条件的边界输入），与22旧回放分开报告；新输入不是人工金标/全27类覆盖。
- [x] 所有作者只见来源及单元，不见查询；当前模型评分、无真人批准如实记录。

## Task 2 E01/E02

Files: outputs/.../scope_units.jsonl、scope_notes.md、scope_review.jsonl。

- [x] 独立作者逐份读24源，修多主体表格/案由弱片段的范围；F004090/F004155强制展示关联依据及残余歧义。
- [x] Root安排独立复核源区间、主体/行为关系和48项实际返回显示；3歧义项保留原版，不伪造批准。
- [x] 记录改动剂量；原内容与新表示分存。

## Task 3 E03

Files: outputs/.../mechanism_cards.jsonl、mechanism_notes.md、mechanism_review.jsonl。

- [x] 独立作者选4个源中存在的机制，跨至少2份文书形成候选卡；不依查询追着改。
- [x] Root安排独立审核各支持事实、条件、概括范围；拒赔卡支持不足未凑数。
- [x] 只试机制卡辅助召回；深度规则库与全库图谱后置。

## Task 4 E04及真实运行

Files: work/.../experiment.py、test_experiment.py、evaluate.py、test_evaluate.py；outputs/.../results.jsonl及sidecars。

- [x] 先失败测试：源/SHA与段匹配、错误主体或歧义不强配、背景字段不能当原话、旧缓存不可写、未变表示复用、第三路不能注入无支持ID、固定分母及缺评分不完整。
- [x] 最小实现B0/S1/C2/W4/M3；各路Top100、rerank100、BGE/reranker同原版。W4仅调融合权重2:1，其他两路1:1；M3第三路1:1:1，固定Top2卡。
- [x] 统一查询编码；相同模型输入同一次真实分数可共享并明确绑定，不能混用改变文本的旧分数。
- [x] Root统一GPU运行，全65475竞争，局部改动不当全库收益；持久化实际阶段、耗时、候选、分数及token截断。

## Task 5 新评分与交付

- [x] 评价池隐藏配置/排名/作者预期，全文与实际context分别判断，全部本轮统一新评；同query/file/text共用同一分。主268/274及显示新增38全部完成；格式干预可见、校验代号可能可见如实披露。
- [x] 主指标有用片段@5（>=2）、至少一段有用覆盖；辅指标全文帮助、误用警示、均分、剂量、时延、重复证据。新旧输入分开。
- [x] 各项采纳门槛：有用提高、覆盖不下降、模型警示不增加；源/范围审核无未解决关键错误。小差异不称显著，全项不强行找赢家。推荐W4候选；E01仅限审核单元返回范围；E02/E03不扩量。
- [x] 保存E01–E04分项结果、总报告、样例、复跑说明、主与补充verification；对后置内容给原因。独立报告复核通过。最终封包的字节证据由delivery_manifest.json与package_delivery.py --check记录。

## 当前阶段

本轮E01–E04小实验、全部模型判断、主/显示/组合复算及独立报告复核已完成。210主记录＋252控制记录，含重复父结果；去重为42输入×8方案=336种组合。全库9639文书/65475单元竞争，局部范围21单元和4卡；不是全量增强或人工金标。36项必要行为测试分别通过。WD是选择后回放，保留N018退步、Q012缺口及N014两处泛化类比敏感性，不更改原分。

## 追加：曝光隔离诊断

- [x] 固定主B0排序/模型输入/分数，生成D1范围与D2背景显示对照，126条；保存设计及父SHA。
- [x] 主评完整后，只复用同轮完全绑定的文件/context分，38新增context由原query对应评分者补评；同轮共268全文/312 context判断。
- [x] 核对D1/D2 rank及score不变、实际22/210曝光，分别报告显示帮助与索引效果，不混作独立GPU试验。
- [x] 选择后的W4+D1组合WD固定W4排序，267需要context全部精确复用；报告147/210、新65/100及排除两争议位置后145/210、新63/100。未冒称独立确认。
