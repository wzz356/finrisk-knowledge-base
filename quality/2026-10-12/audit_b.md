audit_b独立模型语义抽检
已阅读全文 39/39；非人工验收，不估计全量准确率。

F009587 pass

F003967 needs_fix
- MISSING_PUNISHED_PERSON [major] 原文处罚段明确第二被处罚主体及处罚，候选遗漏。 修订：补个人case及相应unknown关联行为；不得凭职务确定直接责任。
- WRONG_REGULATOR [major] 文书标题不是作出决定机关；原文有明确机关。 修订：按作出决定机关列修订regulator与证据。
- UNSUPPORTED_EXPLICIT_LABEL [major] 财务数据对象不能直接认定客户信息不真实。召回可推测但必须保留条件缺口。 修订：优先其他；若保留客户信息标签改inferred、medium或low并补limitations。

F004660 needs_fix
- WRONG_MARKETING_RELEVANCE [major] 合同外利益是本词典明确的营销违规，保险销售利益事实足以判营销相关。 修订：改true并给出原文事实理由。
- OMITTED_LEGAL_REFS [major] 明确处罚依据不可省略。 修订：保存原文明示法律和条文，不猜其他条款。

F008199 needs_fix
- UNKNOWN_MARKETING_WITH_DIRECT_SALES_FACT [major] 明确保险销售和营销违规事实，非未知。 修订：改true并以委托销售/合同外利益为理由。
- VAGUE_LEGAL_REFS [major] 泛称相关条款遗漏已明示条号。 修订：逐条保存原文第八十六、第一百一十六、第一百七十一条。

F001232 needs_fix
- OMITTED_LEGAL_REFS [major] 明确违法及处罚条文被遗漏。 修订：补原文明示两条法条。

F000728 needs_fix
- UNKNOWN_MARKETING_WITH_DIRECT_SALES_FACT [major] 销售事实与是否获得营销宣传原件是两件事；文书直接记载保险销售。 修订：改true并引用委托销售事实；具体话术未知照常保留。

F001198 needs_fix
- WRONG_MARKETING_RELEVANCE [major] 文书明确违规保险销售渠道，营销相关事实充分。 修订：改true并以无资质保险销售为理由。
- OMITTED_LEGAL_REFS [major] 明示违法依据和处罚条文未保存。 修订：补两个原文明示条文。

F006148 pass

F005844 needs_fix
- OMITTED_LEGAL_REFS [major] 原文明示处罚依据被漏存。 修订：补第八十六条及第一百七十一条。

F007196 uncertain
- MARKETING_TRAINING_FLAG_REVIEW [minor] 培训材料违规是营销活动类，但文本仅载内部培训，未明示销售用途；这属于口径需统一的边界，不直接升级为确凿错误。 修订：补营销判断理由中内部培训用途未明的限制；由root按既定营销口径统一。

F004550 pass

F001216 needs_fix
- UNKNOWN_MARKETING_WITH_DIRECT_SALES_FACT [major] 原文已明确电话产品介绍与误导性话术，未取得原件不能成为营销未知的理由。 修订：改true并保存电话介绍及培训误导证据。
- OMITTED_LEGAL_REFS [major] 两组明确违法、处罚及个人责任条号全部漏填。 修订：按原文分组保存法条和对应个人依据，不把条文引用泛写。
- ACTION_OBJECT_DUPLICATED [major] 动作句作为对象会损失字段含义，违反v2补充的动作对象分别保存要求。 修订：逐条拆动作和对象；对象未明确时null并写缺失理由，不造对象。
- MISSING_SPECIFIC_RECALL_LABEL [major] 明确电话销售中的违规行为符合官方电销违规，1至3标签限制内可完整召回。 修订：对公司电话行为及明示主管责任增加电销违规。

F006045 pass

F002973 needs_fix
- OMITTED_LEGAL_REFS [major] 明确违法和处罚依据未保存。 修订：补原文两条法条。

F000306 needs_fix
- OMITTED_LEGAL_REFS [major] 两事项违法、处罚及个人依据均明示，候选两案漏填。 修订：分别补第23、第94、第101条及对应主体。

F003758 needs_fix
- OMITTED_LEGAL_REFS [major] 违法及个人处罚依据均明确，未保存具体法条。 修订：补原文三条依据。

F006352 needs_fix
- VAGUE_LEGAL_REFS [major] 引文虽保存，但法条字段语义值没有法律名称与具体条号，已明示内容应结构化保存。 修订：用明示法条替换泛写value，保留原文引用。

F000472 needs_fix
- WRONG_MARKETING_RELEVANCE [major] 明确合同外利益属于营销违规相关事实。 修订：改true，以合同外利益作为文书营销相关依据。
- OMITTED_LEGAL_REFS [major] 机构与个人的明确违法处罚法条均未填，不能仅由全文覆盖替代。 修订：按两事项和明确个人责任补第116、161、86、170、171条。

F008707 needs_fix
- UNKNOWN_MARKETING_WITH_DECEPTION_FACT [major] 欺骗投保人是明确保险销售误导类事实，可判营销相关而具体话术仍未知。 修订：改true并引用欺骗投保人事实。
- INFERRED_TAG_MISSING_MECHANISM_LIMITATION [major] 推测标签允许召回，但个人角色缺口不能覆盖额外的套费机制缺口。 修订：添加“资料类别/费用科目/资金套取均未明”的机制限制；按关联强弱调整confidence。

F003089 needs_fix
- GENERIC_OBJECT_MISMATCH [minor] 营业费用不是工资卡或费用发票；摘要正确但对象字段被统一模板覆盖。 修订：按三个机制分别修正对象，个人责任记录指向相应机构事项。

