"""Authored interpretations with exact official-reader spans, never current facts."""
import json
from source_registry import ROOT, OUT, save, sha


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def aid(source, number):
    return f'L{source:03}-A{number:04}'


# Each pair is a substantive condition card and its boundary card, authored before new queries.
# Text in these tuples is interpretation, not quotation or a finding about any customer.
SPECS = [
('M01', '如实回访及指导答复', 'obligation_interpretation', ['L002-A0035','L005-A0011','L005-A0016','L005-A0025'],
 ['当前对象是否属于监管要求回访的保险产品','是否指导投保人对实际未获说明的事项作已知悉的答复'],
 '回访应核实真实知悉和身份；指导作虚假答复会破坏该目的。第35条直接约束保险公司回访职责；销售人员诱导行为的专项认定指引仍待核全文。',
 '回访违规', '不得把回访义务条文冒充逐字规定所有人员诱导行为的专项条文'),
('M01', '真实理解辅助及合理简化', 'scope_guard', ['L002-A0035','L005-A0011'],
 ['是帮助理解后按实际情况答复还是预设虚假答案','是否满足已实施可回溯管理且有关信息已确认等简化条件'],
 '解释名词、预约和要求如实反馈不等于诱导不实回答；合理简化须符合监管条件，不能靠销售人员自行免除。',
 '回访违规', '未出现完整回访脚本不等于未履行全部回访义务'),
('M02', '回访身份真实性', 'obligation_interpretation', ['L002-A0035','L005-A0016'],
 ['实际接听和作出本人答复的人是否为投保人','是否让非本人冒称投保人完成身份及知悉确认'],
 '回访包含身份真实性确认。明示要求同事冒称投保人属风险筛查线索；不能据此补写冒名已经成功。',
 '回访违规', '不能把风险话术写成已实施冒名或伪造录音的事实'),
('M02', '透明辅助与冒充的区别', 'interpretation_guard', ['L002-A0035'],
 ['辅助者是否公开真实身份且不替投保人作本人确认','投保人是否实际完成必要的身份及知悉答复'],
 '透明预约、转接或翻译辅助本身不等于冒名；是否允许具体辅助仍须核回访制度，不能推成任意代理均被允许。',
 '回访违规', '身份、答复人未知时不能仅因他人接起电话判定冒名'),
('M03', '绝对避债避税宣传', 'prohibition_interpretation', ['L002-A0017','L008-A0538','L008-A0539','L009-A0004'],
 ['销售表述是否作无条件覆盖一切债务或税种的承诺','所称利益是否确为相应法律规则覆盖的保险赔款或财产处置'],
 '虚假、夸大或隐去条件的法律效果宣传有风险；撤销权和保险赔款免税条文不能推出所有保单免执行或所有收益免税。',
 '避债避税', '不得替法院、税务机关作个案最终结论，也不能补写未来税制'),
('M03', '有限法律税务说明', 'interpretation_guard', ['L008-A0538','L008-A0539','L008-A0540','L008-A0541','L008-A0542','L009-A0004'],
 ['是否保留请求撤销的构成、期限及具体处置等条件','是否将个人所得税法保险赔款免税限定于其条文对象'],
 '有条件说明不当然构成避债避税宣传；具体保险给付及财产类型仍需个案核实。不能反向认定所有投保都必须撤销。',
 '避债避税', '未给法律适用细节不等于已经违反税法或已被强制执行'),
('M04', '合同外成交利益', 'prohibition', ['L001-A0116','L001-A0131'],
 ['承诺利益是否给投保人、被保险人或受益人','是否为保险合同约定外的保费回扣或其他利益'],
 '分别按公司及工作人员、代理经纪主体适用条文。承诺本身可触发筛查，不必等待实际兑现；不能略过利益对象和合同内外。',
 '合同外利益', '出现礼品、奖金字样不自动证明合同外利益'),
('M04', '合同权益与活动边界', 'interpretation_guard', ['L001-A0116','L001-A0131'],
 ['利益是否已经明确列入真实有效的保险合同','活动是否与投保成交绑定且对象是否为法条所列当事人'],
 '合同约定的给付、已归属红利及不与投保绑定的正常活动不能仅凭赠送表述套用合同外利益；未知时核合同和活动规则。',
 '合同外利益', '销售人员口称公司活动不能证明它是合同权益'),
('M05', '非保证利益不得保证化', 'prohibition_interpretation', ['L002-A0022','L003-A0013','L003-A0037','L005-A0008','L005-A0012'],
 ['被承诺部分是否为未来分红或高于最低保证的万能收益','话术是否将该不确定部分承诺为固定、必得或不受经营结果影响'],
 '分红未来非保证、万能超过最低保证利率的部分不确定；真实已归属利益与未来收益须分开，不读取旧演示利率数字为当前标准。',
 '保证收益', '不能从有保证二字推定所有收益表述违规'),
('M05', '合同保证对象与期间', 'scope_guard', ['L007-S01-I01','L005-A0007','L005-A0012'],
 ['合同所保证的是账户价值、保险金还是全部已交保费','保证利率是否有保证期间及期满调整条款'],
 '万能最低保证针对保单账户价值，可能设置保证期间；依法依约说明确实的保证部分不等于承诺未来非保证收益。',
 '保证收益', '不得把账户价值最低保证扩成全部保费无损或永久固定收益'),
('M06', '明示保险及避免产品混同', 'prohibition', ['L002-A0017','L002-A0025','L003-A0013'],
 ['实际推介对象是否为保险产品','是否把其直接表述成银行存款或混淆产品性质'],
 '销售宣传须明示保险；适当性告知不得混淆存款、理财、基金、信托、保险等产品。银行渠道不改变保险产品性质。',
 '销售误导', '不得从银行网点或银行员工自动推出所售产品是存款'),
('M06', '比较与准确解释边界', 'scope_guard', ['L005-A0006','L005-A0029','L002-A0017'],
 ['是在说明产品差异还是将保险等同存款','是否作规则所禁的与存款等收益简单比较或误导宣传'],
 '准确解释保险与存款差异不自动等于不当比较；一年期以上人身保险产品规则有其范围，比较仍需完整条件。',
 '销售误导', '不能因一句同时出现保险与存款就判为混同'),
('M07', '退保损失与告知', 'obligation', ['L002-A0025','L003-A0037','L005-A0007'],
 ['所述退保发生于犹豫期、普通退保还是特殊约定情形','已知现金价值及费用是否与随时原额退回等表述矛盾'],
 '提示退保、费用和现金价值；不能对明知存在的普通提前退保损失作无损承诺。拟议误导可预警，不必等待客户实际退保。',
 '隐瞒重要信息', '不能凭一段节选没有提退保就断言全流程隐瞒'),
('M07', '犹豫期与特殊退款条件', 'interpretation_guard', ['L005-A0007','L005-A0012','L003-A0037'],
 ['退款说明是否限定真实合同所定犹豫期及相应条件','是否已知可全退的特殊依据，还是时点与扣费未知'],
 '犹豫期和已证实特殊退款与普通退保区分。具体全退或扣费必须从本次合同事实判断，法规一般要求不能替代产品事实。',
 '隐瞒重要信息', '不得自行编造统一犹豫期天数、统一退费率或当前现金价值'),
('M08', '保障与免责说明', 'obligation', ['L001-A0017','L002-A0025','L002-A0026','L003-A0037'],
 ['本次合同是否对保障、等待期、免赔额或比例给付设有限制','宣传是否与已知责任条款矛盾，或明确要求故意隐去重要限制'],
 '格式条款应提供并作提示；免责、免赔额、免赔率、比例赔付等须解释。具体责任由本次真实合同支撑，不能从旧案例补齐。',
 '销售误导', '不得把需要核实合同写成已确定不赔或无条件理赔'),
('M08', '范围与信息片段边界', 'scope_guard', ['L004-A0029','L002-A0025','L002-A0026'],
 ['引用的是保险法及销售规则还是排除团体人身保险的特定披露办法','是否满足同公司同产品三个月内重复投保、简单条款及同意等简化提示条件'],
 '人身保险产品信息披露管理办法不适用团体人身保险；不因此免除其他法律及销售说明责任。简化提示不是允许隐瞒重要条款。',
 '销售误导', '不能把特定办法不适用推成一切免责提示义务不存在'),
('M09', '停售调价公告条件', 'prohibition', ['L002-A0019'],
 ['保险销售人员是否宣称对应产品即将停售或调价','公司是否已发布对应名称和起始日期的公告，以及是否属于条文公告例外'],
 '公司未公告前销售人员不得宣称该产品即将停售调价；没有在输入附公告不等于公司没有公告。真实公告也不豁免其他虚假表述。',
 '虚假宣传', '不得把缺公告材料直接当未发布公告的事实'),
('M09', '虚构限额及真实活动', 'prohibition_interpretation', ['L002-A0017','L010-A0002','L010-A0004','L010-A0028'],
 ['是否存在真实且对应产品、日期和渠道的配额依据','是在商业广告或销售宣传中明确编造稀缺条件，还是仅据真实公告说明'],
 '虚构配额属于真实性问题，不必硬套停售条文；广告法先核商业广告范围。对真实公告准确说明不一概判为违规。',
 '虚假宣传', '不能从销售名额少推导监管强制停售'),
('M10', '无资格机构受托实际销售', 'prohibition', ['L001-A0116','L001-A0119','L002-A0002','L002-A0003','L002-A0005'],
 ['受托机构是否具备实际保险代理或经纪等所需资格','实际职责是否含具体产品推介、条款商谈或促成保险合同等销售行为'],
 '不得委托未取得合法资格机构从事保险销售；分清机构许可和销售人员执业登记，客户同意不代替法定资格。',
 '委托无资质机构销售', '不得把申请许可中说成已取得许可'),
('M10', '转介场务与销售的区别', 'interpretation_guard', ['L002-A0002','L002-A0003','L002-A0005'],
 ['服务方是否仅提供场务技术服务或合规转介，不作具体产品推介与商谈','实际行为、委托内容及资格是否足够明确'],
 '纯服务与实际销售须按行为识别；仅称合作或转介不能证明合法，也不能仅凭外包就断言其无资格销售。',
 '委托无资质机构销售', '资格和实际行为均未知时不得推定无证销售已经成立'),
('M11', '订立合同本人确认与真实记录', 'prohibition', ['L002-A0029','L002-A0033','L005-A0004','L005-A0017'],
 ['材料是否属于订立保险合同的投保声明等确认文书','销售人员是否代替相关当事人确认或提交虚假的本人确认记录'],
 '订立合同相关文书保险销售人员不得代确认；业务和当事人信息应如实提供。万能产品风险告知另有不得误导代操作要求。',
 '客户信息不真实', '不能将销售人员口述帮助自动认定为伪造签名已经完成'),
('M11', '允许协助和授权范围', 'scope_guard', ['L002-A0029','L002-A0033'],
 ['是否为客户真实自主确认或非销售人员的合法书面委托确认','是否将订立合同专门规定不当地泛用于所有保全变更'],
 '条文允许投保人或其书面委托人员确认，同时禁止保险销售人员代确认；不能用笼统授权绕开销售人员限制。保全变更须另核依据。',
 '客户信息不真实', '未知实际操作者、授权及环节时不能确定已伪造本人确认'),
('M12', '取消后停止商业营销', 'obligation', ['L006-A0024'],
 ['电话是否为商业营销，是否取得同意或请求','消费者是否已明确取消且后续仍拟议或实际向其营销'],
 '商业信息或电话需同意或请求，提供明确便捷取消方式；取消后立即停止，过去的同意不当然覆盖撤回以后。',
 '电销违规', '不得把曾经咨询等同永久同意电话推销'),
('M12', '必要服务与营销区分', 'interpretation_guard', ['L006-A0024','L002-A0005'],
 ['联系是否为履行已有保单必要服务且不夹带营销','取消范围、电话目的及是否推销是否明确'],
 '取消营销不自动禁止一切必要服务联系；标为服务也不改变实质推销性质。目的及同意未知时先核实。',
 '电销违规', '不能仅因出现电话或拒接就判定商业电话违法'),
]


