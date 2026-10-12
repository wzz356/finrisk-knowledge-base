import json,sys,hashlib
from pathlib import Path
from p3reader import rows,OUT
def check(p,r):
 assert type(r['pair_id']) is str and type(r['contexts']) is list
 assert r['pair_id']==p['pair_id']
 assert [c['context_id'] for c in r['contexts']]==[c['context_id'] for c in p['contexts']]
 if p['needs_file_judgment']:
  assert type(r['help_grade']) is int and r['help_grade'] in range(4)
  assert type(r['source_quote']) is str and type(r['reason']) is str and type(r['limitations']) is list
  assert all(type(x) is str for x in r['limitations']) and type(r['misleading_risk']) is bool
  assert r['help_type'] in ['support','boundary','irrelevant']
  assert r['mechanism_match'] in ['same','partial','different']
  assert r['conditions_match'] in ['compatible','partial','conflict','unknown']
  if r['help_grade']>=2: assert r['source_quote'] and r['source_quote'] in p['full_source_text']
 else: assert set(r)=={'pair_id','contexts'}
 for c,d in zip(p['contexts'],r['contexts']):
  assert type(d['help_grade']) is int and d['help_grade'] in range(4) and type(d['misleading_risk']) is bool
  assert type(d['evidence_quote']) is str and type(d['reason']) is str
  if d['help_grade']>=2: assert d['evidence_quote'] and d['evidence_quote'] in c['text'] and d['evidence_quote'] in p['full_source_text'],(p['pair_id'],d['evidence_quote'])
if sys.argv[1]=='verify':
 rr=[json.loads(x) for x in OUT.read_text(encoding='utf-8').splitlines()]
 assert len(rr)==len(rows) and len({r['pair_id'] for r in rr})==len(rows)
 by={p['pair_id']:p for p in rows}
 for r in rr: check(by[r['pair_id']],r)
 result={'pairs':len(rr),'contexts':sum(len(r['contexts']) for r in rr),'file_judgments':sum(p['needs_file_judgment'] for p in rows),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(__import__('p3reader').SRC.read_bytes()).hexdigest(),'model_review':True,'human_review':False,'human_judgment_count':0,'coverage_ids_types_grades_contiguous_quotes':'passed','read_encoding':'UTF-8','encoding_note':'Initial 0..9 CP936 output failed; reread UTF-8 0..9 and separately 5..6 before first judgments. Truncated 172 reread in full before judgment.','forbidden_sources_accessed':False}
 Path(__file__).with_name('p3log.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result))
else:
 data=json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))
 start=int(sys.argv[1]); existing={json.loads(x)['pair_id'] for x in OUT.read_text(encoding='utf-8').splitlines()} if OUT.exists() else set()
 built=[]
 for i,(f,cc) in enumerate(data,start):
  p=rows[i]; assert p['pair_id'] not in existing
  r={'pair_id':p['pair_id']}
  if p['needs_file_judgment']:
   g,t,m,c,q,reason,limits=f
   r.update(help_grade=g,help_type=t,mechanism_match=m,conditions_match=c,source_quote=q,reason=reason,limitations=limits,misleading_risk=False)
  else: assert f is None
  assert len(cc)==len(p['contexts'])
  r['contexts']=[dict(context_id=c['context_id'],help_grade=d[0],evidence_quote=d[1],reason=d[2],misleading_risk=d[3] if len(d)>3 else False) for c,d in zip(p['contexts'],cc)]
  check(p,r); built.append(r)
 with OUT.open('a',encoding='utf-8',newline='\n') as h:
  for r in built:h.write(json.dumps(r,ensure_ascii=False)+'\n')
 print(f'Saved {len(built)}; total {len(existing)+len(built)}')
