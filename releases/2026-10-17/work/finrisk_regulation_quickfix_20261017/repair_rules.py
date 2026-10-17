"""Operational screening conditions derived from published V1 cards, not query references.

All predicates use positive wording. They assess proposed/spoken behavior; actual completion is separate.
These are model-authored research interpretations, not executable statutory text or expert legal approval.
"""
from common_paths import BASE,rows

DEFINITIONS=[
('M01','指导本人作不实回访答复',[
 ('review_context','当前涉及保险产品的身份/知悉回访准备或答问'),
 ('false_answer_instruction','明确要求投保人把实际未理解、未获告知或不实事项回答成已知悉；按真实理解答复不满足')],
 '解释后如实回答、预约回访不等于指导造假；录音缺前段不证明此前没告知或客户没理解。'),
('M02','非本人冒名完成回访',[
 ('identity_review','当前涉及应由投保人确认身份或知悉情况的保险回访'),
 ('impersonation','明确安排或出现非本人冒称本人完成身份或知悉确认；公开身份仅预约转接不满足')],
 '本人是否已经完成未来回访不是识别拟议冒名的必要条件；公开预约且不代答本身不是冒名。'),
('M03','无条件扩大保险避债免税效果',[
 ('insurance_legal_promotion','当前向客户说明保险的债务隔离、执行或税务效果'),
 ('unconditional_overclaim','法律效果说明已知超出相关规则对象或条件；绝对覆盖一切债务或所有税种可成立，特定给付是否满足免税对象未知则unknown；准确有条件说明不成立')],
 '特定给付是否属于免税对象未知时保留待核；明细未拿到且准备作说明可候选预警，不自动证明该笔给付应税或宣传避税已经成立。'),
('M04','合同外成交利益',[
 ('covered_recipient','利益对象为投保人、被保险人或受益人'),
 ('transaction_offer','存在与投保成交绑定的经济利益承诺或给付'),
 ('outside_contract','当前已明确利益在真实保险合同约定以外，而非仅缺合同或活动规则材料')],
 '合同给付、年金、真实合同利益不因出现领取或赠送字样自动变成合同外利益；不用等实际兑现才预警明确承诺。'),
('M05','未来非保证利益被保证化',[
 ('uncertain_future_benefit','被承诺对象已明确为未来分红、超过最低保证的万能收益等非保证利益'),
 ('promised_certain','把该非保证部分明确保证为固定必得、不受经营结果影响等')],
 '说明合同确实保证的对象和期间、已归属利益不满足本风险；只知道保证二字而不知对象则待核。'),
('M06','保险与其他金融产品性质混同',[
 ('insurance_known','当前实际推介对象明确为保险产品'),
 ('equated_deposit','当前表述把保险当作存款、基金、理财、信托等另一种金融产品，而非准确区分、反面示例或单纯银行代销')],
 '若实际产品究竟是存款或保险未知，不能仅从柜台或定期二字补出保险性质。'),
('M07','退保金额或损失误导',[
 ('refund_assurance','当前存在关于无损、原额、随时退回等退款保证或明确隐去退保损失的安排'),
 ('known_refund_terms','当前已有保单时点、现金价值、扣费或特殊退款条件，可以判断该保证是否成立'),
 ('refund_conflict','退款保证与这些已知事实明确矛盾，或明确要求隐瞒已知退保损失')],
 '犹豫期和真实特殊退款条件分别核对；记忆性初步说明且明确先暂停等待核实，不能自动写成已知不实承诺。'),
('M08','保障或免责条件误导',[
 ('contract_limit_known','当前材料或说话人明确承认了本合同的责任、等待期、免赔额等重要限制'),
 ('contradiction_or_concealment','当前明确对外说相反内容，或明确拟议故意隐去已知限制')],
 '仅一段可以报而没有合同/治疗资料不能证明此前未核合同或一定不能赔；如实告知限制和反面纠正不满足。'),
('M09','虚假停售或稀缺宣传',[
 ('scarcity_statement','当前存在即将停售/调价或名额稀缺等商业宣传'),
 ('known_notice_violation_or_falsity','当前明确公司未有符合条文要求的公告且不属条文例外，或已知所称停售/配额是虚构')],
 '未附公告或不知道是否发布只能unknown；真实公告准确转告不自动有风险；不能由历史假停售证明当前也是假。'),
('M10','委托无资格机构实质销售',[
 ('substantive_sales','机构受托承担具体产品推荐、条款商谈或促成投保等实质销售'),
 ('institution_unlicensed','当前明确该机构未取得实际销售行为所需的合法资格')],
 '场务、签到或仅前端对接不自动为销售；未提供许可材料不等于无证。机构资格与人员登记分别核。'),
('M11','销售代替当事人确认订立合同文书',[
 ('contract_confirmation','当前为订立保险合同的投保声明等确认文书或相应操作'),
 ('salesperson_substitution','明确由保险销售人员替代当事人确认，而非当事人自主确认或非销售人员合法书面受托'),
 ('personal_record_falsified','明确拟将代操作记录作为客户本人的真实阅读/知悉/确认提交')],
 '明确拟议代操作即可话术预警，无需证明点击已经完成；协助理解与伪造确认区分，不能泛化到全部保全。'),
('M12','取消后继续商业电话营销',[
 ('marketing_cancelled','消费者已明确取消或拒绝相应商业营销'),
 ('later_marketing','后续仍明确拟议或实际向其商业推销，不是按其请求处理已有保单必要服务')],
 '联系目的未知只待核；取消后不夹带营销的理赔材料补正等服务不自动等于违规外呼。')]


def build_specs():
    links=rows(BASE/'tag_rule_links_full.jsonl');rules=rows(BASE/'rules.jsonl');specs=[]
    for mech,title,predicates,boundary in DEFINITIONS:
        relevant=[r for r in rules if r['mechanism_id']==mech]
        tags=list(dict.fromkeys(r['official_tag'] for r in links if r['mechanism_id']==mech))
        specs.append(dict(mechanism_id=mech,title=title,
            predicates=[dict(predicate_id=mech+'.'+key,description=desc,required_status='met',
                required_for_risk=not (mech=='M11' and key=='personal_record_falsified')) for key,desc in predicates],
            boundary=boundary,canonical_label=tags[0],candidate_label_links=tags,
            canonical_policy='以既有候选映射首项作为机制主标签；仅在必要事实均成立时规范化输出，不把全部关联自动提升',
            source_rule_ids=[r['rule_id'] for r in relevant],
            article_refs=list(dict.fromkeys(a for r in relevant for a in r['article_refs'])),
            rule_identity='model_authored_operational_screening_not_expert_legal_determination'))
    return specs


SPECS=build_specs()
SPECS_BY_ID={r['mechanism_id']:r for r in SPECS}
