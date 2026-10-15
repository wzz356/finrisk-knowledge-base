"""同一真实Flash服务；参考集标注者看不到本文件或排名。"""
import sys
import common
from common import *
def run(pilot):
 freeze_check();freeze_check('candidate_freeze.json');freeze_check('api_freeze.json')
 assert read(OUT/'export_authorization.json')['explicit_authorized']
 prior=ROOT/'work/finrisk_deepseek_rerank_20261014';common.PRIOR=prior;sys.path.insert(0,str(prior))
 citation=module(ROOT/'work/finrisk_official_only_20261015/citation.py','evalset_API_citation')
 def validate(packet,response):
  try:return citation.validate_completion(packet,response)
  except ValueError as e:
   if '引文未严格绑定' in str(e):raise ValueError('引文不是原unit_text连续原样字串。请source_quote仅摘6—10个连续原字符，选择不含逗号或换行的短词句；不要复述整段，不要把ASCII逗号改成中文逗号。事实、分数和等级仍按原规则判断。') from None
   raise
 engine=module(WORK/'request_engine.py','evalset_request_engine');engine.OUT=OUT;engine.WORK=WORK
 engine.EXPECTED_PAIRS=len(rows(OUT/'score_inputs.jsonl'));engine.validate_completion=validate
 engine.freeze_check=lambda:(freeze_check(),freeze_check('candidate_freeze.json'),freeze_check('api_freeze.json'))
 engine.run(pilot)
if __name__=='__main__':
 if len(sys.argv)!=2 or sys.argv[1] not in ['pilot','run']:raise ValueError('参数只允许pilot/run')
 run(sys.argv[1]=='pilot')
