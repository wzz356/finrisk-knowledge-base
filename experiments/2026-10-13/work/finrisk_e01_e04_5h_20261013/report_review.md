# E01–E04五小时实验独立报告审核

审核时间：2026-10-12T19:59:38Z（北京时间2026-10-13）。审核者：独立会话模型，非人类批准。

结论：已审报告中的关键指标、样例原文、推理/评分复用边界及候选方案与实际产物一致，未发现实质性报告缺陷。推荐结论保持为下一离线版本的候选；没有把同轮选择后的组合当成独立确认，没有将模型意见升级为人工金标或全库采用。

## 审核范围与实际操作

读取实验总报告、完整方案、README、复跑说明、样例对比及评分规则；对照analysis、三阶段metrics/per_query/validated_judgments/blind_pool、source_review_notes/scope_review/mechanism_review、input/execution freeze、retrieval_diagnostics、sensitivity、verification/verification_extra、设计和评分阅读记录、运行/测试日志，以及相关实现。

使用独立临时只读核算，未调用报告生成器或会写时间戳的verify_delivery/verify_extra主入口。仅运行experiment.py --help和evaluate.py prepare/summarize --help；三个命令均退出0。没有重新检索、模型推理、付费API调用或重复整套测试，没有读取.env、教材正文或360预留正文，没有修改源、评分、报告或旧交付；本审核只新增本文件。

## 独立复算结果

- 主结果210条，42×B0/S1/C2/W4/M3；显示126条，复用B0；组合126条，复用B0/W4。去重后是8方案×42=336种输入/方案，462是文件累计记录数。报告没有称其为462次独立运行或输入。
- 三阶段池分别为268配对/274 context、210/254、248/267；三阶段remaining_pool均空。主/显示的不同context精确合并为268配对/312 context；显示新增38。组合267 context的全文字段和片段判断与同轮已判读池逐字段相等，没有新语义评分。
- 2310个Top5位置逐一核对per_query的returned_hit与实际结果、全文/片段grade/reason/quote与validated_judgments、context SHA与池正文。所有≥2分引用均连续逐字存在于实际片段及完整原文；全文正分引用均存在完整原文。
- 每方案固定210分母。独立复算所有8方案及新20/旧22/新风险10/新边界10分层，与analysis及三阶段metrics一致。

|方案|总体有用|覆盖|片段警示|新20有用|scope曝光|prefix曝光|
|---|---:|---:|---:|---:|---:|---:|
|B0|134/210|39/42|9|59/100|0|0|
|S1|133/210|39/42|8|59/100|5|0|
|C2|133/210|39/42|9|59/100|1|1|
|W4|144/210|40/42|8|63/100|0|0|
|M3|134/210|39/42|9|59/100|0|0|
|D1|137/210|40/42|9|61/100|22|0|
|D2|137/210|40/42|9|61/100|22|22|
|WD|147/210|41/42|8|65/100|19|0|

独立排除N014/F001987、F001988两位置后，D1/D2=135/210、覆盖39/42、新59/100、新覆盖19/20；WD=145/210、覆盖40/42、新63/100、新覆盖19/20，与sensitivity一致。该核算未改原分，也不是统一重标全部案例的严格同机制金标。

N018的有用位置为B0 5/5、W4/WD 3/5，确实少2；Q012所有方案仍0/5；Q009为B0 0/5、W4/WD 2/5。报告准确保留退步/失败，并把Q009新增帮助描述为给付条件核查，没有补称同疾病直接证据。

## 推理、来源与冻结绑定

