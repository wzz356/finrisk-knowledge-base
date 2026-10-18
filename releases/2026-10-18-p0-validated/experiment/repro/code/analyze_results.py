"""Score only after both fixed inference phases terminate; never rerun inference."""
from collections import Counter
from effect_common import *
from protocol import validate_result
from analysis_adapter import normalize_prediction,group_bootstrap
from scoring import score_evaluation

def main():
    verify(read(OUT/'contracts/pre_inference_freeze.json')['sha256'])
    # Require BOTH arms and BOTH splits terminal before opening true references.
    accepted={};jobs={};audit=[];marks={}
    for split in ('development','holdout'):
        phase=split+'_judgment';folder=OUT/'api'/phase;mark=read(folder/'completion.json');marks[phase]=mark
        if not mark['terminal'] or not mark['all_tasks_attempted']:raise ValueError('fixed inference not terminal')
        jp=OUT/'api_jobs'/(phase+'.jsonl');verify(read(jp.with_suffix('.freeze.json'))['sha256'])
        if sha(jp)!=mark['jobs_sha256'] or sha(folder/'accepted.jsonl')!=mark['accepted_sha256']:raise ValueError('job/result binding differs')
        for j in rows(jp):jobs[j['pair_id']]=j
        for r in rows(folder/'accepted.jsonl'):
            j=jobs[r['pair_id']]
            if canonical_sha(j['body'])!=r['base_payload_sha256']:raise ValueError('response did not belong to frozen request')
            accepted[r['pair_id']]={**r,'parsed':validate_result(j,r['parsed'])}
        audit.extend(rows(OUT/'audit'/(phase+'_map.jsonl')))
    mapping=list(rows(DATA/'reference/mapping.jsonl'));byopaque={m['opaque_id']:m for m in mapping}
    qs={q['opaque_id']:q['text'] for q in input_queries()}
    refs=list(rows(DATA/'reference/expected.jsonl'));byqid={r['query_id']:r for r in refs}
    preds=[];comparisons=[]
    for a in audit:
        m=byopaque[a['opaque_id']];j=jobs[a['pair_id']]
        if textsha(qs[a['opaque_id']])!=a['current_text_sha256'] or j['data']['current_text']!=qs[a['opaque_id']] or byqid[m['query_id']]['text_sha256']!=textsha(qs[a['opaque_id']]):raise ValueError('query/answer alignment differs')
        p=normalize_prediction(j,accepted.get(a['pair_id']),m['query_id'],a['arm']);preds.append(p)
    if len(preds)!=72 or len({(p['query_id'],p['arm']) for p in preds})!=72:raise ValueError('36 x 2 fixed denominator required')
    normalized_map=[{**m,'analysis_set':{'main_analysis':'main','boundary_challenge':'boundary'}[m['analysis_set']]} for m in mapping]
    report=score_evaluation(refs,normalized_map,preds);indexed={(p['query_id'],p['arm']):p for p in preds}
    for m in normalized_map:
        qid=m['query_id'];r=byqid[qid];o=indexed[qid,'old'];n=indexed[qid,'new']
        comparisons.append(dict(query_id=qid,opaque_id=m['opaque_id'],split=m['split'],analysis_set=m['analysis_set'],group_id=m['group_id'],
            expected_state=r['overall_state'],old_state=o['state'],new_state=n['state'],old_correct=o['valid'] and o['state']==r['overall_state'],new_correct=n['valid'] and n['state']==r['overall_state'],
            reference_mechanism_ids=r['mechanism_ids'],old_mechanism_ids=o['mechanism_ids'],new_mechanism_ids=n['mechanism_ids'],uncertain_mechanism_ids=r['uncertain_mechanism_ids'],
            old_reason=o['reason'],new_reason=n['reason'],reference_status=r['adjudication_status']))
    for split in ('development','holdout'):
        for aset in ('main','boundary'):
            points=[p for p in comparisons if p['split']==split and p['analysis_set']==aset]
            report['strata'][split][aset]['group_bootstrap_accuracy_delta']=group_bootstrap(points)
    case_pairs={}
    for a in audit:case_pairs.setdefault(a['opaque_id'],{})[a['arm']]=a
    if not all(v['old']['case_text_sha256']==v['new']['case_text_sha256'] and v['old']['displayed_case_ids']==v['new']['displayed_case_ids'] for v in case_pairs.values()):raise ValueError('paired case context changed')
    assembly={}
    for arm in ('old','new'):
        aa=[a for a in audit if a['arm']==arm]
        assembly[arm]=dict(queries=len(aa),case_chars=dict(min=min(a['case_chars'] for a in aa),max=max(a['case_chars'] for a in aa),mean=sum(a['case_chars'] for a in aa)/len(aa)),
            legal_chars=dict(min=min(a['law_chars'] for a in aa),max=max(a['law_chars'] for a in aa),mean=sum(a['law_chars'] for a in aa)/len(aa)),
            displayed_articles=sum(len(a['displayed_article_ids']) for a in aa),omitted_knowledge_items=sum(len(a['omitted_knowledge_ids']) for a in aa),
            cases_shown=sum(len(a['displayed_case_ids']) for a in aa),condition_schema_chars_mean=sum(a['extra_condition_schema_chars'] for a in aa)/len(aa))
    allrecords=list(rows(OUT/'api/records.jsonl'));ledger=list(rows(OUT/'api/ledger.jsonl'));settles=[r for r in ledger if r['event']=='settle']
    reserved={r['reservation_id'] for r in ledger if r['event']=='reserve'}
    if reserved!={r['reservation_id'] for r in settles}:raise ValueError('unsettled usage remains')
    fee=dict(hard_cap_usd=2,booked_peak_bound_usd=sum(r['booked_usd'] for r in settles),actual_invoice_verified=False,unknown_usage_count=sum(r['unknown_usage'] for r in settles),
        attempts=len(allrecords),unique_tasks=len({r['pair_id'] for r in allrecords}),by_status=dict(Counter(r['status'] for r in allrecords)),
        by_kind=dict(Counter(r['kind'] for r in allrecords)),returned_models=dict(Counter(r['returned_model'] for r in allrecords)),
        prompt_tokens=sum((r.get('usage') or {}).get('prompt_tokens',0) for r in allrecords),completion_tokens=sum((r.get('usage') or {}).get('completion_tokens',0) for r in allrecords),
        first_utc=min(r['utc'] for r in allrecords),last_utc=max(r['utc'] for r in allrecords))
    if fee['booked_peak_bound_usd']>2+1e-9:raise ValueError('fee cap exceeded')
    ranking=list(rows(OUT/'retrieval/rankings_development.jsonl'))+list(rows(OUT/'retrieval/rankings_holdout.jsonl'))
    diagnostics=dict(common_case_context_identical_for_all36=True,assembly=assembly,fee=fee,
        rerank_quote_invalid_pairs=sum(r['invalid_rerank_quotes'] for r in ranking),rerank_total_pairs=3600,
        quote_invalid_scores_retained_without_semantic_retries=True,
        primary_confirmation='holdout/main, 12 queries; model silver, not expert gold',global_retrieval_recall_measured=False,
        all_scope_decisions_semantically_expert_reviewed=False,mechanical_citations_do_not_measure_semantic_sufficiency=True)
    save(OUT/'results/normalized_predictions.jsonl',preds,True);save(OUT/'results/per_query_comparison.jsonl',comparisons,True)
    save(OUT/'results/metrics.json',report);save(OUT/'results/diagnostics.json',diagnostics)
    save(OUT/'results/scoring_source_lock.json',dict(created_utc=utc(),sha256={str(p):sha(p) for p in (Path(__file__),WORK/'analysis_adapter.py',WORK/'scoring.py')}))
    print(json.dumps(dict(scored_queries=36,predictions=72,fee=fee,holdout_main=report['strata']['holdout']['main']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
