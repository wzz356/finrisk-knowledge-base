"""Paired legal-assembly ablation; no reference answers are opened here."""
import argparse
import sys
from collections import defaultdict
from effect_common import *
from protocol import job,validate_result,JUDGMENT_SYSTEM
sys.path.insert(0,str(RUNTIME/'code'))
from knowledge_assets import KnowledgeAssets
from scope_table import load_scopes
from evidence_runtime import assemble_policy
from risk_coverage import analyze_coverage

def pack_cases(ids,read_cache,budget=4000):
    text='';kept=[];omitted=[]
    for uid in ids:
        record=read_cache[uid];block='[历史案例 '+uid+'；并列片段不合并归责，不证明当前输入事实]\n'+record['text']
        proposal=text+('\n\n' if text else '')+block
        if len(proposal)<=budget:text=proposal;kept.append(uid)
        else:omitted.append(uid)
    return text,kept,omitted

def paired_payloads(text,mids,cards,scope_facts,case_text,case_ids,old_pack,new_pack):
    pids=[p['predicate_id'] for mid in mids for p in cards[mid]['predicates']]
    if len(pids)!=len(set(pids)):raise ValueError('ambiguous candidate predicate IDs')
    common=dict(current_text=text,mechanism_ids=mids,predicate_ids=pids,
        required_by_mechanism={mid:[p['predicate_id'] for p in cards[mid]['predicates'] if p['required_for_risk']] for mid in mids},
        condition_definitions=[dict(mechanism_id=mid,predicate_id=p['predicate_id'],description=p['description'],required_for_risk=p['required_for_risk']) for mid in mids for p in cards[mid]['predicates']],
        scope_facts=scope_facts,cases=case_text,case_unit_ids=case_ids)
    results={}
    for arm,pack in [('old',old_pack),('new',new_pack)]:
        payload={**common,'laws_and_guides':pack['text'],'article_ids':pack['article_ids'],
            'coverage':dict(omitted_knowledge_ids=pack['omitted_ids'],current_business_facts_verified=False,scope_classification_origin='model_from_current_input_not_fact_approval',all_input_risks_checked=False)}
        pid='FXJ_'+canonical_sha([text,arm,payload])[:24];payload['pair_id']=pid
        results[arm]=job(pid,'judgment',payload,JUDGMENT_SYSTEM,2048)
    return results

def accepted_initial(split):
    folder=OUT/'api'/(split+'_initial');mark=read(folder/'completion.json');jp=OUT/'api_jobs'/(split+'_initial.jsonl')
    if not mark['complete'] or sha(folder/'accepted.jsonl')!=mark['accepted_sha256'] or sha(jp)!=mark['jobs_sha256']:raise ValueError('full shared initial stage not complete/bound')
    jobs={j['pair_id']:j for j in rows(jp)};accepted={r['pair_id']:r for r in rows(folder/'accepted.jsonl')}
    if set(jobs)!=set(accepted):raise ValueError('missing initial scores or scope')
    for pid,r in accepted.items():
        if r['base_payload_sha256']!=canonical_sha(jobs[pid]['body']):raise ValueError('initial response binding changed')
        validate_result(jobs[pid],r['parsed'])
    return accepted

