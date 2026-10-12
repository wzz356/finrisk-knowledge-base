import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[3]
def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
if __name__ == '__main__':
    idx = [json.loads(s) for s in (ROOT / 'finrisk-knowledge-base/data/file_index.jsonl').read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    early = [x for x in idx if x.get('batch') == 'early30']
    print('INDEX_COUNT', len(idx), 'EARLY30', len(early))
    for p in [early[0]['candidate'],early[0]['source']]:
        env=json.loads((ROOT/'finrisk-knowledge-base'/p['path']).read_text(encoding='utf-8-sig').splitlines()[p['line']-1])
        print('ENVELOPE',p,'KEYS',list(env))
        print(json.dumps(env,ensure_ascii=False)[:1700])
    q = read('outputs/FinRisk_剩余全量运行_v2_20261011/reports/质量验收_20261012/定向复核工作队列_v2.json')
    print('QUEUE_TYPE', type(q).__name__)
    if isinstance(q, dict):
        print('QUEUE_KEYS', list(q))
        for k,v in q.items():
            print(k, ('len='+str(len(v))) if isinstance(v,list) else json.dumps(v,ensure_ascii=False)[:1400])
            if isinstance(v,list):
                for x in v[:1]: print(json.dumps(x, ensure_ascii=False))
    else:
        print('QUEUE_LENGTH',len(q))
        for x in q[:3]: print(json.dumps(x,ensure_ascii=False))
    print('SIGNAL_COUNTS',Counter(s['code'] for x in q['records'] for s in x['signals']))
    for x in q['records']:
        codes=[s['code'] for s in x['signals']]
        if any(c not in ['LEGAL_REFS_EMPTY_WITH_QUOTED_LAW','DATE_EMPTY_WITH_SOURCE_DATE','MONEY_EMPTY_WITH_SOURCE_MONEY'] for c in codes):
            print(json.dumps(x,ensure_ascii=False))
            if sum(1 for _ in []): pass
