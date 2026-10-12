import json, sys, hashlib
from pathlib import Path
BASE=Path(__file__).parent
SRC=BASE/'judgment_part_2.jsonl'
OUT=BASE/'judgments_part_2.jsonl'
DATA=[json.loads(x) for x in SRC.read_text(encoding='utf-8').splitlines() if x]

if sys.argv[1]=='show':
    start,end=map(int,sys.argv[2:4])
    for i in range(start,end+1):
        x=DATA[i-1]
        print(f'\n===== {i} {x["pair_id"]} {x["query_id"]} =====')
        print('QUERY:',x['query_text'])
        prior=next((k+1 for k,y in enumerate(DATA[:i-1]) if y['full_source_text']==x['full_source_text']),None)
        if prior: print(f'FULL: 与已显示并阅读的第{prior}条完整原文逐字符相同；',x['full_source_text'].splitlines()[0])
        else: print('FULL:',x['full_source_text'])
        for j,c in enumerate(x['contexts']):
            print(f'CONTEXT {j}: {c["context_id"]}\n{c["text"]}')
elif sys.argv[1]=='append':
    specs=json.loads(sys.stdin.read())
    rows=[]
    for s in specs:
        i,g,t,m,c,q,r,lim,cs=s
        x=DATA[i-1]
        assert len(cs)==len(x['contexts']), (i,len(cs),len(x['contexts']))
        assert q in x['full_source_text'], (i,q)
        row={'pair_id':x['pair_id'],'help_grade':g,'help_type':t,'mechanism_match':m,'conditions_match':c,'source_quote':q,'reason':r,'limitations':lim,'misleading_risk':False,'contexts':[]}
        for k,(cg,cq,cr,*extra) in enumerate(cs):
            ctx=x['contexts'][k]
            assert cq in ctx['text'],(i,k,cq)
            if cg>=2: assert cq and cq in x['full_source_text'],(i,k,cq)
            row['contexts'].append({'context_id':ctx['context_id'],'help_grade':cg,'evidence_quote':cq,'reason':cr,'misleading_risk':bool(extra and extra[0])})
        rows.append(row)
    old=[json.loads(l) for l in OUT.read_text(encoding='utf-8').splitlines()] if OUT.exists() else []
    assert not (set(x['pair_id'] for x in rows)&set(x['pair_id'] for x in old))
    with OUT.open('a',encoding='utf-8',newline='\n') as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
    print('saved',len(rows),'total',len(old)+len(rows))
elif sys.argv[1]=='check':
    rows=[json.loads(l) for l in OUT.read_text(encoding='utf-8').splitlines() if l]
    assert len(rows)==len(DATA)
    lookup={x['pair_id']:x for x in DATA}
    assert len({x['pair_id'] for x in rows})==len(DATA)
    assert set(x['pair_id'] for x in rows)==set(lookup)
    count=0
    observed=set()
    expected={(x['pair_id'],c['context_id']) for x in DATA for c in x['contexts']}
    for r in rows:
        x=lookup[r['pair_id']]
        assert set(r)=={'pair_id','help_grade','help_type','mechanism_match','conditions_match','source_quote','reason','limitations','misleading_risk','contexts'}
        assert type(r['pair_id']) is str and type(r['contexts']) is list
        assert type(r['help_grade']) is int and r['help_grade'] in range(4)
        assert r['help_type'] in ['support','boundary','irrelevant']
        assert r['mechanism_match'] in ['same','partial','different']
        assert r['conditions_match'] in ['compatible','partial','conflict','unknown']
        assert type(r['limitations']) is list and all(type(t) is str for t in r['limitations'])
        assert type(r['misleading_risk']) is bool
        assert type(r['reason']) is str and type(r['source_quote']) is str
        if r['source_quote']: assert r['source_quote'] in x['full_source_text']
        if r['help_grade']>=2: assert r['source_quote'] and r['source_quote'] in x['full_source_text']
        ids=[c['context_id'] for c in r['contexts']]
        assert len(ids)==len(set(ids)) and set(ids)==set(c['context_id'] for c in x['contexts'])
        cl={c['context_id']:c for c in x['contexts']}
        for c in r['contexts']:
            assert set(c)=={'context_id','help_grade','evidence_quote','reason','misleading_risk'}
            assert type(c['context_id']) is str
            key=(r['pair_id'],c['context_id'])
            assert key not in observed
            observed.add(key)
            assert type(c['help_grade']) is int and c['help_grade'] in range(4)
            assert type(c['reason']) is str and type(c['evidence_quote']) is str and type(c['misleading_risk']) is bool
            if c['evidence_quote']: assert c['evidence_quote'] in cl[c['context_id']]['text'] and c['evidence_quote'] in x['full_source_text']
            if c['help_grade']>=2: assert c['evidence_quote'] and c['evidence_quote'] in cl[c['context_id']]['text'] and c['evidence_quote'] in x['full_source_text']
            count+=1
    assert observed==expected and count==sum(len(x['contexts']) for x in DATA)
    print(json.dumps({'pairs':len(rows),'contexts':count,'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()},ensure_ascii=False))
