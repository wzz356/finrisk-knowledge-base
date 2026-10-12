import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POOL = ROOT / 'independent_audit_pool.jsonl'
OUT = ROOT / 'independent_audit_judgments.jsonl'
rows = [json.loads(line) for line in POOL.read_text(encoding='utf-8').splitlines()]
judgments = []

def add(index, grade, kind, mechanism, conditions, quote, reason, limits, context_decisions, misleading=False):
    row = rows[index]
    assert len(context_decisions) == len(row['contexts'])
    contexts = []
    for source, decision in zip(row['contexts'], context_decisions):
        cg, cq, cr, cm = decision
        if cg >= 2:
            assert cq and cq in source['text'] and cq in row['full_source_text'], (index, source['context_id'], cq)
        contexts.append(dict(context_id=source['context_id'], help_grade=cg, evidence_quote=cq,
                             reason=cr, misleading_risk=cm))
    if grade >= 2:
        assert quote and quote in row['full_source_text'], (index, quote)
    judgments.append(dict(pair_id=row['pair_id'], help_grade=grade, help_type=kind,
                          mechanism_match=mechanism, conditions_match=conditions,
                          source_quote=quote, reason=reason, limitations=limits,
                          misleading_risk=misleading, contexts=contexts))

def save():
    OUT.write_text(''.join(json.dumps(j, ensure_ascii=False) + '\n' for j in judgments), encoding='utf-8')
    print(f'Saved {len(judgments)} pairs / {sum(len(j["contexts"]) for j in judgments)} contexts')

q0 = '将保险条\n款、保险费\n率与银行机\n构的存款利\n率进行片面\n比较'
add(0, 2, 'support', 'same', 'partial', q0,
    '简表直接载明保险与银行存款利率的片面比较，可提示不能仅凭数字判断。',
    ['未说明计算口径或具体比较条件；原文是条款、费率与存款利率。'],
    [(2, q0, '片段完整呈现片面比较行为，支持审查比较口径及条件是否充分。', False)])
q1 = '承诺 “承运人责任险若发生人伤案件医疗费用不分医保用药和非医保用药,我公司按实际损失金额的100%比例进行赔付”,扩大保险责任。'
add(1, 2, 'support', 'partial', 'partial', q1,
    '原文认定忽略用药条件并承诺百分百赔付扩大责任，能帮助检查宣传条件。',
    ['案涉承运人责任险，不是百万医疗险；输入已有责任范围限定，须核对实际条款。'],
    [(2, q1, '可见百分百赔付和用药条件被忽略的具体事实，提示核实是否扩大保障。', False)])
q2 = '只要凭病理报告他就可以给钱,确诊就给钱。”没有给消费者强调条款\n约定免除责任的内容。'
add(2, 3, 'support', 'same', 'compatible', q2,
    '原文直接记录确诊给钱话术及免责条件未强调，清楚支持区分诊断与给付条件。',
    ['原案话术另含超过两年条件；不能据此替代输入产品的合同审查。'],
    [(3, q2, '话术、免责条件遗漏和管理责任均可见，直接帮助识别无条件给付风险。', False),
     (3, q2, '片段保留确诊给钱及免责条件遗漏，能够直接区分诊断事件与合同给付。', False)])
q3 = '没\n有明确说明其贷款保证保险\n产品及需要缴纳保费问题。'
add(3, 2, 'support', 'partial', 'partial', q3,
    '朋友圈宣传未说明产品性质及保费的处罚，能帮助审查险种与费用表达。',
    ['原案是贷款保证保险，未涉及两全险冒称意外险或局部费率、保障内容。'],
    [(2, q3, '片段载明朋友圈隐去产品性质与保费，提供产品身份和费用披露对照。', False)])
q4 = '超过13%的保单存在曲解商业车险费率改革、\n电话销售等政策法规的情况,质检均未及时发现和纠正'
add(4, 3, 'support', 'same', 'partial', q4,
    '原文认定电销曲解政策法规并说明质检缺失及追责，有较完整的同类行为依据。',
    ['原案是车险费率改革及电销政策；未明确载明输入所称内部销售政策错误。'],
    [(1, '', '片段仅载与事实不符促销及申辩，未呈现曲解法规政策的具体机制。', False),
     (2, q4, '明确呈现电销曲解政策法规与质检遗漏，可帮助核对话术所依据规则。', False),
     (2, q4, '主体前缀未扩张责任，正文明确载政策法规曲解及质检未纠正事实。', False)])
