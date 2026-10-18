"""Conservative mechanism reading hints, without positive or safe verdicts."""
import re

# These are navigation aliases, not legal elements or classifier labels.
TRIGGERS={
 'M01':[r'回访',r'回答.{0,12}(?:知道|明白|清楚)',r'(?:教|照着).{0,8}(?:回答|答复)'],
 'M02':[r'回访',r'冒充.{0,8}(?:客户|投保人)',r'代(?:接|答).{0,8}(?:电话|回访)'],
 'M03':[r'避债|免税|逃债|债权人|债务|税务|执行财产'],
 'M04':[r'合同.{0,4}(?:之外|以外|外)',r'返还.{0,12}(?:千|百|元|现金)',r'返佣|回扣|赠送|返点'],
 'M05':[r'(?:保证|保底|固定).{0,12}(?:收益|回报|分红|利率)',r'万能|投连|投资连结|分红'],
 'M06':[r'银行存款|理财产品|存款|储蓄|保本理财'],
 'M07':[r'退保|退还保费|取回本金|中途退出'],
 'M08':[r'免责|都能赔|全部赔|全额赔|不赔|保障范围|责任范围|理赔条件'],
 'M09':[r'停售|下架|最后.{0,6}(?:一天|机会|名额)|限额|稀缺'],
 'M10':[r'无资格|没有资格|未取得.{0,8}资格|无牌|合作平台|销售资质|机构.{0,8}销售'],
 'M11':[r'代签|替.{0,8}(?:签名|签字|确认)',r'(?:签名|确认).{0,8}(?:代为|替客户|代签|销售替)',r'签名确认由销售替客户'],
 'M12':[r'退订|取消.{0,8}(?:营销|电话|来电)|别再.{0,8}(?:电话|联系)|拒接|电话营销']}

def _check_ids(values,cards,label):
    if not isinstance(values,(list,tuple)) or any(not isinstance(v,str) or v not in cards for v in values) or len(set(values))!=len(values):raise ValueError('invalid '+label)
    return list(values)

def analyze_coverage(text,available_cards,read_ids=(),checked_ids=()):
    if not isinstance(text,str) or not text.strip():raise ValueError('nonempty current text required')
    if not isinstance(available_cards,dict) or not available_cards or not set(available_cards)<=set(TRIGGERS):raise ValueError('registered mechanism cards required')
    read=_check_ids(read_ids,available_cards,'read IDs');checked=_check_ids(checked_ids,available_cards,'checked IDs')
    matches=[];seen=set()
    for mid in available_cards:
        for pattern in TRIGGERS[mid]:
            for m in re.finditer(pattern,text):
                key=(mid,m.start(),m.end())
                if key not in seen:
                    seen.add(key);matches.append(dict(mechanism_id=mid,start=m.start(),end=m.end(),text=m.group(),identity='reading_trigger_not_fact_or_risk'))
    candidates=sorted({s['mechanism_id'] for s in matches});unmapped=not candidates
    adjacent=sorted({other for mid in candidates for other in available_cards[mid].get('adjacent_mechanism_ids',[]) if other in available_cards}-set(candidates))
    unchecked=sorted(set(candidates)-set(checked))
    return dict(schema='finrisk-mechanism-reading-coverage-v1',candidate_mechanism_ids=candidates,trigger_spans=matches,
        read_mechanism_ids=read,caller_reported_checked_ids=checked,unchecked_candidate_ids=unchecked,
        not_read_candidate_ids=sorted(set(candidates)-set(read)),adjacent_mechanism_hints=adjacent,
        coverage_status='unmapped' if unmapped else ('pending' if unchecked else 'caller_reports_checked'),
        fallback_readable_mechanism_ids=sorted(available_cards) if unmapped else [],
        all_official_labels_covered=False,whole_input_risk_free_supported=False,risk_determined=False,
        current_input_facts_verified=False,checks_origin='caller_reported_not_verified',negation_not_resolved=True,
        limitations=['候选提示不等于风险成立；否定/主体/条件须由判断环节核查','没有触发不等于安全；词表之外存在未映射风险','已读资料不等于已经判断；调用方报告的检查未经本层语义核准'],human_approved=False)
