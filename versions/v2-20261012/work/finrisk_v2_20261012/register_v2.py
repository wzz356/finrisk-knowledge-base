"""Single-writer compatibility registration, preserving old formal revision history."""
import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from run_v2 import ROOT,read_rows,canonical,sha_json,sha_file,save_json,apply_overlays
from normalize_v2 import iter_records
from check_all import make_compatibility_validator
sys.path.insert(0,str(ROOT/'work/finrisk_remaining'))
import fast_runtime as startup_runtime
runtime=startup_runtime.base

def next_revision(revision,old_sha,new_sha):
    if old_sha==new_sha:return None
    if revision is not None and revision>=2:raise ValueError('two formal revisions already used; needs human review')
    return (revision if revision is not None else -1)+1

def run(output,overlay_path,execute=False):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    overlays={r['file_id']:r for r in read_rows(overlay_path)}
    # One explicit verified entry covers the complete frozen 8509-source package.
    verified=runtime.verify_package_bindings(None);schedule=verified['schedule'];selected=runtime._selected()
    checks={r['file_id']:r for r in read_rows(ROOT/'outputs/FinRisk_知识库V2_20261012/quality/baseline_mechanical/mechanical_checks.jsonl')}
    candidates={r['file_id']:r for r in iter_records(ROOT/'finrisk-knowledge-base/data/candidates') if r['batch']=='remaining8509'}
    aliases=json.loads((ROOT/'outputs/FinRisk_剩余全量运行_v2_20261011/reports/质量验收_20261012/name_evidence_exceptions_v1.json').read_text(encoding='utf-8-sig'))['records']
    validate=make_compatibility_validator(out/'validation',aliases)
    validator_sha=sha_file(ROOT/'work/finrisk_acceptance_20261012/compat_check_v1.py')
    # Before any ledger mutation, preflight every source/candidate and freeze the exact target bytes.
    plan=[];drafts={};tasks={};counts=Counter()
    for batch in schedule['batches']:
        bid=batch['batch_id'];task_map={t['file_id']:t for t in runtime.tasks_for(batch,selected)}
        db_path=Path(batch['planned_run_path'])/'workflow.sqlite3';jobs={}
        if db_path.exists():
            with sqlite3.connect('file:'+db_path.resolve().as_posix()+'?mode=ro',uri=True) as db:
                for row in db.execute('SELECT file_id,revision,proposal_sha256 FROM jobs'):
                    jobs[row[0]]={'revision':None if row[1]<0 else row[1],'proposal_sha256':row[2]}
        for fid,t in task_map.items():
            c=candidates[fid]
            if checks[fid]['status']!='pass' or checks[fid]['original_draft_json_sha256']!=c['draft_json_sha256']:
                raise ValueError('base candidate lacks bound successful check: '+fid)
            origin=Path(c['original_candidate_path']).resolve()
            if not origin.is_relative_to(runtime.RUN/'authored'):raise ValueError('original draft path escapes authored area')
            raw=origin.read_bytes()
            if sha_file(origin)!=c['original_candidate_sha256'] or sha_json(runtime.strict_json(raw))!=c['draft_json_sha256']:
                raise ValueError('exact original candidate binding changed: '+fid)
            proposal=c['draft'];overlay=overlays.get(fid)
            if overlay:
                source={**t,'text_sha256':t['text_sha256']}
                proposal=apply_overlays({fid:c},{fid:source},[overlay])[fid]
                raw=canonical(proposal)+b'\n'
            digest=runtime.sha(raw);old=jobs.get(fid,{'revision':None,'proposal_sha256':None})
            revision=next_revision(old['revision'],old['proposal_sha256'],digest)
            if revision is not None:
                result=validate(t,proposal)
                if result['uncovered_tokens']:raise ValueError('coverage gap')
                counts['new' if old['proposal_sha256'] is None else 'update']+=1
                snapshot=out/'targets'/bid/(fid+'.json');snapshot.parent.mkdir(parents=True,exist_ok=True)
                if snapshot.exists() and snapshot.read_bytes()!=raw:raise ValueError('target snapshot differs')
                snapshot.write_bytes(raw);drafts[fid]=(proposal,raw,snapshot)
            else:counts['already_current']+=1
            tasks[fid]=t
            plan.append(dict(batch_id=bid,file_id=fid,previous_revision=old['revision'],previous_sha256=old['proposal_sha256'],
                target_revision=revision,target_sha256=digest,source_sha256=t['source_sha256'],text_sha256=t['text_sha256'],
                original_candidate_sha256=c['original_candidate_sha256'],overlay_applied=bool(overlay),
                semantic_status='candidate',human_review_status='pending',
                active_validator_version='finrisk-compat-v1',active_validator_sha256=validator_sha))
        print(json.dumps({'event':'registration_preflight_progress','batch':bid,'files':len(plan),'counts':dict(counts)}),flush=True)
    if len(plan)!=8509:raise ValueError('incomplete registration population')
    plan_path=out/'registration_plan.jsonl';plan_path.write_bytes(b''.join(canonical(r)+b'\n' for r in plan))
    binding={'phase':'preflight_complete','files':len(plan),'counts':dict(counts),'executed':False,
             'registration_plan_sha256':sha_file(plan_path),'script_sha256':sha_file(__file__),
             'compatibility_checker_sha256':sha_file(ROOT/'work/finrisk_acceptance_20261012/compat_check_v1.py'),
             'active_validator_version':'finrisk-compat-v1','active_validator_sha256':validator_sha,
             'overlay_file_sha256':sha_file(overlay_path),'frozen_source_package_manifest_sha256':verified['package_manifest_sha256'],
             'note':'Controlled V2 registration explicitly uses frozen compatibility guards; prior config and formal history retained.',
             'human_approved':0}
    save_json(out/'registration_summary.json',binding)
    print(json.dumps(binding,ensure_ascii=False),flush=True)
    if not execute:return
    # SQLite backup API preserves a consistent prior snapshot; never reset revisions or reviews.
    backups=[]
    for batch in schedule['batches']:
        db_path=Path(batch['planned_run_path'])/'workflow.sqlite3'
        if not db_path.exists():continue
        dest=out/'before_sqlite'/batch['batch_id']/'workflow.sqlite3';dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():raise FileExistsError('prior backup exists; explicit recovery required')
        with sqlite3.connect('file:'+db_path.resolve().as_posix()+'?mode=ro',uri=True) as src, sqlite3.connect(dest) as dst:src.backup(dst)
        backups.append(dict(batch_id=batch['batch_id'],backup_path=str(dest),backup_sha256=sha_file(dest)))
    save_json(out/'before_sqlite/backups.json',backups)
    plan_map={r['file_id']:r for r in plan};results=[]
    sink=(out/'registration_receipts.jsonl').open('wb')
    try:
        for batch in schedule['batches']:
            bid=batch['batch_id'];flow=runtime._make_workflow(batch,verified)
            batch_tasks=[tasks[fid] for fid in batch['file_ids']];flow.plan(bid,batch_tasks)
            flow.validator=validate
            for fid in batch['file_ids']:
                r=plan_map[fid];job=flow.get_job(bid,fid)
                if r['target_revision'] is not None:
                    # Recheck current history immediately before write, rejecting concurrent drift.
                    if job['proposal_sha256']!=r['previous_sha256'] or job['revision']!=r['previous_revision']:
                        raise ValueError('ledger changed since preflight: '+fid)
                    proposal,raw,snapshot=drafts[fid]
                    receipt={'mode':'real','provider':'current_conversation','model':None,'actual_model_deployment':None,
                        'usage':None,'cost':None,'external_api_call':False,'task_kind':'controlled_v2_candidate_registration',
                        'origin_path':str(snapshot),'origin_sha256':r['target_sha256'],
                        'registration_plan_sha256':binding['registration_plan_sha256'],
                        'active_validator_version':'finrisk-compat-v1',
                        'active_validator_sha256':binding['compatibility_checker_sha256'],
                        'source_package_sha256':verified['package_manifest_sha256']}
                    job=flow.ingest_proposal(bid,fid,proposal,receipt,revision=r['target_revision'],serialized_proposal=raw)
                if job['proposal_sha256']!=r['target_sha256'] or job['human_approved']:
                    raise ValueError('registered version or human state mismatch: '+fid)
                row={**r,'status':'registered_current_candidate','current_revision':job['revision'],
                     'current_sha256':job['proposal_sha256'],'job_status':job['status']}
                results.append(row);sink.write(canonical(row)+b'\n')
            sink.flush();print(json.dumps({'batch':bid,'registered':len(results)}),flush=True)
    finally:sink.close()
    binding.update(phase='registered_complete',executed=True,registered_current=len(results),
                   receipt_sha256=sha_file(out/'registration_receipts.jsonl'),prior_database_backups=len(backups))
    save_json(out/'registration_summary.json',binding)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--overlays',type=Path,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args();run(a.output,a.overlays,a.execute)
