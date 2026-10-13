"""Render existing actual return text and model grades, never assign judgments."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[2]/'outputs/FinRisk_E02小批量实验_20261013'
DATA={(r['query_id'],r['arm']):r for r in [json.loads(s) for s in (OUT/'evaluation/per_query_metrics.jsonl').read_text(encoding='utf-8').splitlines()]}


def quote(text):return '\n'.join('> '+s for s in text.splitlines())


def show(qid,arm,fid):
    h=next(h for h in DATA[(qid,arm)]['top5'] if h['file_id']==fid)
    return f"**{arm}第{h['rank']}位，{fid}，片段{h['context_help_grade']}分，模型警示{h['context_misleading_risk']}。**\n\n实际返回：\n\n{quote(h['returned_hit']['text'])}\n\n本轮判断：{h['context_reason']}\n"


parts=['# E02样例对比\n\n以下原话来自实际Top5结果，0–3分与警示为本轮模型意见，非人工金标。背景字段标签为派生说明，标签后的内容是有区间支持的原文摘录。不同阶段旧评分不替换本轮分数。\n']
cases=[
 ('C007','F003464','F003464','P2','从泛案由补到具体事实，但未增加有用位置','P0已能提示合同内/外边界，因此2分；P2增加具体批单、书面承诺与本金事实，升3分。它有助核实“写进合同”的真实性，不能认定当前合同内兑现违规；两者都跨有用阈值，故有用总数不变。'),
 ('C001','F006493','F006493','P2','补文书身份，减少个人实施误用风险','补公司与个人共同当事人，仍保留不实优惠/中奖这个与真实赠券不同的机制。新背景没有把全部事实排他归给个人，模型主体警示由true变false；片段帮助仍2分。'),
 ('C002','F004090','F004090','P2','命中行的主体不能当作整张表的主体','原命中13字符，背景对应济南机构行；扩展上下文645字符还含滨州、济宁及个人。新的背景没有明确只针对命中行，模型新增误用警示。摘录真实不等于它能无范围地覆盖父文本，已另记return_scope_hold。'),
 ('Q009','F004155','F004155','P2','部分文书身份与多主体父上下文没有范围围栏','原索引句20字符、两处出现；父文本519字符。前缀只列延安机构和曹爱斌，未提供疾病诊断/给付机制，且可能将其他行销售误导套给这两者，新增模型警示。原unit歧义没有因前缀批准而消失，三方案本题有用仍0/5。'),
 ('Q047','F001345','F002692','P1','一次排序替换带来本轮唯一新增有用位置','P0倒签单及报表结果材料不直接说明当前估损依据变化；P1换入准备金/估损相关的边界核查材料。每题4/5变5/5，是唯一有用数量改善，覆盖率没变。新增返回没有背景，收益发生在排序选择，不是新增背景被模型直接读到。')]
for i,(qid,oldfid,newfid,arm,title,explanation) in enumerate(cases,1):
    parts.extend([f'## {i}. {qid}：{title}\n','输入：'+DATA[(qid,'P0')]['query_text']+'\n',show(qid,'P0',oldfid),show(qid,arm,newfid),'解释：'+explanation+'\n'])
parts.append('## 下一轮最小修正\n\n把背景明确绑定到“索引命中原话+原区间”，再单独列扩展阅读；多主体表按行/案件拆分，不能把单个主体放在整表之上当统一主体。仅文书身份须注明不代表行为归属，多个重复出现位置继续标歧义。修正后先重测这两项，再作新输入确认。本轮未改冻结结果或默认库。\n')
(OUT/'样例对比.md').write_text('\n'.join(parts),encoding='utf-8')
print('5 actual paired examples rendered')
