"""Read-only final experiment/source/legacy delivery checks; save a new report."""
from collections import Counter
from pathlib import Path
import e06,e07
from e07 import OUT,ROOT,WORK,demo


def old_delivery(folder):
    root=ROOT / 'outputs' / folder
    manifest=demo.read_json(root / 'delivery_manifest.json')
    for row in manifest['files']:
        path=ROOT / row['path']
        assert path.stat().st_size==row['size_bytes'] and demo.sha_file(path)==row['sha256']
    listed={r['path'] for r in manifest['files'] if r['path'].startswith(root.relative_to(ROOT).as_posix()+'/')}
    actual={p.relative_to(ROOT).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='delivery_manifest.json'}
    assert actual==listed
    return dict(files=len(manifest['files']),bytes=sum(r['size_bytes'] for r in manifest['files']),
                manifest_sha256=demo.sha_file(root / 'delivery_manifest.json'),unchanged=True)


def main():
    sources=demo.source_map()
    profiles=demo.rows(OUT / 'e07_final/e07_profiles.jsonl')
    checks=demo.rows(OUT / 'e07_final/e07_input_checks.jsonl')
    branches=demo.rows(OUT / 'e07_final/e07_information_branches.jsonl')
    fields={p['mechanism_id']:{q['field_id'] for q in p['questions']} for p in profiles}
    state=Counter()
    for profile in profiles:
        support=profile['support'];source=sources[support['file_id']]
        assert demo.sha_text(source)==support['source_sha256']
        for span in support['spans']:assert source[span['start']:span['end']]==support['quote']
    queries={q['query_id']:q['text'] for q in demo.rows(OUT / 'queries.jsonl')}
    for check in checks:
        e07.validate_input_record(check,fields[check['mechanism_id']])
        assert check['text']==queries[check['query_id']]
        assert check['human_approved'] is False
        state.update(c['state'] for c in check['conditions'])
    assert state==Counter(present=19,absent=12,unknown=33)
    assert len(branches)==8 and len(profiles)==7 and len(checks)==16
    assert sum(len(c['followup_questions']) for c in checks)==31
    packets={p['query_id']:p for p in demo.rows(demo.OUT / 'evidence_packets.jsonl')}
    judgments={j['query_id']:j for j in demo.rows(demo.OUT / 'model_judgments.jsonl')}
    parents=demo.rows(demo.OUT / 'display_results.jsonl')
    units,_=demo.load_scope(sources)
    graph=demo.read_json(OUT / 'local_graph.json')
    actual={r['query_id']:r for r in demo.rows(OUT / 'e06_results.jsonl')}
    for parent in parents:
        e06.validate_parent_binding(parent,packets[parent['query_id']],judgments[parent['query_id']],sources)
        assert actual[parent['query_id']]['files']==e06.diversify(parent['files'][:20],units,graph)
    all_judgments=demo.rows(OUT / 'e06_all_judgments.jsonl')
    assert len(all_judgments)==80
    for j in all_judgments:
        assert j['text']==queries[j['query_id']]
        assert j['source_sha256']==demo.sha_text(sources[j['hit']['file_id']])
        assert j['displayed_text_sha256']==demo.sha_text(j['hit']['text'])
        assessment=j['assessment']
        if assessment['helpful']:assert assessment['quote'] and assessment['quote'] in j['hit']['text']
    assert sum(j['assessment']['helpful'] for j in all_judgments)==51
    e05verify=demo.read_json(OUT / 'e05_verification.json')
    e05metrics=demo.read_json(OUT / 'e05_metrics.json')
    assert e05verify['status']=='passed' and e05metrics['status']=='complete_exploratory_replay'
    assert e05metrics['actual_new_rerank_pairs']==1649 and e05metrics['exact_shared_rerank_pairs']==3151
    assert '最终结论：**PASS' in (WORK / 'code_review.md').read_text(encoding='utf-8')
    assert 'PASS' in (WORK / 'e05_summary_review.md').read_text(encoding='utf-8')
    log=(WORK / 'tests_final_green.log').read_text(encoding='utf-8-sig')
    assert 'Ran 25 tests' in log and '\nOK' in log
    old={folder:old_delivery(folder) for folder in ('FinRisk_离线演示V3_20261013','FinRisk_E01-E04五小时实验_20261013')}
    for path,digest in demo.read_json(OUT / 'freeze_retrieve.json')['files_sha256'].items():assert demo.sha_file(path)==digest
    report=dict(status='passed',tests_passed=25,e07=dict(mechanisms=7,inputs=16,conditions=64,
        state_counts=dict(state),questions=31,simulated_branches=8),
        e06=dict(queries=16,positions=80,exact_parent_bindings_and_replays=True,helpful=51),
        e05=e05verify,old_deliveries=old,
        independent_model_code_review='passed',independent_model_source_review='passed',
        human_approved=False,independent_quality_gold=False,production_default_modified=False,E08_executed=False)
    demo.write_new(OUT / 'verification_final.json',report)
    print(report)


if __name__=='__main__':main()
