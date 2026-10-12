import json,sys,hashlib,collections
from pathlib import Path
BASE=Path(__file__).parent
ROWS=[json.loads(x) for x in (BASE/'judgment_part_3.jsonl').read_text(encoding='utf-8').splitlines()]
OUT=BASE/'judgments_part_3.jsonl'

def show(q,start=0,n=6):
 rs=[r for r in ROWS if r['query_id']==q]
 done={json.loads(x)['pair_id'] for x in OUT.read_text(encoding='utf-8').splitlines()} if OUT.exists() else set()
 seen={r['source_sha256'] for r in ROWS if r['pair_id'] in done}
 print('QUERY',q,rs[0]['query_text'])
 for i,r in enumerate(rs[start:start+n],start):
  print('\nITEM',i,r['pair_id'],r['file_id'])
  if r['source_sha256'] in seen:print('SOURCE: 同一完整原文此前已逐字读过',r['file_id'])
  else:print('SOURCE:',r['full_source_text']);seen.add(r['source_sha256'])
  for j,c in enumerate(r['contexts']): print('CONTEXT',j,c['context_id'],repr(c['text']))

def append(q,decisions):
 rs=[r for r in ROWS if r['query_id']==q]
 existing=[json.loads(x) for x in OUT.read_text(encoding='utf-8').splitlines()] if OUT.exists() else []
 ids={x['pair_id'] for x in existing}
 for i,g,typ,mm,cm,quote,reason,limits,ctx in decisions:
  r=rs[i]
  assert r['pair_id'] not in ids
  assert g in range(4) and (g<2 or quote and quote in r['full_source_text'])
  assert len(ctx)==len(r['contexts'])
  cr=[]
  for c,(cg,cq,why,*mr) in zip(r['contexts'],ctx):
   assert cg in range(4) and (cg<2 or cq and cq in c['text'] and cq in r['full_source_text']), (r['pair_id'],c['context_id'],cq)
   cr.append(dict(context_id=c['context_id'],help_grade=cg,evidence_quote=cq,reason=why,misleading_risk=bool(mr and mr[0])))
  obj=dict(pair_id=r['pair_id'],help_grade=g,help_type=typ,mechanism_match=mm,conditions_match=cm,source_quote=quote,reason=reason,limitations=limits,misleading_risk=any(c['misleading_risk'] for c in cr),contexts=cr)
  with OUT.open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps(obj,ensure_ascii=False)+'\n')
  ids.add(r['pair_id'])
 print('saved',len(ids))

if __name__=='__main__':show(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 0,int(sys.argv[3]) if len(sys.argv)>3 else 6)