def dependency_closure(primary, dependencies):
    if any(i not in dependencies for i in primary):
        raise ValueError('unregistered article ID')
    seen, queue = set(), list(primary)
    while queue:
        item = queue.pop(0)
        if item not in dependencies:
            raise ValueError('unregistered dependency')
        if item not in seen:
            seen.add(item)
            queue.extend(dependencies[item])
    return sorted(seen)


def span(article, start=0, end=None):
    end = len(article['text']) if end is None else end
    return dict(article_id=article['article_id'], version_id=article['version_id'],
                start=start, end=end, quote=article['text'][start:end],
                source_start=article['start']+start, source_end=article['start']+end)


def build():
    articles = {r['article_id']:r for r in rows(OUT/'articles.jsonl')}
    dependencies = {key:[] for key in articles}
    for key in articles:
        sid = articles[key]['source_id']
        deps = {'L002':[aid(2,2),aid(2,5)], 'L003':[aid(3,3),aid(3,47),aid(3,49)],
                'L004':[aid(4,29),aid(4,31)],'L005':[aid(5,29),aid(5,30)]}.get(sid, [])
        dependencies[key] = [i for i in deps if i != key]
    additions = {aid(3,12):[aid(3,38)], aid(3,35):[aid(3,n) for n in [34,36,38,39,40]],
                 aid(3,36):[aid(3,n) for n in [34,35,40]], aid(3,13):[aid(3,12),aid(3,38),aid(3,40)],
                 aid(3,37):[aid(3,40)],aid(2,22):[aid(3,40)],aid(5,17):[aid(5,4)]}
    for key, deps in additions.items():
        dependencies[key] = list(dict.fromkeys(dependencies[key]+deps))
    views = []
    for key, article in articles.items():
        if key in [aid(5,8),aid(5,12),aid(5,19)]:
            # Keep qualitative opening/risks and the complete withdrawal section as separate exact excerpts.
            end = article['text'].index('(四)利益演示')
            tail = article['text'].index('(五)犹豫期及退保')
            spans = [span(article,0,end),span(article,tail)]
            reason = '本轮未核最新利益演示数值规则，整段利益演示暂不向判别模型提供；完整历史版本仍可回源。'
        else:
            spans, reason = [span(article)], None
        views.append(dict(article_id=key,version_id=article['version_id'],spans=spans,
                          partial=reason is not None,withheld_reason=reason))
    rules, links, tags, review = [], [], [], []
    vm = {v['article_id']:v for v in views}
    for index, spec in enumerate(SPECS):
        mech,title,norm,refs,conditions,interpretation,tag,forbidden = spec
        rule_id = f'{mech}-R{index%2+1:02}'
        supports = [s for key in refs for s in vm[key]['spans']]
        rules.append(dict(rule_id=rule_id,mechanism_id=mech,title=title,norm_type=norm,
             article_refs=refs, dependency_refs=dependency_closure(refs,dependencies),
             subjects='以各条文所列保险公司、中介、销售人员或经营者为准；不能互换主体',
             products='核产品性质、期限、个人或团体及本条范围',channels='核实际销售宣传、回访、订立或商业电话环节',
             conditions=[dict(condition_id=f'{rule_id}-C{i+1}',description=value,
                              support_article_refs=refs,role='需从当前输入核实的事实维度，非本次事实断言')
                         for i,value in enumerate(conditions)],
             condition_logic='按触发行为AND适用范围核对；所列核实维度不是必须全部为真的关键词判定器',
             exceptions='见同机制边界卡及dependency_refs中的原文；未知条件须保留unknown',
             required_facts=conditions,forbidden_inferences=[forbidden],interpretation=interpretation,
             support_spans=supports,review_status='model_reviewed_research_only',human_approved=False,
             review_identity='当前会话助手，非独立专家',publication_ready=False))
        links.append(dict(mechanism_id=mech,rule_id=rule_id,relation=norm,review_status='model_silver'))
        tags.append(dict(official_tag=tag,rule_id=rule_id,mapping_role='候选关联，满足事实条件后才能定标签'))
        review.append(dict(rule_id=rule_id,reviewer_type='model',human_approved=False,
             result='原文跨度、主体和例外已逐卡核对；效力未核来源只供研究',
             specific_gap=('L011专项认定全文和现行效力未完成；使用一般规则解释' if mech=='M01' else None)))
    data = dict(rules=rules,dependencies=dependencies,model_views=views,
                mechanism_links=links,tag_links=tags,review_log=review)
    validate(data)
    return data


