"""定位原文事实用于构造问题；不检索新问题、不使用答案定制模型。"""
import random,re
from common import *
sources=rows(SOURCE);assert len(sources)==9639
exclude={r['file_id'] for r in rows(ROOT/'outputs/FinRisk_纯官方案例库DeepSeek试跑_20261015/official_reference_cases.jsonl')}
patterns={'dividend':r'保底.{0,18}(收益|分红)|保证.{0,15}收益|基本.{0,5}收益|6%是',
 'deposit':r'把.{0,8}保费.{0,10}(存钱|存款)|混淆保险与储蓄|说成.{0,5}存钱|片面比较',
 'surrender':r'退保.{0,15}(损失|本金)|本金.{0,12}(损失|领取)|中途.{0,10}(取出|领取)',
 'coverage':r'夸大保险责任|夸大.{0,5}保障|保险责任.{0,5}不实',
 'scarcity':r'虚构.{0,15}限售|限时限额|虚假.{0,8}停售',
 'gift':r'赠送.{0,15}(礼品|购物卡|油卡)|返还.{0,15}(保费|现金)',
 'identity':r'冒充|银行.{0,10}员工身份|银行工作人员身份',
 'competitor':r'贬低|诋毁|同业公司.{0,10}不实',
 'callback':r'阻碍.{0,10}回访|代.{0,8}回访|篡改.{0,8}电话',
 'signature':r'代.{0,8}签名|代.{0,8}签字|代替投保人.{0,15}风险提示',
 'finance':r'虚列.{0,15}(宣传费|费用)|套取.{0,8}资金',
 'qualification':r'未取得.{0,15}资格.{0,12}(保险|营销)|无资格证|不具有.{0,8}资质'}
found={}
for key,pat in patterns.items():
 hits=[]
 for d in sources:
  if d['official_file_id'] in exclude:continue
  matches=list(re.finditer(pat,d['full_text']))
  if matches:
   p=matches[0];hits.append({'file_id':d['official_file_id'],'title':d['full_text'].splitlines()[0],
    'match':p.group(),'context':d['full_text'][max(0,p.start()-120):min(len(d['full_text']),p.end()+440)],'chars':len(d['full_text'])})
 random.Random('finrisk-evalset-20261015-'+key).shuffle(hits);found[key]={'count':len(hits),'candidates':hits[:4]}
save('source_exploration.json',found)
for key,value in found.items():print(json.dumps({'group':key,**value},ensure_ascii=False))