add(5, 1, 'irrelevant', 'different', 'unknown', '',
    '电话销售虚假服务承诺是附近主题，但原文不涉及理赔手续便利或办理速度。',
    ['原案涉及退休工资、如实告知及洗牙等合同外赠送服务，不能据此评判理赔速度。'],
    [(1, '', '承诺赠送服务却未实际赠与属邻近线索，不能明确支持理赔便利速度机制。', False),
     (1, '', '前缀载合同外服务赠送，正文主要是处罚依据，未提供理赔流程或时长。', False)])
q6 = '向参与者随机赠送国通电子储油卡。2018年1月至8月,结算金额共计1398068.3元。上述费用错误列支在理赔费用-车辆费用-燃油费科目项下。'
add(6, 2, 'support', 'partial', 'partial', q6,
    '原文同时涉及车险客户赠券和储油卡错误列支，可帮助分别核查赠送及费用用途。',
    ['储油卡对象是活动参与者，未说明均为投保人；错误列支在理赔燃油费，不是宣传费。'],
    [(2, q6, '具体载储油卡赠送与错误列支，可支持核对实际用途，但未说明投保人受赠。', False)])
q7 = '电话销售过程中存在欺骗投保人的行为,涉及保单53份。其中,夸大产品收益,涉及保单12份;错误解释保险责任,涉及保单22份;'
q7c2 = '对缴费期间进行误导性解\n释,涉及保单8份;以产品升级名义诱导客户购买新保单,涉及保单3份;'
add(7, 2, 'support', 'partial', 'partial', q7,
    '原文明确列出电销产品误导类型并以录音证明，可帮助回听核查介绍内容。',
    ['原案主体是保险公司电销中心；不支持代理公司冒用保险公司来电身份的认定。'],
    [(2, q7, '列明收益、责任等多类产品介绍误导，可帮助检查录音内容但不证明身份冒用。', False),
     (2, q7c2, '可见缴费期间误导及权益隐瞒，提供内容审查线索但未涉及来电主体身份。', False)])
save()

q8 = '你公司把并非是纵横代理公司代理的保险业务虚挂在该公司名下,并通过银行转账方式将手续费支付给代理公司,纵横代理公司按手续费金额8%的比例扣除开具发票费用后,把你公司支付的手续费余额以现金\n或转账方式套取出来,交给你公司业务员并转支付给其他代理人。'
add(8, 3, 'support', 'same', 'partial', q8,
    '原文完整描述业务虚挂、手续费先付代理机构及扣费返还业务员的资金路径。',
    ['原文业务员的劳动关系未明；输入员工归属仍需单独核实。'],
    [(3, q8, '片段保留非代理来源、虚挂及扣费返款链条，能直接核对业务与资金路径。', False)])
q9 = '你公司对于上述保费资金的收付及所谓“业务费用”的支付等均未纳入账内进行会计核算,也未能提供相关凭证和证明资料,属帐外经营'
q9c = '你公司对于上述业务未建立详细的业务记录,也未进行业务档案或专门帐簿管理'
add(9, 2, 'support', 'partial', 'partial', q9,
    '代理机构收支未入账、缺凭证并无详细业务记录，明确帮助检查财务基础记录。',
    ['原案针对共保保费及业务费用，不表明全部佣金工资房租均无账簿或财务报表。'],
    [(2, q9c, '明确载未建业务记录及专门账簿，能支持查基础记录，收支凭证细节不可见。', False)])
q10 = '将营业货车改为特种车II类车辆承保的行为。所涉及的2份保单(交强险及商业车险\n保单各1份)签单保费合计9398.26元,实际应收取保费22183.16元,合计少收保费12784.9元。'
add(10, 3, 'support', 'same', 'partial', q10,
    '具体载明营业货车改用其他类别导致少收保费并处罚，清楚支持核对真实用途。',
    ['原案改为特种车II类，未载营业改非营业或家用车辆的两种具体变更。'],
    [(3, q10, '车辆实际类别、改用类别及应收差额均可见，可直接帮助辨别费率类别错误。', False)])
add(11, 1, 'irrelevant', 'different', 'unknown', '',
    '仅有偿付能力最低资本计算错误这一附近主题，未涉及单一风险限额或分保。',
    ['最低资本计算不同于实有资本金、公积金的单风险限额；原文无保证保险分保事实。'],
    [(1, '', '片段的资本计算违规仅属宽泛线索，不能核实十分之一限额和再保险安排。', False)])