def validate(data):
    articles = {r['article_id']:r for r in rows(OUT/'articles.jsonl')}
    sources = {r['source_id']:r for r in rows(OUT/'sources/texts.jsonl')}
    official = {r['risk_tag'] for r in json.loads((ROOT/'outputs/FinRisk_正式测试集V2_20261017/official_labels.json').read_text(encoding='utf-8-sig'))}
    for r in articles.values():
        if sources[r['source_id']]['text'][r['start']:r['end']] != r['text']:
            raise ValueError('article/source span mismatch')
    ids = [r['rule_id'] for r in data['rules']]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate rules')
    for rule in data['rules']:
        dependency_closure(rule['article_refs'],data['dependencies'])
        for s in rule['support_spans']:
            a = articles[s['article_id']]
            if s['version_id'] != a['version_id'] or not 0 <= s['start'] < s['end'] <= len(a['text']):
                raise ValueError('invalid version or span')
            if a['text'][s['start']:s['end']] != s['quote']:
                raise ValueError('non-exact support quote')
    if any(row['official_tag'] not in official for row in data['tag_links']):
        raise ValueError('invented tag')


if __name__ == '__main__':
    data = build()
    for key, name in [('rules','rules.jsonl'),('model_views','article_model_views.jsonl'),
                      ('mechanism_links','mechanism_rule_links.jsonl'),('tag_links','tag_rule_links.jsonl'),
                      ('review_log','review_log.jsonl')]:
        save(OUT/name,data[key],True)
    save(OUT/'article_dependencies.json',data['dependencies'])
    print(json.dumps(dict(rules=len(data['rules']),conditions=sum(len(r['conditions']) for r in data['rules']),
                         human_reviewed=0,production_active=0),ensure_ascii=False))
