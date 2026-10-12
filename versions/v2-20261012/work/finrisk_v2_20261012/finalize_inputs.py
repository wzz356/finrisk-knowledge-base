"""Freeze non-overlapping effective overlays and reuse only unchanged successful checks."""
import json
import sys
from pathlib import Path
from collections import Counter
from run_v2 import ROOT,read_rows,canonical,sha_json,sha_file,save_json,apply_overlays
from check_all import make_compatibility_validator,task_for
sys.path.insert(0,str(Path(__file__).resolve().parent/'quality'))
from quality_common import get

def main():
    base=ROOT/'work/finrisk_v2_20261012/quality';out=ROOT/'outputs/FinRisk_知识库V2_20261012/quality'
    names=['early30_overlays.jsonl','priority20_overlays_canonical.jsonl','coverage_binding_overlays.jsonl',
           'date_binding_overlays.jsonl','date_semantic_overlays.jsonl','legacy_semantic_overlays.jsonl','F001901_final_overlay.jsonl']
    final={};origins={};inputs={}
    for name in names:
        p=base/name;inputs[name]=sha_file(p)
        for row in read_rows(p):
            fid=row['file_id'];draft,text,idx,c,s=get(fid)
            if fid in final:
                previous=final[fid]
                if name in ['coverage_binding_overlays.jsonl','date_binding_overlays.jsonl','date_semantic_overlays.jsonl']:
                    if previous.get('overlay_kind','label_migration')!='label_migration':raise ValueError('unexpected overlapping content repairs: '+fid)
                    # A composed repair must preserve the previously migrated label policy/tags.
                    if row['updated_draft']['label_policy_version']!=previous['updated_draft']['label_policy_version']:raise ValueError('label policy lost')
                    if [b['risk_tags'] for b in row['updated_draft']['behaviors']]!=[b['risk_tags'] for b in previous['updated_draft']['behaviors']]:raise ValueError('migrated labels lost')
                elif name=='F001901_final_overlay.jsonl':
                    if fid!='F001901' or row['updated_draft']['cases'][0]['penalty_date']!=previous['updated_draft']['cases'][0]['penalty_date']:
                        raise ValueError('unexpected date followup override')
                else:raise ValueError('unapproved overlapping overlay: '+fid)
            apply_overlays({fid:c},{fid:s},[row])
            if row.get('updated_draft_json_sha256')!=sha_json(row['updated_draft']):raise ValueError('updated draft SHA differs')
            final[fid]=row;origins.setdefault(fid,[]).append(name)
    out.mkdir(parents=True,exist_ok=True);target=out/'effective_overlays.jsonl'
    if target.exists():raise FileExistsError(target)
    target.write_bytes(b''.join(canonical(final[f])+b'\n' for f in sorted(final)))
    initial=ROOT/'outputs/FinRisk_知识库V2_20261012/quality/baseline_mechanical/mechanical_checks.jsonl'
    checks={r['file_id']:r for r in read_rows(initial)}
    aliases=json.loads((ROOT/'outputs/FinRisk_剩余全量运行_v2_20261011/reports/质量验收_20261012/name_evidence_exceptions_v1.json').read_text(encoding='utf-8-sig'))['records']
    validate=make_compatibility_validator(out/'effective_validation',aliases);counts=Counter()
    for fid,row in final.items():
        draft,text,idx,c,s=get(fid);effective=apply_overlays({fid:c},{fid:s},[row])[fid]
        result=validate(task_for(s),effective)
        checks[fid].update(status='pass',effective_draft_json_sha256=sha_json(effective),validation=result,
                           verification_origin='rechecked_final_effective_overlay')
    for fid,row in checks.items():
        counts[row['status']]+=1;counts[row['batch']+':'+row['status']]+=1
        if fid not in final:row['verification_origin']='carried_forward_same_candidate_and_source'
        if row['status']!='pass':raise ValueError('unresolved mechanical block: '+fid)
    if len(checks)!=9639:raise ValueError('incomplete final checks')
    path=out/'mechanical_checks_final.jsonl';path.write_bytes(b''.join(canonical(checks[f])+b'\n' for f in sorted(checks)))
    save_json(out/'input_freeze.json',{'candidate_files':9639,'effective_overlays':len(final),'counts':dict(counts),
        'overlay_file_sha256':sha_file(target),'final_checks_sha256':sha_file(path),'initial_checks_sha256':sha_file(initial),
        'overlay_input_sha256':inputs,'origins_by_file':origins,'all_mechanical_checks_passed':True,
        'human_approved':0,'limitations':['机械通过不等于全量语义核验；候选事实与标签仍需人工验收。',
        '覆盖指针及17份唯一同值日期修补只做来源绑定，不能增加实施主体或日期角色认定。']})
    print(json.dumps({'files':len(checks),'overlays':len(final),'counts':dict(counts),'human_approved':0},ensure_ascii=False))

if __name__=='__main__':main()
