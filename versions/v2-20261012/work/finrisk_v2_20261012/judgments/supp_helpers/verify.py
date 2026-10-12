import sys,json,hashlib,collections,pathlib
sys.path.insert(0,'work/finrisk_v2_20261012/judgments')
from supp_helper import IN,OUT,DATA
raw=OUT.read_bytes(); rows=[json.loads(s) for s in raw.decode('utf-8').splitlines()]
by={x['pair_id']:x for x in DATA}; ids=[x['pair_id'] for x in rows]
assert len(ids)==len(set(ids))==len(DATA)==81
assert set(ids)==set(by)
file_keys={'pair_id','help_grade','help_type','mechanism_match','conditions_match','source_quote','reason','limitations','misleading_risk','contexts'}
context_keys={'context_id','help_grade','evidence_quote','reason','misleading_risk'}
files=contexts=quotes=flags=0; reason_lengths=[]
for o in rows:
 x=by[o['pair_id']]; s=x['full_source_text']
 assert hashlib.sha256(s.encode('utf-8')).hexdigest()==x['source_sha256']
 assert set(o)==(file_keys if x['needs_file_judgment'] else {'pair_id','contexts'})
 if x['needs_file_judgment']:
  files+=1
  assert type(o['help_grade']) is int and o['help_grade'] in range(4)
  assert o['help_type'] in {'support','boundary','irrelevant'}
  assert o['mechanism_match'] in {'same','partial','different'}
  assert o['conditions_match'] in {'compatible','partial','conflict','unknown'}
  assert isinstance(o['limitations'],list) and all(isinstance(v,str) for v in o['limitations'])
  assert type(o['misleading_risk']) is bool
  assert isinstance(o['source_quote'],str) and isinstance(o['reason'],str)
  assert o['help_grade']<2 or o['source_quote'] and o['source_quote'] in s
  if o['source_quote']: assert o['source_quote'] in s; quotes+=1
  reason_lengths.append(len(o['reason']))
 cs={c['context_id']:c for c in x['contexts']}
 assert len(cs)==len(o['contexts'])
 assert {c['context_id'] for c in o['contexts']}==set(cs)
 for c in o['contexts']:
  contexts+=1; assert set(c)==context_keys
  assert type(c['help_grade']) is int and c['help_grade'] in range(4)
  assert type(c['misleading_risk']) is bool
  assert isinstance(c['evidence_quote'],str) and isinstance(c['reason'],str)
  q=c['evidence_quote']; assert c['help_grade']<2 or q and q in cs[c['context_id']]['text'] and q in s
  if q: assert q in cs[c['context_id']]['text'] and q in s; quotes+=1
  flags+=c['misleading_risk']; reason_lengths.append(len(c['reason']))
assert files==79 and contexts==83
assert all(20<=n<=60 for n in reason_lengths),(min(reason_lengths),max(reason_lengths))
report={'status':'passed','input_sha256':hashlib.sha256(IN.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(raw).hexdigest(),'pair_count':len(rows),'file_judgment_count':files,'context_judgment_count':contexts,'exact_quote_checked_count':quotes,'context_misleading_count':flags,'model_review':{'pairs':len(rows),'files':files,'contexts':contexts},'human_judgment_count':0,'paid_api_calls':0,'reason_length_range':[min(reason_lengths),max(reason_lengths)],'input_access':'specified supplemental_pending.jsonl and judging_instructions.md only; helper and own output used for recording and validation'}
p=pathlib.Path('work/finrisk_v2_20261012/judgments/supp_helpers/verification.json'); p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
