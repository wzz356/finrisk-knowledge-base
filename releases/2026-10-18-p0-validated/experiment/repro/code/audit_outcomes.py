"""Post-hoc diagnostics only: flag scope/navigation/condition issues, no relabeling."""
from collections import Counter
from effect_common import *

def main():
    # Existence of final metrics means both inference splits were terminal.
    read(OUT/'results/metrics.json')
    refs={r['query_id']:r for r in rows(DATA/'reference/expected.jsonl')};mapping={r['opaque_id']:r for r in rows(DATA/'reference/mapping.jsonl')}
    preds={(p['query_id'],p['arm']):p for p in rows(OUT/'results/normalized_predictions.jsonl')}
    audits={};cov={};jobs={}
    for split in ('development','holdout'):
        for a in rows(OUT/'audit'/(split+'_judgment_map.jsonl')):audits[a['opaque_id'],a['arm']]=a
        for r in rows(OUT/'audit'/('coverage_'+split+'.jsonl')):cov[r['opaque_id']]=r['coverage']
        for j in rows(OUT/'api_jobs'/(split+'_judgment.jsonl')):jobs[j['pair_id']]=j
    diagnostics=[];review=[]
    for oid,m in mapping.items():
        ref=refs[m['query_id']];required=set(ref['mechanism_ids'])|set(ref['uncertain_mechanism_ids']);a=audits[oid,'new'];d=jobs[a['pair_id']]['data']
        nav=set(a['candidate_mechanism_ids']);missing=sorted(required-nav)
        arms={}
        for arm in ('old','new'):
            aa=audits[oid,arm];p=preds[m['query_id'],arm];wrong=[]
            for r in ref['required_predicate_assessments']:
                got=p['predicates'].get(r['predicate_id'])
                if got is None or got['status']!=r['status']:wrong.append(dict(predicate_id=r['predicate_id'],expected=r['status'],predicted=got,reference_evidence=r['evidence']))
            arms[arm]=dict(state=p['state'],mechanism_ids=p['mechanism_ids'],reason=p['reason'],wrong_conditions=wrong,
                legal_article_ids=p['legal_article_ids'],case_unit_ids=p['case_unit_ids'],
                citations_flagged_mismatch_under_shared_model_scope=[i for i in p['legal_article_ids'] if a['article_scope_decisions'][i]['decision']=='mismatch'],
                displayed_articles=aa['displayed_article_ids'],omitted_knowledge=aa['omitted_knowledge_ids'])
        rec=dict(query_id=m['query_id'],opaque_id=oid,split=m['split'],analysis_set=m['analysis_set'],group_id=m['group_id'],expected_state=ref['overall_state'],
            reference_status=ref['adjudication_status'],current_text=d['current_text'],reference_mechanism_ids=ref['mechanism_ids'],uncertain_mechanism_ids=ref['uncertain_mechanism_ids'],
            candidate_mechanism_ids=sorted(nav),missing_reference_mechanism_candidates=missing,scope_facts=a['scope_facts'],reference_scope_facts=ref['scope_facts'],arms=arms,
            new_scope_excluded_article_ids=a['assembly']['scope_excluded_article_ids'],new_budget_omitted_article_ids=a['assembly']['budget_omitted_article_ids'],new_guides_shown=a['assembly']['included_guide_ids'])
        diagnostics.append(rec)
        if arms['old']['state']!=arms['new']['state'] or missing or arms['new']['state']!=ref['overall_state'] or any(v['citations_flagged_mismatch_under_shared_model_scope'] for v in arms.values()):review.append(rec)
    summary={}
    for split in ('development','holdout'):
        for aset in ('main_analysis','boundary_challenge'):
            rr=[r for r in diagnostics if r['split']==split and r['analysis_set']==aset]
            nonempty=[r for r in rr if r['reference_mechanism_ids'] or r['uncertain_mechanism_ids']]
            summary[split+'__'+aset]=dict(queries=len(rr),queries_with_reference_candidate_mechanisms=len(nonempty),
                all_reference_candidates_in_reading_list=sum(not r['missing_reference_mechanism_candidates'] for r in nonempty),
                missing_candidates=[dict(query_id=r['query_id'],ids=r['missing_reference_mechanism_candidates']) for r in rr if r['missing_reference_mechanism_candidates']],
                scope_excluded_occurrences=sum(len(r['new_scope_excluded_article_ids']) for r in rr),budget_omitted_occurrences=sum(len(r['new_budget_omitted_article_ids']) for r in rr),
                old_citation_scope_flags=sum(len(r['arms']['old']['citations_flagged_mismatch_under_shared_model_scope']) for r in rr),
                new_citation_scope_flags=sum(len(r['arms']['new']['citations_flagged_mismatch_under_shared_model_scope']) for r in rr))
    save(OUT/'results/outcome_diagnostics.jsonl',diagnostics,True);save(OUT/'results/semantic_review_queue.jsonl',review,True)
    save(OUT/'results/navigation_scope_diagnostics.json',dict(strata=summary,reading_candidate_coverage_is_not_case_recall=True,scope_flags_are_model_supplied_not_expert_legality=True))
    print(json.dumps(dict(queries=36,flagged_for_semantic_review=len(review),summary=summary),ensure_ascii=False))

if __name__=='__main__':main()