q12 = '对故意编造未曾发生的保险事故、虚构\n保险合同或者故意夸大已经发生的保险\n事故的损失程度进行虚假理赔,骗取保险\n金或者牟取其他不正当利益'
add(12, 2, 'support', 'same', 'partial', q12,
    '简表直接载编造事故和夸大已有损失进行虚假理赔，明确帮助区分两类事实。',
    ['未说明具体赔案、相机采购或款项去向；核损员责任不能扩张到所有承办人员。'],
    [(2, q12, '片段完整保留两种虚假理赔机制及核损员身份，可帮助分别审查事故与损失。', False)])
add(13, 0, 'irrelevant', 'different', 'unknown', '',
    '原文涉及代理资格、代签名、费用及团险销售，未提供保险金给付不落实依据。',
    [],
    [(0, '', '片段只呈现代理合同与事实证明材料，没有承办理赔或保险金给付事实。', False)])
q14 = '在理赔时编造保险事故或扩大部分农户损失程度进行赔付,赔款用于返还代垫保费或村组工作经费的问\n题。'
q14c = '赔款用于返还代垫保费或村组工作经费的问\n题。虚假理赔涉及赔案6笔'
add(14, 2, 'support', 'partial', 'partial', q14,
    '种植险虚假赔款返还代垫保费的明确事实，可帮助追查赔款实际对象及用途。',
    ['原案另有编造事故或夸大损失；未载利息、次年预收或抵付其他险种保费。'],
    [(2, q14c, '可见赔款用于代垫保费及村组经费并属虚假理赔，可帮助辨别资金用途。', False),
     (2, q14, '片段保留种植险、虚假理赔及代垫保费返还链条，提供资金用途的具体对照。', False)])
q15 = '2009年你公司投保的职业责任保险的保险期限为2009年7月16日至2010年7月15日,2011年你公司投保的职业责任保险期限为2011年3月25日至2012年3月24日。2010年7月16日至2011年3月24日期\n间,你公司未保持职业责任保险的有效性和连续性。'
q15c = '你公司未保持职业责任保险的有效性和连续性。\n二、上述未保持职业责任保险的有效性和连续性行为违反了《保险专业代理机构监管规定》第四十条的规定'
add(15, 3, 'support', 'same', 'compatible', q15,
    '两张保单起止与中间空档、连续性违规认定均完整，直接支持审核经营期间覆盖。',
    ['仍须核对输入机构的经营期间及保单起止；原案规则有时间适用范围。'],
    [(2, q15c, '仍明确载未保持连续性的认定，但保单起止及空档起日被截断，难核对期间。', True)])
save()

add(16, 1, 'boundary', 'partial', 'unknown', '',
    '原文仅称培训课件有误导性内容，未说明保险冒充存款或反例纠错的关键条件。',
    ['不能把课件出现错误话语等同于认可使用；原文未说明是否反面示例或销售提纲。'],
    [(1, '', '只载课件有不规范误导内容，缺少原话和使用目的，无法判断禁止反例的边界。', False),
     (1, '', '课件误导是宽泛线索，未说明反例标注及是否交付销售使用，不足明确对照。', False),
     (1, '', '课件误导及其他渠道违规均可见，但未呈现存款话术或纠错培训的适用条件。', False),
     (1, '', '可见培训误导及回访管理问题，不能据此将禁止使用的反例认定为误导宣传。', False)])
q17 = '将“生存保险金”宣传为“利\n息”、称“10年后能够连本带息取回”;将不确定的利益宣传为承诺约定利益,夸大保险产品的利益'
add(17, 2, 'boundary', 'partial', 'conflict', q17,
    '原文将保险金称利息并保证不确定利益，能对照完整解释非保证部分的差别。',
    ['原案未直接比较保险与银行两个利率；不能证明输入的完整比较一定合规或违规。'],
    [(2, q17, '具体显示利息化、保证不确定利益及取回承诺，可对照披露条件充分与否。', False)])
add(18, 0, 'irrelevant', 'different', 'unknown', '',
    '原案是电销欺骗、万能险渠道及伪造承保录音，未涉及销售执业证或档案电话维护。',
    ['原案不真实联系电话属于被保险人及录音造假，不能套到销售人员电话号码更正。'],
    [(0, '', '片段载条款费率和欺骗投保人的管理责任，无销售人员登记发证的依据。', False)])
q19 = '2012年,分公司委托2家无兼业代理许可证的邮储银行网点从事保险销售活动。'
add(19, 3, 'boundary', 'same', 'unknown', q19,
    '银行网点已无证销售的具体事实及处罚明确，可帮助确认须核验保险代理许可。',
    ['输入仍在审核且许可未知；原案的无证并已销售条件尚未在输入得到确认。'],
    [(3, q19, '无兼业代理许可的银行网点已销售及对应处罚可见，能提示核查许可与实施状态。', False)])
