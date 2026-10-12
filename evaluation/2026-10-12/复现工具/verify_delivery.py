"""Read-only delivery consistency checks; save final hashes after all checks pass."""
import collections
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/finrisk_retrieval_20261012'
OUT = ROOT / 'outputs/FinRisk_召回实验_20261012'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return [json.loads(x) for x in (OUT/name).read_text(encoding='utf-8').splitlines() if x.strip()]


def main():
    frozen = {
        'queries.jsonl':'ee98d68b4e743fc2b5aef5c09f91627d71d5c10912081f9edcc587904c4cda18',
        'retrieval_results.jsonl':'edbba86d7a7c031f965095513aa803c196684a85b0937dc7221e14fac6d634c9',
        '评估标注/judgments_part_1.jsonl':'e5700bd7259011be35424e84efee4e3e2979a4df08cdb1ae620bad7ebfde7874',
        '评估标注/judgments_part_2.jsonl':'678df6dc52623e3db0f942581a79308dd41688b3be53d919e0dacc90f548484c',
        '评估标注/judgments_part_3.jsonl':'ef51d1675159c9d0dcf487f0ea30cc53ff389d768d7334972c6e3d7aa7961c0a',
        '评估标注/independent_audit_judgments.jsonl':'ef3f45b6466f64d18c5528d68f02bee0d05390704499b26fba57846c81b25eda',
    }
    for name,value in frozen.items():
        assert sha(OUT/name) == value, name
    runner_sha = '7a05001beb6e611e47743ec420f70763f61fd106932b02d54f73e24d772da4cb'
    assert sha(WORK/'runner.py') == runner_sha
    results=read('retrieval_results.jsonl')
    per=read('指标/per_query_metrics.jsonl')
    metrics=json.loads((OUT/'指标/metrics.json').read_text(encoding='utf-8'))
    judgments={x['pair_id']:x for x in read('指标/validated_judgments.jsonl')}
    original={x['pair_id']:x for n in range(1,4) for x in read(f'评估标注/judgments_part_{n}.jsonl')}
    assert len(original)==len(judgments)==671 and original==judgments
    assert len(results)==len(per)==300
    expected={(f'Q{i:03}',c,a) for i in range(1,51)
              for c,a in [('raw','bm25'),('raw','rrf_rerank'),('structured','bm25'),
                          ('structured','dense'),('structured','rrf'),('structured','rrf_rerank')]}
    assert {(r['query_id'],r['corpus'],r['arm']) for r in results}==expected
    assert {(r['query_id'],r['corpus'],r['arm']) for r in per}==expected
    grouped=collections.defaultdict(list)
    for r in per:
        grouped[(r['corpus'],r['arm'])].append(r)
        assert r['returned_files']==len(r['top5'])<=5
        f=sum(x['help_grade']>=2 for x in r['top5'])
        c=sum(x['context_help_grade']>=2 for x in r['top5'])
        assert abs(r['useful_at5']-f/5)<1e-10
        assert abs(r['context_useful_at5']-c/5)<1e-10
        assert r['support_coverage_at5']==bool(f)
        for x in r['top5']:
            j=judgments[x['pair_id']]
            cj=next(z for z in j['contexts'] if z['context_id']==x['context_id'])
            assert x['help_grade']==j['help_grade'] and x['context_help_grade']==cj['help_grade']
    for m in metrics['metrics']:
        rows=grouped[(m['corpus'],m['arm'])]
        assert len(rows)==50
        for field in ['useful_at5','context_useful_at5','support_coverage_at5','strong_coverage_at5',
                      'pool_ndcg_at5','mean_help_at5','misleading_at5','context_misleading_at5']:
            assert abs(m[field]-sum(r[field] for r in rows)/50)<1e-10,(m['corpus'],m['arm'],field)
    pool={x['pair_id']:x for x in read('评估标注/blind_judgment_pool.jsonl')}
    quote_checks=0
    for pid,j in judgments.items():
        p=pool[pid]
        if j['help_grade']>=2: assert j['source_quote']
        if j['source_quote']:
            assert j['source_quote'] in p['full_source_text']
            quote_checks+=1
        cm={c['context_id']:c for c in p['contexts']}
        for c in j['contexts']:
            if c['help_grade']>=2: assert c['evidence_quote']
            if c['evidence_quote']:
                assert c['evidence_quote'] in cm[c['context_id']]['text']
                if c['help_grade']>=2: assert c['evidence_quote'] in p['full_source_text']
                quote_checks+=1
    assert quote_checks==metrics['exact_quote_checks']==1087
    audit=json.loads((OUT/'运行完整性检查.json').read_text(encoding='utf-8'))
    assert audit['status']=='passed' and audit['exact_source_spans_checked']==5692
    assert audit['token_inputs_checked']==94307
    agree=json.loads((OUT/'指标/独立复标一致性.json').read_text(encoding='utf-8'))
    assert agree['file_useful_threshold_agreements']==agree['pairs']==24
    assert agree['context_useful_threshold_agreements']==agree['contexts']==38
    source_manifest=json.loads((OUT/'人工验收原文/manifest.json').read_text(encoding='utf-8'))
    assert len(source_manifest['files'])==15
    for item in source_manifest['files'].values(): assert sha(OUT/item['file'])==item['text_sha256']
    packet=(OUT/'人工验收样例.md').read_text(encoding='utf-8')
    assert len(re.findall(r'^## Q\d{3} ',packet,re.M))==11
    compared=(OUT/'逐查询对照.md').read_text(encoding='utf-8')
    assert len(re.findall(r'^\| Q\d{3} \|',compared,re.M))==50
    link_checks=0
    markdown=['实验报告.md','人工验收样例.md','逐查询对照.md','独立复标记录.md','运行与复现说明.md']
    for name in markdown:
        t=(OUT/name).read_text(encoding='utf-8')
        for m in re.finditer(r'\[[^\]]*\]\(([^)]+)\)',t):
            ref=m.group(1)
            if not ref.startswith(('https:','http:','#')):
                assert (OUT/ref).exists(),(name,ref)
                link_checks+=1
    # Save final reporting/audit tools only; frozen runner and scoring data are untouched.
    for name in ['build_final_report.py','verify_delivery.py','audit_actual_run.py']:
        shutil.copy2(WORK/name,OUT/'复现工具'/name)
    files={str(p.relative_to(OUT)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':sha(p)}
           for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='交付完整性.json'}
    summary={'status':'passed','experiment_complete':True,'human_approved':False,
             'queries':50,'result_rows':300,'groups':6,'judged_pairs':671,'contexts':945,
             'main_exact_quote_checks':quote_checks,'independent_pairs':24,'independent_contexts':38,
             'exported_source_files':15,'diagnostic_queries':11,'local_markdown_links_checked':link_checks,
             'frozen_inputs_unchanged':True,'runner_sha256':runner_sha,
             'runner_rule_tests':{'status':'passed','tests':15,
                                  'evidence':'本轮真实执行python -B -m unittest -v test_runner，exit_code=0，Ran 15 tests，OK；结果见会话工具记录。'},
             'files':files,'limitations':['模型辅助帮助度、同模型体系独立上下文复标，非人类验收',
                                          '50条合成开发查询，不是盲测或全库完整相关集合',
                                          '正式知识库及审批/账本未切换，后续改进收益尚未测量']}
    (OUT/'交付完整性.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='files'},ensure_ascii=False))
    print('hashed_files',len(files))


if __name__=='__main__':
    main()
