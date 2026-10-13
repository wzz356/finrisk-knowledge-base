"""Verify public experiment files and all byte-exact restored payload hashes; standard library."""
import argparse,json
from pathlib import Path
from v2_payloads import sha,safe_path,verify_payload,payload_chunks,LIMIT

def main(repo):
    repo=Path(repo).resolve();version=repo/'experiments/2026-10-13'
    manifest=json.loads((version/'publication_manifest.json').read_text(encoding='utf-8'))
    actual={p.relative_to(version).as_posix() for p in version.rglob('*') if p.is_file()}
    assert actual==set(manifest['files'])|{'publication_manifest.json'}
    for name,meta in manifest['files'].items():
        path=safe_path(version,name)
        assert path.stat().st_size==meta['bytes'] and sha(path)==meta['sha256'],name
        assert path.stat().st_size<=LIMIT and not path.name.startswith('.env')
        assert path.suffix not in {'.npy','.safetensors','.sqlite','.sqlite3','.pem','.key','.pfx','.p12','.pyc','.pdf'}
    maps=json.loads((version/'payload_map.json').read_text(encoding='utf-8'))['payloads']
    payloads={m['path']:m for m in maps};assert len(payloads)==len(maps)==480
    for i,meta in enumerate(maps,1):
        verify_payload(version,meta)
        if i%100==0:print(json.dumps({'event':'payloads_verified','count':i,'total':len(maps)}),flush=True)
    def read_original(name):
        return json.loads(b''.join(payload_chunks(version,payloads[name])))
    index=json.loads((version/'bundle_index.json').read_text(encoding='utf-8'))
    assert len(index['bundles'])==5 and index['weights']==[1,1] and index['E08_executed'] is False
    needed=set()
    for bundle in index['bundles']:
        frozen=read_original(bundle['manifest_path'])
        assert payloads[bundle['manifest_path']]['sha256']==bundle['manifest_sha256']
        entries=frozen.get('files') or frozen['output_files']+frozen['work_code_notes_and_logs']
        expected={r['path'] for r in entries}|{bundle['manifest_path']}
        assert expected==set(bundle['original_paths'])
        needed|=expected
        for row in entries:
            meta=payloads[row['path']]
            assert meta['sha256']==row['sha256'] and meta['bytes']==row.get('size_bytes',row.get('bytes'))
    needed.add('outputs/FinRisk_离线知识库重建任务清单_教材方法对应.md')
    assert needed==set(payloads)
    prefix='outputs/FinRisk_E07_E06_E05探索_20261013/'
    metrics=read_original(prefix+'e05_metrics.json');wide=read_original(prefix+'e05_sensitivity.json')
    assert [metrics['arms'][a]['helpful'] for a in ('B0','DIR','TREE')]==[47,45,45]
    assert all(wide['arms'][a]['helpful']==53 for a in ('B0','DIR','TREE'))
    assert metrics['unique_judgments']==83 and metrics['positions']==240
    assert metrics['actual_new_rerank_pairs']==1649 and metrics['exact_shared_rerank_pairs']==3151
    assert read_original(prefix+'e06_metrics.json')['useful_positions_after']==51
    assert read_original(prefix+'e07_final/e07_execution.json')['state_counts']==dict(present=19,absent=12,unknown=33)
    assert read_original(prefix+'adoption.json')['current_weights']==[1,1]
    assert read_original(prefix+'verification_final.json')['tests_passed']==25
    report={'status':'passed','bundles':5,'original_payloads':len(maps),'public_files':len(actual),
        'restored_original_bytes':sum(m['bytes'] for m in maps),'source_sha_verified':True,
        'current_weights':[1,1],'E08_executed':False,'human_approved':False,
        'independent_quality_gold':False,'models_or_caches_included':False}
    print(json.dumps(report,ensure_ascii=False),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parent.parent)
    main(p.parse_args().repo)