q20 = '增提未决赔款准备金的目的是规避监管,相关数据均是根据规避监管需要倒算得出,并非以实际经济活动为依据进行会计确认、计量和报告。'
add(20, 3, 'boundary', 'partial', 'conflict', q20,
    '监管复核明确以规避监管倒算而非实际活动为依据，清楚帮助对照损失依据变化。',
    ['原案大幅增提准备金，不是少提或删赔案；输入新证据及审批尚须验证，不能据此认定合规。'],
    [(1, '', '只呈现当事人主张实际成本变化的申辩，缺少后续驳回，不能作为监管认可依据。', True),
     (3, q20, '复核明确倒算监管目标且赔付基本稳定，直接帮助区分真实依据变化与改数规避。', False)])
q21 = '2008年签发的1笔政策性能繁母猪养殖保险凭证未列明耳标号,且保险期限列示错误;'
add(21, 2, 'support', 'same', 'partial', q21,
    '母猪保险缺耳标号的具体事实提示标的识别记录独立重要，客户信息完整不能替代。',
    ['原案是未列耳标号，输入是号码与现场不符；原案并未说明客户姓名电话是否完整。'],
    [(2, q21, '明确载母猪保险凭证缺耳标号，能帮助单独审查标的识别信息的完整准确。', False),
     (2, q21, '耳标遗漏及期限错误直接可见，支持核验标的记录而非只检查投保人身份。', False)])
q22 = '2017年至2018年4月,39件涉及赔款金额的保险公估报告中未指明赔款金额所依据的保险条款。'
q22c3 = '该公司存在保险公估报告未列明赔款金额依据的保险条款的违法行为:'
add(22, 3, 'support', 'same', 'compatible', q22,
    '明确记录公估报告列赔款却无所据条款，且有专门公估规定与责任认定，直接帮助审核。',
    ['原案处罚分公司负责人直接管理责任；不能据此直接确认输入具体责任人员。'],
    [(3, q22, '公估身份、报告缺赔款条款依据及专门规则均可见，能明确区分公估与销售。', False),
     (3, q22, '正文完整列明公估报告、涉及赔款与条款依据缺失的事实，可直接帮助审核结论。', False),
     (2, q22c3, '前缀保留公估报告缺依据机制，正文给专门规则及管理责任，可帮助确认适用领域。', False)])
q23 = '车险\n销售过程中向投保人返还利益;向不具\n有保险代理资质机构支付车险销售费\n用;'
q23c1 = '车险\n销售过程中向投保人返还利益;'
q23c2 = '销售过程中向投保人返还利益;向不具\n有保险代理资质机构支付车险销售费\n用;'
add(23, 2, 'boundary', 'partial', 'unknown', q23,
    '简表分别载投保人返利与无代理资质机构销售费，可帮助审查企业角色和款项性质。',
    ['未涉及汽车销售企业或明确现金返款；输入来源方是否投保人、代理资质均未确认。'],
    [(2, q23c1, '可见返利对象为投保人，能提示对象条件；机构销售费机制被截断，不能扩张套用。', True),
     (2, q23c2, '片段分列投保人利益和无资质机构销售費，支持核对来源方角色但不直接定性。', False)])
save()

