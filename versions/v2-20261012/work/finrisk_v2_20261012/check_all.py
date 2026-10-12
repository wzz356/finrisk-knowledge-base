"""Run frozen compatibility guards against explicitly exported candidate records."""
import argparse
import hashlib
import json
import sys
import traceback
from collections import Counter
from pathlib import Path
from normalize_v2 import iter_records
from run_v2 import ROOT,read_rows,save_json,canonical,sha_json,apply_overlays,sha_file

sys.path.insert(0,str(ROOT/'work/finrisk_acceptance_20261012'))
from compat_check_v1 import make_compatibility_validator

RAW_ROOTS={
    'remaining8509':ROOT/'outputs/FinRisk_剩余全量准备_20261011/raw',
    'prior1000':ROOT/'outputs/FinRisk_1000准备_20261011/raw',
    'early100':ROOT/'outputs/FinRisk_基础重建运行_v1_20261010/inputs/raw_text',
    'early30':ROOT/'outputs/FinRisk_30份模型预审与人工验收候选_20261010/inputs/raw_text',
}

def task_for(source):
    fid=source['file_id'];raw=(RAW_ROOTS[source['batch']]/(fid+'.txt')).resolve()
    if not raw.is_file():raise FileNotFoundError('explicit original raw source missing: '+str(raw))
    if sha_file(raw)!=source['source_sha256']:raise ValueError('original raw source SHA differs: '+fid)
    doc=dict(source.get('document_metadata') or {})
    for k in ['source_id','text_id','source_sha256','text_sha256','text_version','full_text']:doc[k]=source[k]
    doc['official_file_id']=fid
    return dict(file_id=fid,document=doc,raw_path=str(raw),
                **{k:source[k] for k in ['source_id','text_id','source_sha256','text_sha256','text_version','full_text']})

def run(repo,out,overlay_paths):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    target=out/'mechanical_checks.jsonl'
    if target.exists():raise FileExistsError(target)
    sources={r['file_id']:r for r in iter_records(Path(repo)/'data/sources')}
    overlays={r['file_id']:r for p in overlay_paths for r in read_rows(p)}
    if sum(len(read_rows(p)) for p in overlay_paths)!=len(overlays):raise ValueError('duplicate overlay')
    aliases=json.loads((ROOT/'outputs/FinRisk_剩余全量运行_v2_20261011/reports/质量验收_20261012/name_evidence_exceptions_v1.json').read_text(encoding='utf-8-sig'))
    if isinstance(aliases,dict):aliases=aliases['records']
    validate=make_compatibility_validator(out,aliases);counts=Counter();seen=set()
    with target.open('wb') as sink:
        for c in iter_records(Path(repo)/'data/candidates'):
            fid=c['file_id'];s=sources[fid]
            if fid in seen:raise ValueError('duplicate file_id')
            seen.add(fid)
            row={'file_id':fid,'batch':c['batch'],'original_draft_json_sha256':c['draft_json_sha256'],
                 'original_candidate_byte_sha256':c['original_candidate_sha256'],'text_sha256':s['text_sha256'],
                 'source_sha256':s['source_sha256'],'semantic_status':'candidate','human_review_status':'pending'}
            try:
                if sha_json(c['draft'])!=c['draft_json_sha256']:raise ValueError('candidate SHA mismatch')
                draft=apply_overlays({fid:c},{fid:s},[overlays[fid]])[fid] if fid in overlays else c['draft']
                row['effective_draft_json_sha256']=sha_json(draft)
                result=validate(task_for(s),draft)
                row.update(status='pass',validation=result)
                counts['pass']+=1;counts['requires_review']+=result['requires_review']
            except (AssertionError,ValueError,KeyError,TypeError,OSError) as exc:
                frame=traceback.extract_tb(exc.__traceback__)[-1]
                row.update(status='blocked',error=type(exc).__name__+': '+str(exc),
                           location={'file':frame.filename,'line':frame.lineno,'code':frame.line})
                counts['blocked']+=1
            sink.write(canonical(row)+b'\n');counts[c['batch']+':'+row['status']]+=1
            if len(seen)%500==0:print(json.dumps({'files':len(seen),'counts':dict(counts)}),flush=True)
    if len(seen)!=9639 or seen!=set(sources):raise ValueError('incomplete exported population')
    report={'files':len(seen),'counts':dict(counts),'checks_sha256':sha_file(target),
            'checker_sha256':sha_file(__file__),'compatibility_checker_sha256':sha_file(ROOT/'work/finrisk_acceptance_20261012/compat_check_v1.py'),
            'overlay_sha256':{str(p):sha_file(p) for p in overlay_paths},
            'scope':'source bytes/decode, full text, quotes, field types, labels, coverage, declared amount/date guards; no semantic approval',
            'signal_does_not_mean_error':True,'human_approved':0}
    save_json(out/'mechanical_check_summary.json',report);print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=ROOT/'finrisk-knowledge-base')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--overlays',nargs='*',type=Path,default=[])
    a=p.parse_args();run(a.repo,a.output,a.overlays)