F004694 pass

F004586 needs_fix
- UNKNOWN_MARKETING_WITH_DIRECT_SALES_FACT [major] 明示违规销售即可判营销相关，无需补具体误导机制。 修订：改true，以违规销售事实为理由，具体机制继续未知。

F005834 pass

F007796 needs_fix
- OMITTED_LEGAL_REFS [major] 原文明示处罚法条未填。 修订：补明示第69条，各主体按文书共同依据保存但不推个人责任类型。

F003314 needs_fix
- MASSIVE_BEHAVIOR_OMISSION [critical] 候选把事实总引导句当唯一行为，遗漏整份长文的实质事实、金额期间、否定限定及对应召回。 修订：按阅读全文结果逐机制重建behavior及coverage；所有数字范围条件保留对应原文连续证据。
- BEHAVIOR_DATE_AS_PENALTY_DATE [critical] 2007-05-18是私印保单行为起日；末尾完整署期2009-05-13。 修订：改决定日2009-05-13，原文署期逐字保留；行为起日归对应行为期间。
- MISSING_EXPLICIT_PENALTY_AMOUNTS [critical] 原文分组决定明确三项金额，无理由全置未知。 修订：分别保存三项罚款及对应事项范围、连续处罚引文。
- WRONG_REGULATOR [major] 受罚公司不是监管机关的一部分。 修订：使用原标题中的机关名称并独立绑定公司主体。
- OMITTED_LEGAL_REFS [major] 分组适用条文明示但全遗漏。 修订：按原文各组逐条保留，不补现行版本。
- WRONG_MARKETING_RELEVANCE [major] 以投保形式约定保费出资人投资回报的行为已有营销关联，不能以简要案由排除。 修订：改true；承诺收益等可inferred召回，注明赔款投资机制不等正常产品收益率。

F002890 needs_fix
- INVENTED_PENALTY_TYPE [major] “责令停止”不是另一个“责令改正”；原文无该处罚。 修订：删除无据责令改正，停止新业务项保完整范围。
- FINDING_QUOTE_ONLY_PENALTY [major] 处罚末尾本身不能证明摘要所称具体责任事项。 修订：扩到对应当事人事实责任段，保留申辩及采纳，FD-P01用具体责任原称谓。
- INDEPENDENT_MECHANISMS_MERGED [major] 假批退财务冲销与假退费签名清单是独立动作，合并丢机制及对应事实。 修订：局部拆机构复合行为，保源主体链路及所载具体数额。
- OMITTED_LIMITS_ARGUMENTS_MITIGATION [major] 逐字全文coverage不能代替关键数字、否定、申辩和采纳结果的语义保存。 修订：补对应conditions/factors/negations/exceptions；依法不推出减轻具体子项。
- PERSON_OBJECT_EXPANDS_UNRELATED_ITEMS [major] 统一对象把投资、任职等行为扩加到无此责任记载的个人。 修订：逐人修action、object、FD-P01及coverage绑定，禁止把所有个人挂每段。
- OMITTED_MITIGATION_LEGAL_REF [major] 明确用于处罚裁量的法条不能漏存。 修订：给王野田、刘琦、李桂琴补明确第27条与对应段证据。

F001744 needs_fix
- OMITTED_DETAILED_TIME_LIMITS [minor] 完整日期是任职与职业责任险连续性判断的关键条件，不能只有原文引用或声称保留。 修订：补对应conditions或时间因子，用原连续证据保各任命/投保期，不作处罚日期。

F008914 needs_fix
- OMITTED_BEHAVIOR_PERIOD [major] 行为期间明确但漏掉，全文引文不能代替期间语义值。 修订：补case行为期及behavior条件或时期因子。

F001294 needs_fix
- WRONG_MARKETING_RELEVANCE [major] 明确合同外利益是营销相关事项。 修订：改true并引用合同外利益事实。

F005641 needs_fix
- OMITTED_LEGAL_REFS [major] 明确处罚依据未保存。 修订：补三条原文法条，不按个人职务猜具体适用子项。

F000561 needs_fix
- OMITTED_ARGUMENT_QUALIFICATION [minor] 否定和机关回应属于实质限定；不能只说从轻未获采纳而遗漏原主观否认。 修订：补申辩、采纳和不采纳结果的条件/否定项，避免将申辩当认定事实。
- TARGET_SCOPE_TRUNCATED [minor] 能繁限定与或关系不应简化为一般母猪赔案。 修订：三个照片行为摘要和对象使用水稻或能繁母猪，保或关系。

F000092 needs_fix
- UNKNOWN_MARKETING_WITH_DECEPTION_FACT [major] 欺骗投保人明确属于销售误导类，具体渠道未知不阻断营销相关判断。 修订：改true并引用欺骗投保人，不把电话中心名称升级实际通话证据。

F002373 pass

F002918 needs_fix
- OMITTED_LEGAL_REFS [major] 明确违法和吊销依据未保存。 修订：补原文两条依据，不从财务未建账推虚列套取。

F009099 pass

F001347 needs_fix
- OMITTED_ARGUMENT_DISPOSITION [minor] 申辩及采纳结果属于需保留实质信息，不能仅在整段证据中出现。 修订：补condition或exception区分申辩事实与机关不采信结果；不猜具体申辩内容。

F005669 pass

F009750 needs_fix
- UNKNOWN_MARKETING_WITH_DIRECT_SALES_FACT [major] 明确销售误导/营销违规事实足以判营销相关。 修订：改true并给具体合同外利益、隐瞒重要信息事实理由。

F007794 pass
