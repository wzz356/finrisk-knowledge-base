"""Offline replay of saved metrics; no network or credential access."""
import json
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'repro/code'))
from scoring import score_evaluation
from analysis_adapter import group_bootstrap

def load_rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]

refs=load_rows(root/'dataset/reference/expected.jsonl')
mapping=[{**m,'analysis_set':{'main_analysis':'main','boundary_challenge':'boundary'}[m['analysis_set']]} for m in load_rows(root/'dataset/reference/mapping.jsonl')]
preds=load_rows(root/'results/normalized_predictions.jsonl');indexed={(p['query_id'],p['arm']):p for p in preds};byref={r['query_id']:r for r in refs}
report=score_evaluation(refs,mapping,preds)
for split in ('development','holdout'):
    for aset in ('main','boundary'):
        points=[]
        for m in mapping:
            if m['split']!=split or m['analysis_set']!=aset:continue
            q=m['query_id'];o=indexed[q,'old'];n=indexed[q,'new'];state=byref[q]['overall_state']
            points.append(dict(group_id=m['group_id'],old_correct=o['valid'] and o['state']==state,new_correct=n['valid'] and n['state']==state))
        report['strata'][split][aset]['group_bootstrap_accuracy_delta']=group_bootstrap(points)
saved=json.loads((root/'results/metrics.json').read_text(encoding='utf-8-sig'))
if report!=saved:raise ValueError('saved and replayed metrics differ')
print(json.dumps(dict(passed=True,queries=len(mapping),predictions=len(preds),all_metrics_identical=True,network_calls=0),ensure_ascii=False))
