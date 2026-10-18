# 36条新题固定执行与评分协议

版本：new36_review_corrected_v1_20261018。此包在未调用模型、未读取当前实现或旧结果的情况下冻结测试材料副本；原query_author四文件完全未改。36条queries原文和文件字节保持原样。

## 参考身份与主报告预注册

本包仍为受控合成输入及模型银标参考。24条非边界参考标为model_silver_independently_reviewed，表示已有未参与编写的模型静态复核；不是人工批准、法律专家金标或模型效果实测。12条boundary_reference_pending原样保留边界身份，不能自动改成insufficient_info，也不能混入主指标。全部human_approved=false，review_origin=current_session_model。

主报告预注册仅计24条非pending题；12条边界题另报“边界挑战”，不以36题混合分数作为主结论。pending整题排除，不从多机制pending题抽出部分机制补入主分母。开发18题=12主分析+6挑战；留出18题=12主分析+6挑战。整题状态、机制集合、必要条件三态与证据跨度分别计分；边界挑战不用于宣称确定法律正确率。

## 固定整组划分

开发：SG01、SG03、SG05、SG08、SG10、SG12、MG01、MG02。
留出：SG02、SG04、SG06、SG07、SG09、SG11、MG03、MG04。

每边8组、18题（6个单机制对+2个多机制三联），状态均为8风险/5未见所测机制明确风险/5事实不足。划分采用独立审核的明确映射，不按结果重新随机切组。开发机制覆盖不含M07、M09；留出不含M01、M05，不为凑齐12机制拆组或换组。

## 模型可见payload

唯一输入源为model_inputs.jsonl。每行严格只有opaque_id、text；opaque_id仅供模型不可见的调度和记账，真正请求的用户内容只能是该行完整text。不可把原query_id、group_id、category、split、analysis_set、参考状态、必要条件答案、私有映射、原文件排列或配对/三联其他版本放进任何模型可见消息。

每题创建全新独立上下文；不沿用上一题消息、回答、缓存对话、检索历史或成对版本。若有固定系统提示、检索上下文和输出模式，由父任务在首次推理前冻结其确切内容、知识快照、参数与SHA-256；检索只能基于当前题和冻结知识，不能检索本包reference目录或带入其他题的参考。此次材料整理没有假定或读取实际运行实现。

全36题已固定打乱，调度仅可按reference/mapping.jsonl筛选本阶段分区并保持其既定execution_order，不能恢复原ID顺序、按状态排序或把同组版本聚合到同一上下文。不透明ID与打乱过程未使用标签；私有复现参数见reference/randomization.json。模型不接收opaque_id、种子或映射。

开发阶段只使用开发18题调试、示例和参数选择；留出参考和逐题结果由评分侧保管，不能在开发时读取并据其调参。最终配置冻结后一次性执行留出；若留出暴露题目缺陷，记录并隔离受影响评分，不能静默改答案反复运行择优。静态作者和审核者已看过全量参考，本协议不声称人员盲测。

## 文件可见性

- model_inputs.jsonl：执行用固定匿名输入，36行，每题仅发送text。
- queries.jsonl：保留原文与原ID的审计副本，不能直接作为模型请求来源。
- reference/expected.jsonl：修正后的私有评分参考。
- reference/mapping.jsonl、split.json、groups.jsonl、randomization.json：私有记账、划分及复现数据，模型不可见。
- reference/source_author_notes.md、source_review.md/json：原作者说明与独立审核的证据副本，模型不可见；前者描述的是修前材料，现行规则以本协议、patch_log和修正参考为准。
- patch_log.json、manifest.json、verification.json：修订、文件哈希及静态验证记录；不属于模型输入。

## 语义与时间修正

030的M04.covered_recipient、M04.transaction_offer、M05.promised_certain改unknown；原引文保留为clue_evidence，不再充当met证明。21题的scope_facts已收窄或重绑，逐项前后差异见patch_log。

023、024的2026-10-08只标为取消日，三天后分别是拟营销安排和目的待核工单。023不补成电话已拨；024原文明示尚未拨号，“周五下午”不作实际通话日。边界机制仍继承原条件卡的法规版本、现行性及直接案例不足限制，未新建2026-08-28之后完整立改废覆盖。

## 实际验证范围

已复验每条输入哈希和逐引用跨度、必要条件ID完整集合、三分类与机制状态一致性、整组划分无交叉、两侧各12主+6挑战、匿名输入仅两字段，以及原作者四文件前后SHA-256未变。字面跨度匹配只证明逐字位置正确；局部语义按R03逐项修订，最终修正副本已由独立审核者复验通过，报告见reference/final_recheck.json；仍为模型银标。没有调用模型或业务API，没有读取实现、旧题或旧结果。
