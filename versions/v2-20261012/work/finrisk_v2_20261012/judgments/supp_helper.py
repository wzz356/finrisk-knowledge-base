import json,pathlib,sys
IN=pathlib.Path("outputs/FinRisk_知识库V2_20261012/evaluation/all_pool/supplemental_pending.jsonl")
OUT=pathlib.Path("work/finrisk_v2_20261012/judgments/all9639_supplemental.jsonl")
DATA=[json.loads(s) for s in IN.read_text(encoding="utf-8").splitlines()]
def show(start,end):
 seen={}
 for i in range(start,end):
  x=DATA[i];s=x['full_source_text'];print(f"\nPAIR {i} {x['pair_id']} filejudge={x['needs_file_judgment']} QUERY: {x['query_text']}")
  if s in seen:print('FULL identical to PAIR',seen[s])
  else:print('FULL:',s);seen[s]=i
  for j,c in enumerate(x['contexts']):
   if c['text'].strip()==s.strip():print(f"CTX {j} {c['context_id']}: identical to FULL")
   else:print(f"CTX {j} {c['context_id']}: {c['text']}")
def save(rows):
 existing=[json.loads(s) for s in OUT.read_text(encoding='utf-8').splitlines()] if OUT.exists() else []
 ids={o['pair_id'] for o in existing}
 for i,f,cs in rows:
  x=DATA[i];o={'pair_id':x['pair_id']}
  if x['needs_file_judgment']:
   g,q,r,t,m,c,l=f;o.update(help_grade=g,source_quote=q,reason=r,help_type=t,mechanism_match=m,conditions_match=c,limitations=l,misleading_risk=False)
   assert g<2 or q and q in x['full_source_text'],(i,'file',q)
  assert len(cs)==len(x['contexts'])
  o['contexts']=[]
  for raw,c in zip(cs,x['contexts']):
   g,q,r,*flag=raw;assert g<2 or q and q in c['text'] and q in x['full_source_text'],(i,'ctx',q)
   o['contexts'].append(dict(context_id=c['context_id'],help_grade=g,evidence_quote=q,reason=r,misleading_risk=bool(flag and flag[0])))
  assert o['pair_id'] not in ids;ids.add(o['pair_id']);existing.append(o)
 OUT.write_text(''.join(json.dumps(o,ensure_ascii=False)+'\n' for o in existing),encoding='utf-8');print('saved',len(existing))
if __name__=='__main__':show(int(sys.argv[1]),int(sys.argv[2]))
