"""Verify measured records and prepare a local, auditable result delivery."""
import shutil
import re
from effect_common import *
from api_runner import Ledger,usage_bound

def has_credential_like_value(text):return bool(re.search(r'(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{16,}',text))

def main():
    frozen=read(OUT/'contracts/pre_inference_freeze.json')['sha256'];verify(frozen)
    expected_ledger=Ledger(OUT/'api/ledger.jsonl',2)
    recs=list(rows(OUT/'api/records.jsonl'))
    if len(recs)!=len(expected_ledger.reservations) or len(recs)!=len(expected_ledger.settled):raise ValueError('attempts do not align with ledger')
    identities=set()
    for r in recs:
        rid=r['reservation_id']
        if rid in identities:raise ValueError('duplicate attempt reservation')
        identities.add(rid);reserved=expected_ledger.reservations[rid];paid=expected_ledger.settled[rid]
        if reserved['pair_id']!=r['pair_id'] or reserved['base_payload_sha256']!=r['base_payload_sha256']:raise ValueError('ledger identity differs')
        cost=usage_bound(r['usage'])
        if abs(cost-r['booked_peak_bound_usd'])>1e-12 or abs(cost-paid['booked_usd'])>1e-12:raise ValueError('usage charge differs')
    fees=read(OUT/'results/diagnostics.json')['fee']
    if abs(expected_ledger.booked()-fees['booked_peak_bound_usd'])>1e-9 or expected_ledger.booked()>2:raise ValueError('fee summary differs')
    for phase in ['development_initial','development_judgment','holdout_initial','holdout_judgment']:
        mark=read(OUT/'api'/phase/'completion.json');jp=OUT/'api_jobs'/(phase+'.jsonl')
        if not mark['complete'] or sha(jp)!=mark['jobs_sha256'] or sha(OUT/'api'/phase/'accepted.jsonl')!=mark['accepted_sha256']:raise ValueError('phase not complete/bound')
    # Copy reproducibility sources and frozen new36 locally; never copy a key.
    target=OUT/'repro/code';target.mkdir(parents=True,exist_ok=True)
    for p in WORK.glob('*.py'):shutil.copyfile(p,target/p.name)
    for dirname in ['tests','review','scoring_review']:
        shutil.copytree(WORK/dirname,OUT/'repro'/dirname,dirs_exist_ok=True)
    shutil.copyfile(WORK/'scoring_notes.md',OUT/'repro/scoring_notes.md')
    shutil.copytree(DATA,OUT/'dataset',dirs_exist_ok=True)
    # All newly created JSON/text artifacts, excluding copied code patterns.
    scans=0
    for p in OUT.rglob('*'):
        if p.is_file() and p.suffix in {'.json','.jsonl','.md','.txt'}:
            if has_credential_like_value(p.read_text(encoding='utf-8-sig')):raise ValueError('credential-like value in artifact '+str(p))
            scans+=1
    save(OUT/'results/final_verification.json',dict(passed=True,protected_frozen_files_unchanged=len(frozen),
        phases_complete=4,unique_tasks=3708,attempts=len(recs),usage_ledger_recomputed=True,
        booked_peak_bound_usd=expected_ledger.booked(),hard_cap_usd=2,actual_invoice_verified=False,
        scanned_json_text_artifacts=scans,credential_like_values_found=0,expert_review=False,github_upload_performed=False,verified_utc=utc()))
    pins={str(p.relative_to(OUT)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in {'delivery_manifest.json','run.lock'}}
    save(OUT/'delivery_manifest.json',dict(schema='finrisk-p0-effect-result-delivery-v1',created_utc=utc(),files=pins))
    print(json.dumps(dict(passed=True,protected_files_unchanged=len(frozen),files=len(pins),booked_peak_bound_usd=expected_ledger.booked()),ensure_ascii=False))

if __name__=='__main__':main()
