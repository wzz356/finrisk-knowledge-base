"""Seal new experiment artifacts and verify bytes plus external frozen dependencies."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
from e07 import OUT,ROOT,WORK,demo

MANIFEST=OUT / 'delivery_manifest.json'


def inventory():
    paths=[p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST]
    paths += [p for p in WORK.iterdir() if p.is_file() and p.suffix in ('.py','.md','.log')]
    result=[]
    for path in sorted(paths,key=lambda p:p.relative_to(ROOT).as_posix()):
        assert not path.is_symlink()
        path.resolve().relative_to(ROOT.resolve())
        result.append(dict(path=path.relative_to(ROOT).as_posix(),size_bytes=path.stat().st_size,sha256=demo.sha_file(path)))
    return result


def external_cache_files():
    paths=[]
    for level in (1,2,3):
        cluster=demo.read_json(OUT / f'clusters_level{level}.json')
        path=Path(cluster['normalized_vector_path'])
        assert demo.sha_file(path)==cluster['normalized_vectors_sha256']
        paths.extend([path,path.with_suffix('.json')])
    for path in sorted((WORK / 'retrieval_cache').glob('*.json')):
        metadata=demo.read_json(path)
        vector=path.with_suffix('.npy')
        assert demo.sha_file(vector)==metadata['npy_sha256']
        paths.extend([path,vector])
    assert len(paths)==12 and len(set(paths))==12
    return {str(path.resolve()):demo.sha_file(path) for path in paths}


def verify_reports():
    verification=demo.read_json(OUT / 'verification_final.json')
    assert verification['status']=='passed' and verification['tests_passed']==25
    metrics=demo.read_json(OUT / 'e05_metrics.json')
    assert metrics['unique_judgments']==83 and metrics['positions']==240
    assert metrics['actual_new_rerank_pairs']==1649 and metrics['exact_shared_rerank_pairs']==3151
    wide=demo.read_json(OUT / 'e05_sensitivity.json')
    assert wide['exact_historical_contexts']==80 and wide['new_wider_context_opinions']==3
    items={i['item_id']:i for i in demo.rows(OUT / 'e05_reading_pool.jsonl')}
    wider=demo.rows(OUT / 'e05_sensitivity_bindings.jsonl')
    assert len(wider)==83 and set(r['item_id'] for r in wider)==set(items)
    for row in wider:
        item=items[row['item_id']]
        assert row['item_sha256']==demo.sha_json(item) and row['human_approved'] is False and row['primary_fresh_judgment'] is False
        a=row['assessment']
        if a['helpful']:assert a['quote'] and any(a['quote'] in s['text'] for s in item['source_segments'])
    assert [metrics['arms'][arm]['helpful'] for arm in ('B0','DIR','TREE')]==[47,45,45]
    assert all(wide['arms'][arm]['helpful']==53 for arm in ('B0','DIR','TREE'))
    assert demo.read_json(OUT / 'adoption.json')['current_weights']==[1,1]
    for name in ('E07实验报告.md','E06实验报告.md','E05实验报告.md','完整方案.md','实验总报告.md','README.md','复跑说明.md'):
        text=(OUT / name).read_text(encoding='utf-8')
        assert text.strip() and len(text)>300
    for path,digest in demo.read_json(OUT / 'freeze_retrieve.json')['files_sha256'].items():assert demo.sha_file(path)==digest


def check():
    manifest=demo.read_json(MANIFEST)
    assert manifest['files']==inventory()
    for path,digest in manifest['external_cache_files_sha256'].items():assert demo.sha_file(path)==digest
    verify_reports()
    return dict(status='passed',files=len(manifest['files']),bytes=sum(r['size_bytes'] for r in manifest['files']),
        manifest_sha256=demo.sha_file(MANIFEST),frozen_dependencies=105,external_cache_files=12,
        human_approved=False,E08_executed=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    if not args.check:
        verify_reports()
        caches=external_cache_files()
        demo.write_new(MANIFEST,dict(schema='finrisk_e07_local_e06_small_e05_delivery_v1',
            status='complete_local_exploratory_trials',sealed_at_utc=datetime.now(timezone.utc).isoformat(),
            primary_weights=[1,1],E08_executed=False,tests_passed=25,
            human_approved=False,independent_quality_gold=False,automatic_judgment_api=False,
            source_model_review='passed',root_code_model_review='passed',current_application_modified=False,
            current_retrieval_default_modified=False,github_pushed=False,
            official_dictionary_classes=27,E07='partial_light_condition_questions',E06='local_fact_role_event_prototype',
            E05='21_leaf_7_summary_6_directory_actual_16x3_trial',
            external_cache_files_sha256=caches,
            excluded=['model weights','virtual environments','vector cache copies','unchanged full source corpus dependencies'],
            files=inventory()))
    print(check())


if __name__=='__main__':main()
