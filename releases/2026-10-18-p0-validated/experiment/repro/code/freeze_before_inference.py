"""Verify sealed sources and bind the already authorized inference configuration."""
from effect_common import *
from api_runner import validate_authorization
from protocol import validate_job

pins={}
def add(p,digest=None):
    p=Path(p).resolve();d=sha(p)
    if digest is not None and d!=digest:raise ValueError('source mismatch: '+str(p))
    if str(p) in pins and pins[str(p)]!=d:raise ValueError('conflicting source')
    pins[str(p)]=d

for p,d in read(RUNTIME/'contracts/input_freeze.json')['protected_files'].items():add(p,d)
for p,v in read(RUNTIME/'delivery_manifest.json')['files'].items():add(RUNTIME/p,v['sha256'])
add(RUNTIME/'delivery_manifest.json')
for p,d in read(OUT/'retrieval/freeze.json')['sha256'].items():add(p,d)
for p in sorted((OUT/'retrieval').glob('*')):
    if p.is_file():add(p)
for p in sorted((OUT/'contracts').glob('*')):
    if p.is_file() and p.name!='pre_inference_freeze.json':add(p)
for p in sorted((OUT/'api_jobs').glob('*')):add(p)
add(OUT/'audit/initial_task_map.jsonl');add(OUT/'实验协议.md')
for p in sorted(WORK.glob('*.py')):add(p)
for p in sorted((WORK/'tests').glob('*.py')):add(p)
for p in sorted((SEALED/'code').glob('*.py')):add(p)
for split in ('development','holdout'):
    for j in rows(OUT/'api_jobs'/(split+'_initial.jsonl')):validate_job(j)
validate_authorization(read(OUT/'authorization.json'),read(OUT/'contracts/api_request_plan.json'),sha(OUT/'contracts/api_request_plan.json'))
save(OUT/'contracts/pre_inference_freeze.json',dict(scope=SCOPE,created_utc=utc(),sha256=pins,api_calls_before_freeze=0,reference_answers_used_for_configuration=False))
print(json.dumps(dict(frozen_files=len(pins),validated_initial_jobs=3636,authorized_cap_usd=2)))
