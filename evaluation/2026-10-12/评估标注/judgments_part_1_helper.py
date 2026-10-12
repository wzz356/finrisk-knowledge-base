import sys,json,pathlib,hashlib
sys.stdout.reconfigure(encoding='utf-8')
D=pathlib.Path(__file__).parent
INPUT=D/'judgment_part_1.jsonl'; OUTPUT=D/'judgments_part_1.jsonl'
rows=[json.loads(s) for s in INPUT.read_text(encoding='utf-8').splitlines()]
def save(specs):
 result=[]
 for s in specs:
  i,g,t,m,k,q,reason,limits,cs,*rest=s; r=rows[i]
  assert len(cs)==len(r['contexts']),i
  assert not q or q in r['full_source_text'],(i,q)
  cc=[]
  for c,v in zip(r['contexts'],cs):
   cg,cq,cr,*risk=v
   assert not cq or cq in c['text'] and cq in r['full_source_text'],(i,cq)
   cc.append(dict(context_id=c['context_id'],help_grade=cg,evidence_quote=cq,reason=cr,misleading_risk=bool(risk and risk[0])))
  result.append(dict(pair_id=r['pair_id'],help_grade=g,help_type=t,mechanism_match=m,conditions_match=k,source_quote=q,reason=reason,limitations=limits,misleading_risk=bool(rest and rest[0]),contexts=cc))
 existing=[] if not OUTPUT.exists() else [json.loads(s) for s in OUTPUT.read_text(encoding='utf-8').splitlines()]
 ids={r['pair_id'] for r in existing}
 assert not any(r['pair_id'] in ids for r in result)
 with OUTPUT.open('a',encoding='utf-8',newline='\n') as f:
  for r in result:f.write(json.dumps(r,ensure_ascii=False)+'\n')
 print('已保存',len(existing)+len(result))
def show(start,n=5):
 for i in range(start,min(start+n,len(rows))):
  r=rows[i]; print('\n===',i,r['pair_id'],r['query_id'],'===\n查询:',r['query_text'],'\n原文:\n'+r['full_source_text'])
  for j,c in enumerate(r['contexts']): print('上下文',j,c['context_id'],':\n'+c['text'])
if __name__=='__main__':show(int(sys.argv[1]),int(sys.argv[2]) if len(sys.argv)>2 else 5)
