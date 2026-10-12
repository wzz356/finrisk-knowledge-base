"""Repair missing own-behavior coverage pointers, never rewrite source facts."""
import copy
import json
import sys
from pathlib import Path
from run_v2 import ROOT,read_rows,canonical,sha_json,save_json
sys.path.insert(0,str(Path(__file__).resolve().parent/'quality'))
from quality_common import get
from check_all import task_for,make_compatibility_validator

def add_missing_bindings(draft,text):
    updated=copy.deepcopy(draft);changes=[]
    cases={c['local_key'] for c in draft['cases']}
    for b in draft['behaviors']:
        key=b['local_key'];quote=b['finding_quote']
        if not quote or quote not in text or b['case_key'] not in cases:raise ValueError('finding/case not source bound')
        if any(key in (c.get('behavior_keys') or []) and quote in c.get('quote','') for c in updated['coverage']):continue
        row={'quote':quote,'classification':'behavior','case_keys':[b['case_key']],'behavior_keys':[key],
             'reason':'回补候选finding_quote与其自身行为的覆盖指针；逐字原文，不追加事实或确认主体实施。'}
        updated['coverage'].append(row)
        changes.append({'field':'coverage','behavior_key':key,'source_quote':quote,
                        'finding':'candidate finding quote lacked its own coverage pointer; facts retained exactly'})
    return updated,changes

def main():
    out=ROOT/'work/finrisk_v2_20261012/quality';target=out/'coverage_binding_overlays.jsonl'
    if target.exists():raise FileExistsError(target)
    checks=read_rows(ROOT/'outputs/FinRisk_知识库V2_20261012/quality/baseline_mechanical/mechanical_checks.jsonl')
    rows=[];results=[];validate=make_compatibility_validator(out/'coverage_validation',[])
    early={r['file_id']:r for r in read_rows(out/'early30_overlays.jsonl')}
    for check in checks:
        if check['status']!='blocked' or 'finding_quote not bound' not in check.get('error',''):continue
        fid=check['file_id'];draft,text,idx,c,s=get(fid)
        effective=early[fid]['updated_draft'] if fid in early else draft
        updated,changes=add_missing_bindings(effective,text)
        assert {k:v for k,v in updated.items() if k!='coverage'}=={k:v for k,v in effective.items() if k!='coverage'}
        updated.update(semantic_status='candidate',human_review_status='pending')
        assert changes and updated['semantic_status']=='candidate' and updated['human_review_status']=='pending'
        overlay=dict(file_id=fid,overlay_kind='content_repair',repair_method='mechanical_exact_quote_pointer_rebinding',
            base_draft_json_sha256=sha_json(draft),base_text_sha256=s['text_sha256'],updated_draft=updated,
            updated_draft_json_sha256=sha_json(updated),confirmed_findings=changes,
            limitations=['候选事实与责任原值未改；本步骤不是新增全文语义审核或人工批准。'])
        try:
            result=validate(task_for(s),updated);status='pass';error=None
        except (AssertionError,ValueError,KeyError,TypeError,OSError) as exc:status='blocked';error=type(exc).__name__+': '+str(exc);result=None
        rows.append(overlay);results.append(dict(file_id=fid,status=status,error=error,validation=result))
    target.write_bytes(b''.join(canonical(r)+b'\n' for r in rows))
    save_json(out/'coverage_binding_verification.json',{'documents':len(rows),'passed':sum(x['status']=='pass' for x in results),
        'records':results,'facts_unchanged':True,'human_approved':0})
    print(json.dumps({'documents':len(rows),'passed':sum(x['status']=='pass' for x in results),'remaining_blocks':[x for x in results if x['status']!='pass']},ensure_ascii=False))

if __name__=='__main__':main()