def verify():
    saved = [json.loads(line) for line in OUT.read_text(encoding='utf-8').splitlines()]
    expected_pairs = [r['pair_id'] for r in rows]
    actual_pairs = [j['pair_id'] for j in saved]
    assert len(expected_pairs) == len(set(expected_pairs)) == 24
    assert len(actual_pairs) == len(set(actual_pairs)) == 24
    assert expected_pairs == actual_pairs
    file_keys = {'pair_id', 'help_grade', 'help_type', 'mechanism_match', 'conditions_match',
                 'source_quote', 'reason', 'limitations', 'misleading_risk', 'contexts'}
    context_keys = {'context_id', 'help_grade', 'evidence_quote', 'reason', 'misleading_risk'}
    context_count = positive_files = positive_contexts = flagged_contexts = 0
    quote_audit = []
    for row, judgment in zip(rows, saved):
        assert set(judgment) == file_keys
        assert type(judgment['help_grade']) is int and judgment['help_grade'] in range(4)
        assert judgment['help_type'] in {'support', 'boundary', 'irrelevant'}
        assert judgment['mechanism_match'] in {'same', 'partial', 'different'}
        assert judgment['conditions_match'] in {'compatible', 'partial', 'conflict', 'unknown'}
        assert type(judgment['misleading_risk']) is bool
        assert isinstance(judgment['limitations'], list) and all(isinstance(x, str) for x in judgment['limitations'])
        assert isinstance(judgment['reason'], str) and judgment['reason']
        assert isinstance(judgment['source_quote'], str)
        source_hash = hashlib.sha256(row['full_source_text'].encode('utf-8')).hexdigest()
        assert source_hash == row['source_sha256'], row['pair_id']
        assert [c['context_id'] for c in judgment['contexts']] == [c['context_id'] for c in row['contexts']]
        if judgment['help_grade'] >= 2:
            assert judgment['source_quote'] and judgment['source_quote'] in row['full_source_text']
            positive_files += 1
            quote_audit.append({'pair_id': row['pair_id'], 'context_id': None,
                                'quote_sha256': hashlib.sha256(judgment['source_quote'].encode('utf-8')).hexdigest()})
        for original, result in zip(row['contexts'], judgment['contexts']):
            assert set(result) == context_keys
            assert type(result['help_grade']) is int and result['help_grade'] in range(4)
            assert type(result['misleading_risk']) is bool
            assert isinstance(result['reason'], str) and result['reason']
            assert isinstance(result['evidence_quote'], str)
            context_count += 1
            flagged_contexts += result['misleading_risk']
            if result['help_grade'] >= 2:
                assert result['evidence_quote'] and result['evidence_quote'] in original['text']
                assert result['evidence_quote'] in row['full_source_text']
                positive_contexts += 1
                quote_audit.append({'pair_id': row['pair_id'], 'context_id': original['context_id'],
                                    'quote_sha256': hashlib.sha256(result['evidence_quote'].encode('utf-8')).hexdigest()})
    expected_contexts = [c['context_id'] for row in rows for c in row['contexts']]
    assert len(expected_contexts) == len(set(expected_contexts)) == context_count
    grade_counts = {grade: sum(j['help_grade'] == grade for j in saved) for grade in range(4)}
    context_grades = {grade: sum(c['help_grade'] == grade for j in saved for c in j['contexts']) for grade in range(4)}
    notes = [
        '# 独立隐藏算法帮助度评分记录',
        '',
        '本次为模型独立判读的一致性核验，不是人工验收。评分时不知道初始分值。',
        '评估材料仅使用 judging_instructions.md 与 independent_audit_pool.jsonl；未读取初始评分、provenance、retrieval_results、queries、其他任务进展或已知正例，未联网或调用付费 API。',
        '模型逐条阅读24个 query、完整原文及其返回片段后形成评分，脚本仅保存已判断结果并做格式和引文校验。每8条落盘。',
        '',
        f'- 样本覆盖：24/24，唯一 pair_id：24；片段覆盖：{context_count}/{context_count}，context_id 无重复。',
        f'- 文件等级分布：{json.dumps(grade_counts, ensure_ascii=False)}。',
        f'- 片段等级分布：{json.dumps(context_grades, ensure_ascii=False)}。',
        f'- 文件等级≥2：{positive_files}；片段等级≥2：{positive_contexts}；片段误导风险：{flagged_contexts}。',
        '- 字段、枚举、整数0..3、ID全集与顺序检查通过。',
        '- 所有源文本 SHA-256 与池中 source_sha256 一致；所有2/3分判定的连续引文在原文中精确存在，片段2/3分引文同时存在于 context.text 和 full_source_text。',
        '- 边界案例不据相似处罚推定输入违规，也不据相反条件证明输入合规。宽泛销售误导或培训误导均未替代具体机制证据。',
        '- 片段风险标记：职业责任险日期截断；准备金片段仅呈申辩而遗漏监管驳回；来源方返利片段截断机构费用机制。',
        '',
        f'池文件 SHA-256：`{hashlib.sha256(POOL.read_bytes()).hexdigest()}`',
        f'判定文件 SHA-256：`{hashlib.sha256(OUT.read_bytes()).hexdigest()}`',
        '',
        '2/3分引文 SHA-256（按UTF-8原样编码）：',
        '',
        '| pair_id | context_id（空为文件） | 引文 SHA-256 |',
        '|---|---|---|',
    ]
    notes.extend(f'| {q["pair_id"]} | {q["context_id"] or ""} | {q["quote_sha256"]} |' for q in quote_audit)
    (ROOT / 'independent_audit_notes.md').write_text('\n'.join(notes) + '\n', encoding='utf-8')
    print(json.dumps({'verified_pairs': len(saved), 'verified_contexts': context_count,
                      'positive_files': positive_files, 'positive_contexts': positive_contexts,
                      'context_flags': flagged_contexts, 'file_grades': grade_counts,
                      'context_grades': context_grades,
                      'output_sha256': hashlib.sha256(OUT.read_bytes()).hexdigest()}, ensure_ascii=False))

verify()