- 从21000行score pool逐行重算binding canonical SHA、查询原话SHA、runtime和experiment inputs，核对首次真实分数及随后共享分数。另从65475条实际索引原单元和21条scope独立重建五方案模型文本SHA，21000行indexed_text/representation/file/source绑定全部正确。5744唯一真实rerank输入，15256同轮精确共享；210种输入/主方案每种均100候选槽。没有旧rerank复用标志。
- 全部token侧车逐行检查：0截断、0拒绝，存在used_tokens的行均与input_tokens相等。实际embedding最大510，实际rerank最大436；token_preflight最大embedding510、最坏pair451。报告区分了预检与实际运行。
- 显示及组合的files/cases共10080个命中，逐一比对父结果的file/unit/rank/score、indexed_text/representation/indexed_source字段、case/source字段及stages，均保持相同；新显示表示另存，未伪称长文本参与旧模型分数。
- 61冻结依赖、21旧保护输入、22旧cache文件及175旧E02/E04交付条目逐SHA相同；主results、score/token侧车及三阶段评价/复用输入指纹相同。独立检查没有运行会改核验产物的入口。
- 24源全文共25497字符，source SHA和unit文本SHA正确；24条scope的35段源span逐字相等，prefix quote逐字相等，canonical行及整个scope文件与review绑定。分型15 scoped、6 single_subject、3 ambiguous_unchanged，21条可装饰范围一致。
- 4卡/10支持/10不同file的source、quote/span、unit/file及canonical review绑定通过。不同file不视为独立事件。所有审核人类批准均false。
- 检索曝光按file/unit Top5列表复算：S1 12输入变化、C2 13、W4 25、M3 3；与diagnostics相同。只按file忽略获胜unit的临时初算不符合该字段定义，修正核算口径后通过，并未改产物。

主实现中BM25 k1=1.5/b=0.75，RRF k60、每路Top100、rerank100以及各方案权重均有直接代码依据。运行侧车绑定实际本地BGE/reranker快照、cuda/float16/batch16/max512、42查询单次编码、36改表示和4卡编码。日志379.127秒与报告一致，报告明确它不含会话判读/编排，不能作为生产请求延迟或全实验零成本。

## 样例与结论边界

独立解析样例Markdown，5条输入与记录完全相同；9个展示命中的完整文本、rank、grade、warning、reason和evidence_quote逐字对应实际returned_hit及判断。C002/B0中F004490确实未进Top5，未入说明正确。

F001987/F001988实际内容为贷款话术和条款差异，不含医疗险等待期/免责直接事实。报告、样例和完整方案均披露两文件为同事件不同主体，不是两份独立证据。没有凭处罚结果补出输入违法；空气污染健康津贴条件、真实渠道/虚挂边界及未修跨表行主体问题的表述与展示文字相符。

显示追加和WD选择后的性质已有设计、结果及公开报告说明。主/显示全文评分保持原分，组合精确继承同轮评分。评分样式可见、校验代号可能可见、模型尺度和1/2分边界、20条会话构造且10对相关、未证事件隔离、未覆盖全部27类、scope只审代表单元等限制均已披露。候选W4和局部WD建议没有外推最终风险标签准确率或自动批准全库。

## 复跑与交付说明

复跑说明中的两个Python路径真实存在，experiment与evaluate参数由实际--help确认；新output/cache约束有实现依据。显示/组合入口固定本轮父结果，报告已提示不能直接覆盖、不能无条件继承旧评分。

已读主32项、显示2项、补充2项通过日志及缓存标志修正代码/测试。补充比较只允许file_judgment_from_cache与needs_file_judgment两项记账变化，其他源/显示仍整对象比较，并有源/显示篡改拒绝测试；主冻结实现SHA未变。此处审核既有测试证据和本次独立数据核算，没有宣称重新运行全部测试。

最终delivery_manifest/package_delivery由协调者随后生成，审核时README的manifest链接尚待该步骤；这属于已知收尾，不作为当前报告缺陷。最终清单需包含本审核记录，生成后由协调者核对字节清单。除该已安排封包外，没有新发现的必修项。

## 本次所审文本指纹

|文件|SHA256|
|---|---|
|实验总报告.md|3166d3e0ea069c7a8f454e6cfffb73d0b644dd9d38eafc8a72dcde032c70fa37|
|完整方案.md|4c20280168339b25f43494f54f79f113885dda1bae6029a2d6ab07c40a6570ae|
|README.md|9c8919e38704b498dbe8c9345fe904649f6cc136be2500e5676c10797c896d68|
|复跑说明.md|fd51881e156c9109272e9ec2574cf9fa574cde21f3752640466af5334fddad34|
|样例对比.md|4b990ab7d234fa4e67f14ee66f0fdab33bd75db5d7ab3d3b2ccd593ee8ee45d9|

本审核是机械一致性与报告证据边界复核，不是第二套独立人工语义金标，也不替代全库内容验收。
