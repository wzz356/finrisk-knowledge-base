"""Prepare all input-only API tasks and the exact scoped request plan."""
from effect_common import *
from protocol import job,SCOPE_SYSTEM,JUDGMENT_SYSTEM

def main():
    verify(read(OUT/'retrieval/freeze.json')['sha256']);qs=input_queries()
    private={r['opaque_id']:r for r in rows(DATA/'reference/mapping.jsonl')}
    if set(private)!={q['opaque_id'] for q in qs}:raise ValueError('anonymous bookkeeping map differs')
    packets={r['pair_id']:r for r in rows(OUT/'retrieval/rerank_packets.jsonl')};maps=list(rows(OUT/'retrieval/candidate_map.jsonl'))
    byquery={q['opaque_id']:[m for m in maps if m['opaque_id']==q['opaque_id']] for q in qs}
    rules=(OUT/'retrieval/rerank_rules.md').read_text(encoding='utf-8')+'\n只评分这一对输入，输出一个JSON对象。reason和limitation各不超过40字。'
    jobs_by_split={'development':[],'holdout':[]};task_map=[]
    for q in qs:
        key=q['opaque_id'];split=private[key]['split'];pid='FXS_'+textsha(SCOPE_SYSTEM+'\n'+q['text'])[:24]
        jobs_by_split[split].append(job(pid,'scope',dict(pair_id=pid,current_text=q['text']),SCOPE_SYSTEM,512))
        task_map.append(dict(pair_id=pid,opaque_id=key,kind='scope',split=split))
        for m in byquery[key]:
            packet=packets[m['pair_id']];j=job(packet['pair_id'],'rerank',packet,rules,384)
            jobs_by_split[split].append(j);task_map.append(dict(pair_id=j['pair_id'],opaque_id=key,kind='rerank',split=split))
    for split,jobs in jobs_by_split.items():
        if len(jobs)!=1818:raise ValueError('18 scopes + 1800 scores per split required')
        path=OUT/'api_jobs'/(split+'_initial.jsonl');save(path,jobs,True);save(path.with_suffix('.freeze.json'),dict(sha256={str(path):sha(path)}))
    save(OUT/'audit/initial_task_map.jsonl',task_map,True)
    (OUT/'contracts/scope_system.txt').write_text(SCOPE_SYSTEM,encoding='utf-8');(OUT/'contracts/judgment_system.txt').write_text(JUDGMENT_SYSTEM,encoding='utf-8')
    plan=dict(scope=SCOPE,model='deepseek-flash',endpoint='https://api.deepseek.com/chat/completions',max_unique_tasks=dict(rerank=3600,scope=36,judgment=72),max_attempts_per_task=3,
        proposed_hard_cap_usd=2,all_attempts_share_cap=True,max_workers=12,unknown_usage_booked_at_full_reservation=True,unknown_transport_retry_within_attempt_cap=True,
        data_sent=['36 frozen synthetic business inputs','public penalty excerpts in shared RRF100','public legal text and model-authored reading guides','input-only conservative scope extraction'],
        data_excluded=['reference answers','reference grades','query_id','opaque_id','group_id','split','analysis_set','arm','credential contents'],
        arms=['old expanded legal assembly','new scope-aware whole legal assembly'],shared_case_budget=4000,legal_budget_per_arm=4000,
        common_controls=['same BM25/BGE/RRF candidates and DeepSeek ranking','same uncapped current-input reading candidates','same condition definitions and scope extraction','same actual case_text and displayed case IDs','same model and output protocol'],
        retrieval_metrics_not_measured=['global true Recall','new-query MRR/NDCG without independently labelled case reference'],
        protocol_source=str(DATA/'protocol.md'),fee_protocol_source=str(ROOT/'outputs/FinRisk_法规库实施规划_20261017/实验协议.md'))
    save(OUT/'contracts/api_request_plan.json',plan)
    config=dict(scope=SCOPE,version='pre-API-v1',model='deepseek-flash',temperature=0,thinking='disabled',case_budget=4000,law_budget=4000,route_top_k=100,rrf_c=60,rrf_weights=[1,1],rank_tie='ascending stable unit_id',source_document_collapse='highest unit score then stable unit ID',judgment_candidate_documents=20,
        mechanism_selection='frozen input-only risk_coverage candidates, no two-mechanism cap; all twelve only when unmapped',
        conditions='same immutable card definitions for both arms, no expected states',comparison='legal assembly only; shared full corpus reader and navigation',
        primary_reference_rule='24 main_analysis; boundary_reference_pending 12 only in separate challenge report',
        split_protocol='18 development first; exact same frozen configuration for single 18 holdout run; no planned tuning or answer revision',
        paid_approval_pending=True)
    save(OUT/'contracts/experiment_config.json',config)
    print(json.dumps(dict(prepared_initial_tasks=sum(map(len,jobs_by_split.values())),maximum_judgments=72,maximum_scope_extractions=36,maximum_rerank_scores=3600,new_API_calls=0),ensure_ascii=False))

if __name__=='__main__':main()
