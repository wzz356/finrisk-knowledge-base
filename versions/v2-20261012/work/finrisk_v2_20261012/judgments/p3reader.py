import json,sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
BASE=Path(__file__).resolve().parents[3]
SRC=BASE/'outputs/FinRisk_知识库V2_20261012/evaluation/same8509_pool/judgment_part_3.jsonl'
OUT=Path(__file__).with_name('same8509_p3.jsonl')
rows=[json.loads(x) for x in SRC.read_text(encoding='utf-8').splitlines()]
done={json.loads(x)['pair_id'] for x in OUT.read_text(encoding='utf-8').splitlines()} if OUT.exists() else set()
assert done <= {x['pair_id'] for x in rows}
a=int(sys.argv[1]) if sys.argv[1].isdigit() else 0; b=int(sys.argv[2]) if len(sys.argv)>2 and sys.argv[2].isdigit() else a
for i in range(a,b):
 p=rows[i]
 print(f'\nINDEX {i} ID {p["pair_id"]} DONE {p["pair_id"] in done} FILE {p["needs_file_judgment"]}\nQUERY {p["query_text"]}\nFULLSOURCE\n{p["full_source_text"]}')
 for j,c in enumerate(p['contexts']): print(f'CONTEXT {j} {c["context_id"]}\n{c["text"]}')

