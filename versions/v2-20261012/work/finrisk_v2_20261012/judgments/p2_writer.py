import json,pathlib,hashlib
root=pathlib.Path('work/finrisk_v2_20261012/judgments')
rows=[json.loads(x) for x in pathlib.Path('outputs/FinRisk_知识库V2_20261012/evaluation/same8509_pool/judgment_part_2.jsonl').read_text(encoding='utf-8-sig').splitlines()]
out=root/'same8509_p2.jsonl'
def c(g,q,r,m=False): return dict(help_grade=g,evidence_quote=q,reason=r,misleading_risk=m)
def f(g,t,mm,cm,q,r,ls=[],m=False):return dict(help_grade=g,help_type=t,mechanism_match=mm,conditions_match=cm,source_quote=q,reason=r,limitations=ls,misleading_risk=m)
def save(i,cs,ff=None):
 x=rows[i];d={'pair_id':x['pair_id']}
 if x['needs_file_judgment']:
  assert ff is not None; d.update(ff)
 else: assert ff is None
 assert len(cs)==len(x['contexts'])
 for z,y in zip(cs,x['contexts']):
  z['context_id']=y['context_id'];q=z['evidence_quote'];assert q in y['text'] and q in x['full_source_text'];assert z['help_grade']<2 or q
 d['contexts']=cs
 if ff:
  assert ff['source_quote'] in x['full_source_text'];assert ff['help_grade']<2 or ff['source_quote']
 with out.open('a',encoding='utf-8') as w:w.write(json.dumps(d,ensure_ascii=False)+'\n')
 print(i,'saved')
