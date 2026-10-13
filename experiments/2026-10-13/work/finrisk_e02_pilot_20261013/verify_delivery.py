"""Verify E02 source/result/grade bindings; no inference or semantic grading."""
import copy
import hashlib
import importlib.util
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
OUT = ROOT / "outputs/FinRisk_E02小批量实验_20261013"
E04 = ROOT / "outputs/FinRisk_E04小批量实验_20261012"


def sha(path):
    path=Path(path)
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def obj(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def rows(path): return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]
def check(test, message):
    if not test: raise ValueError(message)


def main():
    frozen=obj(OUT/'execution_freeze.json');initial=obj(OUT/'input_freeze.json')
    for name,expected in initial['protected_input_sha256'].items(): check(sha(ROOT/name)==expected,'protected input changed: '+name)
    for name,expected in frozen['implementation_sha256'].items(): check(sha(WORK/name)==expected,'frozen code changed: '+name)
    for name,expected in frozen['new_input_sha256'].items(): check(sha(OUT/name)==expected,'frozen experiment input changed: '+name)
    check(sha(ROOT/'work/finrisk_v2_20261012/eval_v2.py')==frozen['old_evaluation_helper_sha256'],'old helper changed')
    for cache,key in [('finrisk_retrieval_20261012','old_cache_readonly_snapshot'),('finrisk_e04_pilot_20261012','e04_cache_readonly_snapshot')]:
        now={p.name:sha(p) for p in (ROOT/'work'/cache/'vector_cache').iterdir() if p.is_file()}
        check(now==frozen[key],cache+' cache changed')
    delivery=obj(E04/'delivery_manifest.json')
    for r in delivery['output_files']+delivery['work_code_notes_and_logs']:
        check(sha(ROOT/r['path'])==r['sha256'],'old E04 artifact changed: '+r['path'])
    run=obj(OUT/'results.jsonl.run.json');results=rows(OUT/'results.jsonl')
    check(run['status']=='complete' and len(results)==66 and run['completed_queries']==22,'incomplete real run')
    check(Counter(r['arm'] for r in results)=={'P0':22,'P1':22,'P2':22},'three-arm population incomplete')
    for key,name in [('output_sha256','results.jsonl'),('score_pool_sha256','results.jsonl.score_pool.jsonl'),('token_audit_sha256','results.jsonl.token_audit.jsonl')]:
        check(run[key]==sha(OUT/name),'run sidecar binding changed: '+name)
    for name,expected in run['input_sha256'].items(): check(sha(name)==expected,'run input changed: '+name)
    check(run['source_population']==9639 and run['searchable_units']==65475 and run['changed_units']==24,'population or dose changed')
    check(run['vector_operation']['new_document_encoding_rows']==24 and run['vector_operation']['unchanged_document_reencoding_rows']==0,'unexpected vector recomputation')
    check(run['vector_operation']['actual_query_encoding_rows']==22,'query inference missing')
    check(all(v['truncated_inputs']==0 for v in run['models']['truncation']),'actual model truncation')
    check(run['query_token_preflight']['rejected']==run['overlay_token_preflight']['rejected']==0,'token preflight rejection')
    baseline={r['query_id']:r for phase in ('dev','confirmation') for r in rows(E04/(phase+'_results.jsonl')) if r['arm']=='A0'}
    by={(r['query_id'],r['arm']):r for r in results}
    prefixes={p['unit_id']:p for p in rows(OUT/'prefixes.jsonl')}
    for qid,original in baseline.items():
        p0=by[(qid,'P0')];p2=by[(qid,'P2')]
        check(all(p0[k]==original[k] for k in ('files','cases','stages','query_id','text')),'P0 baseline differs: '+qid)
        check(p2['stages']==p0['stages'],'P2 retrieval stages changed: '+qid)
        for key in ('files','cases'):
            check(len(p0[key])==len(p2[key]),'P2 aggregate count changed')
            for old,new in zip(p0[key],p2[key]):
                if new.get('prefix'):
                    check(new['unit_id'] in prefixes and new['prefix']==prefixes[new['unit_id']]['prefix_text'],'P2 wrong winner prefix')
                plain=copy.deepcopy(new)
                for k in ('prefix_claims','prefix_source_unit_id','prefix_profile','prefix_review_status','prefix_source_sha256','prefix_sha256','base_context_text','original_unit_text'):
                    plain.pop(k,None)
                plain['prefix']='';plain['text']=old['text']
                check(plain==old,'P2 modified identity/ranking/body/index: '+qid)
    scores=rows(OUT/'results.jsonl.score_pool.jsonl')
    check(len(scores)==4400 and Counter(s['arm'] for s in scores)=={'P0':2200,'P1':2200},'score pool incomplete')
    check(len({(s['arm'],s['query_id'],s['unit_id']) for s in scores})==4400,'duplicate score pool entry')
    check(all(s['provenance']['kind']=='actual_local_gpu_rerank100' for s in scores if s['arm']=='P1'),'P1 score is not real GPU provenance')
    spec=importlib.util.spec_from_file_location('delivery_e02_eval',WORK/'evaluate.py');e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
    q=e.load_queries(OUT/'queries.jsonl');sources=e.load_sources();pool,provenance=e.build_pool(q,results,sources)
    saved=e.validate_pool(rows(OUT/'evaluation/blind_judgment_pool.jsonl'))
    check(pool==saved,'current source/query/context pool differs')
    check(len(pool)==125 and sum(len(p['contexts']) for p in pool.values())==146,'pool dose differs')
    check(provenance==rows(OUT/'evaluation/judgment_provenance.jsonl'),'provenance changed')
    check(not rows(OUT/'evaluation/remaining_pool.jsonl'),'pending semantic judgments')
    judgments=e.unique(rows(OUT/'evaluation/validated_judgments.jsonl'),'pair_id','judgment')
    fresh,perquery=e.compute_metrics(q,results,pool,judgments)
    metrics=obj(OUT/'evaluation/metrics.json')
    check(metrics['status']=='complete' and metrics['metrics']==fresh['metrics'],'metrics not reproducible')
    check(perquery==rows(OUT/'evaluation/per_query_metrics.jsonl'),'per-query metrics not reproducible')
    check(metrics['judgments_sha256']==sha(OUT/'evaluation/validated_judgments.jsonl'),'judgment SHA changed')
    for name,expected in metrics['input_sha256'].items(): check(sha(name)==expected,'evaluation input changed: '+name)
    for p in saved.values():
        check('query_task' not in p,'author expected-help leak')
        for c in p['contexts']: check('prefix_source_unit_id' not in c and 'unit_id' not in c,'unblinded winner identity')
    counts=[]
    for arm in ('P0','P1','P2'):
        rr=[r for r in perquery if r['arm']==arm];hits=[h for r in rr for h in r['top5']]
        counts.append({'arm':arm,'denominator':110,'useful_contexts':sum(h['context_help_grade']>=2 for h in hits),
                       'covered_queries':sum(r['context_coverage_at5'] for r in rr),'context_warnings':sum(h['context_misleading_risk'] for h in hits),
                       'useful_files':sum(h['help_grade']>=2 for h in hits),'file_warnings':sum(h['misleading_risk'] for h in hits),
                       'background_slots':sum(bool(h['returned_hit'].get('prefix')) for h in hits)})
    output={'status':'passed','verified_at_utc':datetime.now(timezone.utc).isoformat(),'source_documents':9639,'structured_units':65475,
            'protected_input_files_unchanged':16,'old_cache_files_unchanged':12,'e04_cache_files_unchanged':4,'e04_delivery_unchanged':True,
            'queries':22,'result_records':66,'prefix_units':24,'new_real_rerank_scores':2200,'frozen_real_score_reuse':2200,
            'source_verified_pairs':125,'source_verified_contexts':146,'pending_judgments':0,'actual_truncated_inputs':0,
            'p0_exact_reproduction_queries':22,'p2_identical_ranking_queries':22,'human_approved':False,'counts':counts,
            'scope':'mechanical/source/completeness verification; not a semantic acceptance or adoption decision',
            'semantic_limits':['Two expanded multi-subject return contexts need scope fixes; see return_scope_review.jsonl.',
                               'The 22 queries are diagnostic replay, not independent holdout.',
                               'Model grades and warning flags are not human confirmed error rates.']}
    (OUT/'verification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(output,ensure_ascii=False))


if __name__=='__main__': main()