def prepare(split):
    verify(read(OUT/'contracts/pre_inference_freeze.json')['sha256']);accepted=accepted_initial(split)
    bookkeeping={r['opaque_id']:r for r in rows(DATA/'reference/mapping.jsonl')};queries=[q for q in input_queries() if bookkeeping[q['opaque_id']]['split']==split]
    task_map={r['opaque_id']:r['pair_id'] for r in rows(OUT/'audit/initial_task_map.jsonl') if r['kind']=='scope' and r['split']==split}
    candidates=defaultdict(list)
    for m in rows(OUT/'retrieval/candidate_map.jsonl'):candidates[m['opaque_id']].append(m)
    read_cache={}
    for r in rows(OUT/'retrieval/shared_case_reads.jsonl'):
        if canonical_sha(r['read_result'])!=r['read_result_sha256']:raise ValueError('shared case read cache changed')
        read_cache[r['unit_id']]=r['read_result']
    assets=KnowledgeAssets(RUNTIME/'assets',read(RUNTIME/'contracts/asset_lock.json'));scope_path=RUNTIME/'policy/article_scopes.jsonl'
    scopes=load_scopes(scope_path,read(RUNTIME/'contracts/runtime_manifest.json')['files']['policy/article_scopes.jsonl']['sha256'],assets)
    sys.path.insert(0,str(SEALED/'code'));from knowledge_facade import KnowledgeFacade
    legacy=KnowledgeFacade(SEALED,read(SEALED/'case_reader/final_lock.json'),expected_knowledge_manifest_sha256=sha(SEALED/'expanded/contracts/knowledge_manifest.json'),profile='expanded')
    jobs=[];audit=[];rankings=[];coverage_rows=[]
    for q in queries:
        key=q['opaque_id'];rows_for_q=candidates[key]
        if len(rows_for_q)!=100:raise ValueError('expected shared 100 candidates')
        ranked=sorted([{**r,'score':accepted[r['pair_id']]['parsed']['score']} for r in rows_for_q],key=lambda r:(-r['score'],r['unit_id']))
        seen=set();files=[]
        for r in ranked:
            if r['file_id'] in seen:continue
            seen.add(r['file_id']);files.append({**r,'rank':len(files)+1})
        if len(files)<20:raise ValueError('fewer than 20 distinct shared documents; no default completion')
        rankings.append(dict(opaque_id=key,ranking=files,score_count=100,invalid_rerank_quotes=sum(accepted[r['pair_id']]['parsed'].get('quotation_valid') is False for r in rows_for_q)))
        case_text,case_ids,omitted_cases=pack_cases([r['unit_id'] for r in files[:20]],read_cache)
        coverage=analyze_coverage(q['text'],assets.cards);mids=coverage['candidate_mechanism_ids'] or coverage['fallback_readable_mechanism_ids']
        facts=accepted[task_map[key]]['parsed']['scope_facts']
        old=legacy.get_evidence_bundle(mids,[],budget_chars=8000,case_budget=4000,law_budget=4000)
        new,validated,decisions=assemble_policy(assets,scopes,mids,current_text=q['text'],scope_facts=facts,law_budget=4000)
        old_pack=dict(text=old['law_and_guide_text'],article_ids=[a for a in old['included_legal_and_guide_ids'] if not a.startswith('GUIDE:')],omitted_ids=old['coverage']['omitted_legal_article_ids']+old['coverage']['omitted_guide_ids'])
        new_pack=dict(text=new['text'],article_ids=new['included_article_ids'],omitted_ids=new['next_read_article_ids']+['GUIDE:'+a for a in new['omitted_guide_ids']])
        pair=paired_payloads(q['text'],mids,assets.cards,facts,case_text,case_ids,old_pack,new_pack)
        order=['old','new'] if int(textsha(q['text'])[:2],16)%2==0 else ['new','old']
        for arm in order:
            j=pair[arm];jobs.append(j);pack=old_pack if arm=='old' else new_pack
            audit.append(dict(opaque_id=key,arm=arm,pair_id=j['pair_id'],current_text_sha256=textsha(q['text']),case_text_sha256=textsha(case_text),case_chars=len(case_text),displayed_case_ids=case_ids,
                omitted_case_ids=omitted_cases,law_chars=len(pack['text']),displayed_article_ids=pack['article_ids'],omitted_knowledge_ids=pack['omitted_ids'],candidate_mechanism_ids=mids,
                scope_facts=validated,article_scope_decisions=decisions if arm=='new' else None,assembly=new if arm=='new' else old,
                extra_condition_schema_chars=len(json.dumps(j['data']['condition_definitions'],ensure_ascii=False)),context_budget_counts='only case_text+laws_and_guides; identical condition/output schema and scope facts are additional input fields for both arms'))
        assert pair['old']['data']['cases']==pair['new']['data']['cases'] and pair['old']['data']['condition_definitions']==pair['new']['data']['condition_definitions']
        coverage_rows.append(dict(opaque_id=key,coverage=coverage))
    if len(jobs)!=36:raise ValueError('18 x 2 paired judgments required')
    phase=split+'_judgment';p=OUT/'api_jobs'/(phase+'.jsonl');save(p,jobs,True)
    save(p.with_suffix('.freeze.json'),dict(sha256={str(p):sha(p)}));save(OUT/'audit'/(phase+'_map.jsonl'),audit,True)
    save(OUT/'retrieval'/('rankings_'+split+'.jsonl'),rankings,True);save(OUT/'audit'/('coverage_'+split+'.jsonl'),coverage_rows,True)
    receipt=dict(prepared=36,queries=18,old_new_case_text_identical=True,old_new_condition_definitions_identical=True,model_reference_answers_read=False,new_API_calls=0)
    save(OUT/'audit'/(phase+'_preflight.json'),receipt);print(json.dumps(receipt),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('split',choices=['development','holdout']);a=p.parse_args();prepare(a.split)
