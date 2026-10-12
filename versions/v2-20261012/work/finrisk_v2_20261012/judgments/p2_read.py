import json,sys,pathlib
p=pathlib.Path('outputs/FinRisk_知识库V2_20261012/evaluation/same8509_pool/judgment_part_2.jsonl')
r=[json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines()]
seen=set()
a,b=map(int,sys.argv[1:3])
for i,x in enumerate(r):
 if i<a: seen.add(x['source_sha256'])
 if not a<=i<b: continue
 print('\nPAIR',i,x['pair_id'],'NEEDS',x['needs_file_judgment'],'QUERY',x['query_text'])
 if x['source_sha256'] not in seen:
  print('FULL',x['full_source_text']);seen.add(x['source_sha256'])
 else: print('FULL already displayed',x['file_id'])
 for j,c in enumerate(x['contexts']): print('CTX',j,c['context_id'],c['text'])
