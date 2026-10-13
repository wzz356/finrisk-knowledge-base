# 进度

2026-10-13：用户批准五小时实验，截止北京时间07:16:39。已读执行/并行/TDD/验证技能，读取旧E02/E04编排和评分契约；新目录隔离，原库和冻结成果不改。

已派三独立任务：24源范围修正、3–5候选机制卡、5arm真实runner。Root冻结20新业务输入（10风险+10改变关键条件）、合并22回放，共42；来源作者不看输入。验证旧E02/E04交付全集、21保护输入和22旧缓存文件指纹。card Top2在运行前确定，避免少量卡全部展开形成恒定第三路。

Root评价器11项先红后绿全部通过：源区间、原话/同段关系、字段标题不可当原话、范围approval、盲包去作者预期及方法、缺arm、固定5分母、prepare→缺评incomplete→summarize complete。采用新作用范围标题“命中原话的对应原文（逐段独立，不合并主体）”，重复命中保留全部位置和歧义，不强推同事件/同实施者。

作者范围24条：15 scoped、6 single_subject、3 ambiguous_unchanged（F006493/F006220/F000269）；4机制卡/10支持全部独立model_review批准。scope事实初审通过，最终复绑待写。Root tokenizer-only检查发现C2/F001345超限640 tokens，源完整S1为501；阅读全文后只将154字重复背景缩为9字机构简称，事实/责任/条件均未改。初始候选保存在scope_units_initial.jsonl及token_preflight_initial.json；复检46种输入0超限，max embed510/最坏rerank451。root新scope SHA 66891b3a…由独立审核者再核。

runner作者实际21项测试通过；root发现并修/要求修新查询标记、旧manifest键、全文支持quote与unit交集守卫（完整包含过严）。独立代码审核PASS；root在GPU Python实际跑评价11+检索21共32项全部通过，0失败/跳过，1.734秒。真实GPU和语义成绩尚未开始；合成编排不计实际效果。

61输入/代码/旧cache依赖已冻结，独立scope24/card4最终review绑定当前SHA。真实GPU run完成42×5=210条，379.127秒；5744新真实rerank输入，15256同轮完全同模型输入共享，token截断0；42查询只实际编码一批，未变文档不重编码。source全9639核验，阶段console已持久化gpu_run.log。

新评分池268 query-file/274实际context，按整query分3part（90/87/91pair），方法/排名/作者说明删除；三任务实际阅读评判中。曝光机械诊断：S1仅5/210 scope位置、C2仅1/210背景，B0有22/210可修scope获胜单元。主完整语义指标出来前另冻结display_design：固定本轮B0排序/score/model indexed_text，仅对同获胜单元修返回D1及加背景D2；126条，D1/D2各22曝光，0新模型调用。新显示ID与model输入分开。display保留字段测试2先红，初次绿夹具缺scope_profile发生KeyError，补真实契约夹具后2通过；实际126条全部ranking guard通过，主冻结成果不改。补评将只复用同轮主池完全绑定的已有语义分，新增contexts逐条评，不沿用旧E02/E04。

主268/274全部新语义判断完成，各part引用/类型/exact覆盖通过；root summarize complete，verify_delivery新核验passed。B0/S1/C2/W4/M3 useful134/133/133/144/134of210，覆盖39/39/39/40/39，warning9/8/9/8/9；新文字59/59/59/63/59of100。主完整指标出来前的显示phase只复用同轮210全文与216已见context，另38新context由原query评分者补评，D1/D2均137/210、新61/100、覆盖40/42、新20/20，警示与B0相同。

主和显示成绩之后，另存combo_design，W4排序不变加D1范围形成WD。126条、19scope位置、0新model calls；主/显示312同轮已判context精确合并，组合需要267种全部已判，无新的语义分。WD147/210/new65/100，覆盖41/42/new20/20，warning8/210/new6/100。明确是选择后同输入回放，不是独立确认。

root审查发现N014两处有用是贷款案例对医疗险条件披露的泛化框架，非直接医疗险机制证据；同案个人/机构文件不能算独立证据。另存sensitivity，不改原分：排除这两处WD145/210/new63/100，新覆盖19/20；D1/D2新59/100。N018真实代理边界W4/WD由5/5降3/5，Q012各方法0/5，失败保留。

补充核验初次误把cached池两项来源记账标志与fresh池直接比较，定位旧prepare正确设置file_judgment_from_cache/needs_file_judgment；仅校正这两项比较，源/text仍全等，并TDD加2项篡改拒绝回归通过。verify_extra passed：252control记录、10080个file/case hit模型字段保持、全部池/分数/源/指标复算一致，source file语义分不变。不是重评分或降低源校验。报告、完整方案、5真实样例、README/复跑已写；独立报告审核主要重算通过，最终检查及manifest待完成。

独立最终报告审核完成（report_review.md）：关键指标、2310 Top5位置、引文、评分精确复用、token与5744/15256推理槽、冻结源、五样例、复跑CLI逐项一致，未发现实质报告缺陷。README所列最终manifest由独立的封包入口生成并只读核验，所有实验及报告已完成；本轮仅交付小实验候选，不启动全库增强或生产部署。
