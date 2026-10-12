"""Rebind an unchanged complete candidate date only to one same date in source."""
import copy
import json
import sys
from pathlib import Path
from run_v2 import ROOT,read_rows,canonical,sha_json,save_json
from check_all import task_for,make_compatibility_validator
from compat_check_v1 import _ISO_DATE,_DOT_DATE,_CHINESE_DATE,_parse_date,compact
sys.path.insert(0,str(Path(__file__).resolve().parent/'quality'))
from quality_common import get

PATTERNS=(_ISO_DATE,_DOT_DATE,_CHINESE_DATE)

def matching_date_quote(value,text):
    if not isinstance(value,str):return None
    actual=next((_parse_date(m) for p in PATTERNS if (m:=p.fullmatch(compact(value)))),None)
    if actual is None:return None
    # Keep verbatim whitespace, accepting only one continuous source date span.
    candidates={(m.start(),m.end(),m.group()) for p in PATTERNS for m in p.finditer(text) if _parse_date(m)==actual}
    return next(iter(candidates))[2] if len(candidates)==1 else None

def main():
    out=ROOT/'work/finrisk_v2_20261012/quality';target=out/'date_binding_overlays.jsonl'
    if target.exists():raise FileExistsError(target)
    checks=read_rows(ROOT/'outputs/FinRisk_知识库V2_20261012/quality/baseline_mechanical/mechanical_checks.jsonl')
    early={r['file_id']:r for r in read_rows(out/'early30_overlays.jsonl')}
    rows=[];results=[];validate=make_compatibility_validator(out/'date_validation',[])
    for check in checks:
        if check['status']!='blocked' or 'date' not in check.get('error',''):continue
        fid=check['file_id'];base,text,idx,c,s=get(fid)
        effective=early[fid]['updated_draft'] if fid in early else base
        updated=copy.deepcopy(effective);changes=[]
        for case in updated['cases']:
            value=case.get('penalty_date');quote=matching_date_quote(value,text)
            if quote is None or quote==case.get('penalty_date_quote'):continue
            changes.append({'case_key':case['local_key'],'field':'penalty_date_quote',
                'source_quote':quote,'old_quote':case.get('penalty_date_quote'),'unchanged_date_value':value,
                'finding':'old date evidence was unrelated; a unique matching complete date is present in the original source'})
            case['penalty_date_quote']=quote
        if not changes:
            results.append(dict(file_id=fid,status='unresolved',reason='no unique exact same complete date span; no date value changed'))
            continue
        for a,b in zip(effective['cases'],updated['cases']):
            assert {k:v for k,v in a.items() if k!='penalty_date_quote'}=={k:v for k,v in b.items() if k!='penalty_date_quote'}
        assert effective['behaviors']==updated['behaviors'] and effective['coverage']==updated['coverage']
        updated.update(semantic_status='candidate',human_review_status='pending')
        overlay=dict(file_id=fid,overlay_kind='content_repair',repair_method='unchanged_complete_date_exact_source_rebinding',
            base_draft_json_sha256=sha_json(base),base_text_sha256=s['text_sha256'],updated_draft=updated,
            updated_draft_json_sha256=sha_json(updated),confirmed_findings=changes,
            limitations=['仅重绑唯一同值完整日期引文；原日期值不变，未新增处罚日期角色的语义认定。','模型候选，人工审核pending。'])
        try:
            result=validate(task_for(s),updated);status='pass';error=None
        except (AssertionError,ValueError,KeyError,TypeError,OSError) as exc:status='blocked';error=type(exc).__name__+': '+str(exc);result=None
        if status=='pass':rows.append(overlay)
        results.append(dict(file_id=fid,status=status,error=error,validation=result))
    target.write_bytes(b''.join(canonical(r)+b'\n' for r in rows))
    save_json(out/'date_binding_verification.json',{'documents_examined':len(results),'passed':len(rows),
        'records':results,'date_values_unchanged':True,'human_approved':0})
    print(json.dumps({'examined':len(results),'passed':len(rows),'unresolved':[r for r in results if r['status']!='pass']},ensure_ascii=False))

if __name__=='__main__':main()
