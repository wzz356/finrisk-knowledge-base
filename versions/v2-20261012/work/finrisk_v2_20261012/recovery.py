"""Rebuild tables and projection from saved snapshots, without reading source repo data."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import normalize_v2 as normalizer
from run_v2 import ROOT,read_rows,canonical,sha_json,sha_file,save_json,prepare_dataset

def reconstruct_inputs(snapshots,documents):
    docs={};candidates={};sources={};effective={}
    for d in documents:
        fid=d['official_file_id']
        if fid in docs:raise ValueError('duplicate restored document')
        if hashlib.sha256(d['full_text'].encode('utf-8')).hexdigest()!=d['text_sha256']:raise ValueError('restored text SHA drift')
        docs[fid]=d
    for row in snapshots:
        fid=row['file_id']
        if fid in candidates or fid not in docs:raise ValueError('duplicate snapshot or missing document')
        base=row['base_draft'];updated=row.get('effective_draft') or base
        if sha_json(base)!=row['base_draft_json_sha256'] or sha_json(updated)!=row['effective_draft_json_sha256']:
            raise ValueError('restored candidate content SHA drift')
        c=copy.deepcopy(row['wrapper_metadata']);c['draft']=copy.deepcopy(base)
        s=copy.deepcopy(row['source_record_metadata']);s.update(full_text=docs[fid]['full_text'],document_metadata=copy.deepcopy(row['document_metadata']))
        if c['draft_json_sha256']!=sha_json(base) or s['text_sha256']!=docs[fid]['text_sha256']:raise ValueError('restored source/wrapper binding drift')
        candidates[fid]=c;sources[fid]=s
        if row.get('effective_draft') is not None:effective[fid]=copy.deepcopy(updated)
    if set(docs)!=set(candidates):raise ValueError('snapshot/document population differs')
    return candidates,sources,effective

def main():
    p=argparse.ArgumentParser();p.add_argument('--normalized',type=Path,required=True)
    p.add_argument('--overlays',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output
    if out.exists() and any(out.iterdir()):raise FileExistsError('recovery output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    # Only saved normalized content supplies drafts/text. Original .txt/PDF/task files are not read.
    c,s,e=reconstruct_inputs(read_rows(a.normalized/'extensions/candidate_snapshots.jsonl'),read_rows(a.normalized/'data/documents.jsonl'))
    if len(c)!=9639:raise ValueError('restoration must cover 9639 files')
    normalizer.CONTRACT_PATH=(a.normalized/'contract/schema.json').resolve()
    normalizer.normalize_records(c,s,out/'normalized',e)
    print(json.dumps({'event':'recovery_tables_generated','files':len(c)}),flush=True)
    del e
    original=json.loads((a.normalized/'manifest.json').read_text(encoding='utf-8'))
    rebuilt=json.loads((out/'normalized/manifest.json').read_text(encoding='utf-8'))
    differences=[name for name,binding in original['files'].items() if rebuilt['files'].get(name,{}).get('sha256')!=binding['sha256']]
    if differences:raise ValueError('recovered payload hashes differ: '+str(differences))
    repo=out/'recovered_inputs';(repo/'data/candidates').mkdir(parents=True);(repo/'data/sources').mkdir(parents=True)
    for name,m in [('candidates',c),('sources',s)]:
        (repo/'data'/name/'part-0001.jsonl').write_bytes(b''.join(canonical(m[f])+b'\n' for f in sorted(m)))
    del c,s
    save_json(repo/'manifest.json',{'status':'recovered_saved_inputs','files':9639,
        'candidate_snapshots_sha256':sha_file(a.normalized/'extensions/candidate_snapshots.jsonl'),
        'documents_sha256':sha_file(a.normalized/'data/documents.jsonl')})
    prepare_dataset(repo,out/'projection','all',read_rows(a.overlays))
    before=json.loads((a.prepared/'manifest.json').read_text(encoding='utf-8'))
    after=json.loads((out/'projection/manifest.json').read_text(encoding='utf-8'))
    projection_equal={name:before['corpora'][name]['sha256']==after['corpora'][name]['sha256'] for name in ['raw','structured']}
    if not all(projection_equal.values()):raise ValueError('recovered projection payload differs')
    v=normalizer.verify(out/'normalized')
    if not v['passed']:raise ValueError('recovered normalization failed verify: '+str(v['errors'][:10]))
    report={'passed':True,'source_files':9639,'normalized_payloads_compared':len(original['files']),
        'all_normalized_payload_hashes_equal':not differences,'projection_payload_hashes_equal':projection_equal,
        'verification':v,'source_repo_data_read':False,'raw_original_source_files_read':False,
        'source_of_reconstruction':'saved normalized snapshots + full texts + saved final overlays + copied contract',
        'code_sha256':sha_file(__file__),'human_approved':0,
        'limitations':['重建使用本机既有代码/冻结分词器；未声称异机依赖安装或原PDF/OCR恢复。','原raw SHA沿用已核验绑定，本演练未重新读取raw文件。']}
    save_json(out/'recovery_report.json',report);print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
