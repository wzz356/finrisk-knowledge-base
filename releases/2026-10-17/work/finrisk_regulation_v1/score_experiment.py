"""Offline scoring: missing outputs are failures, unjudged legal items are never grade zero."""
import json
from collections import Counter
from source_registry import ROOT,OUT,save
from rule_cards import rows

STATES=['risk','no_clear_risk','insufficient']

def div(n,d):return n/d if d else 0.
def f1(p,r):return div(2*p*r,p+r)


def classification_metrics(references,predictions,official_tags):
    n=len(references); tp=fp=fn=0; correct=missing=0; extra=0;core_hits=0
    per_labels={t:Counter() for t in official_tags}; per_states={s:Counter() for s in STATES}
    normal_fp=unknown_hit=0;normal_count=unknown_count=0;invalid_tags=0
    for ref in references:
        p=predictions.get(ref['query_id']); y=ref['expected_state']
        state=p.get('state') if p else '__MISSING__'
        tags=set(p.get('risk_labels',[])) if p else set()
        required=set(ref['required_labels']);optional=set(ref.get('optional_labels',[]))
        missing+=p is None;correct+=state==y
        for s in STATES:
            per_states[s]['tp']+=y==state==s
            per_states[s]['fp']+=state==s and y!=s
            per_states[s]['fn']+=y==s and state!=s
            per_states[s]['support']+=y==s
        tp+=state==y=='risk';fp+=state=='risk' and y!='risk';fn+=y=='risk' and state!='risk'
        normal_count+=y=='no_clear_risk';normal_fp+=y=='no_clear_risk' and state=='risk'
        unknown_count+=y=='insufficient';unknown_hit+=y==state=='insufficient'
        extra+=len(tags-required-optional)
        invalid_tags+=len(tags-set(official_tags))
        groups=ref.get('required_label_groups') or [[t] for t in required]
        core_hits+=state==y and all(tags&set(g) for g in groups)
        for t in official_tags:
            if t in optional and t not in required:continue
            per_labels[t]['tp']+=t in tags and t in required
            per_labels[t]['fp']+=t in tags and t not in required
            per_labels[t]['fn']+=t not in tags and t in required
    state_scores={s:dict(support=v['support'],precision=div(v['tp'],v['tp']+v['fp']),recall=div(v['tp'],v['tp']+v['fn'])) for s,v in per_states.items()}
    for v in state_scores.values():v['f1']=f1(v['precision'],v['recall'])
    label_tp=sum(v['tp'] for v in per_labels.values());label_fp=sum(v['fp'] for v in per_labels.values())+invalid_tags;label_fn=sum(v['fn'] for v in per_labels.values())
    lp,lr=div(label_tp,label_tp+label_fp),div(label_tp,label_tp+label_fn)
    per_tag={t:dict(precision=div(v['tp'],v['tp']+v['fp']),recall=div(v['tp'],v['tp']+v['fn']),
                   f1=div(2*v['tp'],2*v['tp']+v['fp']+v['fn']),**v) for t,v in per_labels.items()}
    active=[v for v in per_tag.values() if v.get('tp',0)+v.get('fn',0)>0]
    return dict(questions=n,state_correct=correct,state_accuracy=div(correct,n),missing_outputs=missing,
       state_macro_f1=sum(v['f1'] for v in state_scores.values())/3,per_state=state_scores,
       risk_precision=div(tp,tp+fp),risk_recall=div(tp,tp+fn),risk_f1=div(2*tp,2*tp+fp+fn),
       normal_questions=normal_count,normal_false_positives=normal_fp,normal_false_positive_rate=div(normal_fp,normal_count),
       insufficient_questions=unknown_count,insufficient_correct=unknown_hit,insufficient_recognition_rate=div(unknown_hit,unknown_count),
       label_micro_precision=lp,label_micro_recall=lr,label_micro_f1=f1(lp,lr),
       label_macro_f1_all_official=div(sum(v['f1'] for v in per_tag.values()),len(official_tags)),
       label_macro_precision_all_official=div(sum(v['precision'] for v in per_tag.values()),len(official_tags)),
       label_macro_recall_all_official=div(sum(v['recall'] for v in per_tag.values()),len(official_tags)),
       label_macro_f1_reference_positive_tags=div(sum(v['f1'] for v in active),len(active)),
       label_macro_precision_reference_positive_tags=div(sum(v['precision'] for v in active),len(active)),
       label_macro_recall_reference_positive_tags=div(sum(v['recall'] for v in active),len(active)),
       invalid_definite_label_count=invalid_tags,score_implementation_version=2,
       extra_definite_label_count=extra,extra_definite_labels_per_query=div(extra,n),
       state_and_core_label_group_match=div(core_hits,n),per_tag=per_tag,
       reference_status='model_silver_not_expert_gold',optional_tags_not_false_positives=True)


def law_metrics(references,law_rows):
    by_id={r['query_id']:r for r in law_rows};denom=len(references)
    totals={str(k):0. for k in [1,5,10,20]}; expanded={str(k):0. for k in [1,5,10,20]}
    top1=mrr=0.;details=[]
    from rule_cards import dependency_closure
    dependencies=json.loads((OUT/'article_dependencies.json').read_text(encoding='utf-8'))
    for ref in references:
        r=by_id[ref['query_id']]; order=[h['article_id'] for h in r['ranking']]
        groups=[set(g) for g in ref['acceptable_primary_basis_groups']]
        direct=set().union(*groups)
        first=next((i for i,key in enumerate(order[:20],1) if key in direct),None)
        top1+=bool(order and order[0] in direct);mrr+=1/first if first else 0
        for k in [1,5,10,20]:
            keys=set(order[:k]);totals[str(k)]+=div(sum(bool(g&keys) for g in groups),len(groups))
            # Definition/exception expansion only: generic rule-support expansion reported separately at Top5.
            keys_exp=set(dependency_closure(list(keys),dependencies)) if keys and keys<=set(dependencies) else keys
            expanded[str(k)]+=div(sum(bool(g&keys_exp) for g in groups),len(groups))
        details.append(dict(query_id=ref['query_id'],first_registered_basis_rank=first,
                 primary_basis_count_in_top5=len(direct&set(order[:5])),actual_context_count=len(r['articles']),
                 actual_context_registered_basis_present=bool(direct&{a['article_id'] for a in r['articles']}),
                 missing_dependency_ids=r.get('missing_dependency_ids',[])))
    return dict(questions=denom,necessary_basis_group_coverage={k:div(v,denom) for k,v in totals.items()},
         after_definition_exception_expansion={k:div(v,denom) for k,v in expanded.items()},
         Top1=div(top1,denom),MRR_at_20=div(mrr,denom),NDCG=None,
         NDCG_status='未完成Top20逐对分级，不将未标注视为0',details=details,
         metric_scope='预登记最小依据组覆盖，非真实全库Recall；跨度正确不代表适用正确',
         dependency_completeness=div(sum(not r.get('missing_dependency_ids') for r in details),denom))


def main():
    refs=rows(OUT/'experiment/confirm_references.jsonl');law=rows(OUT/'experiment/law_retrieval.jsonl')
    value=law_metrics(refs,law)
    target=OUT/'experiment/law_basis_coverage.json'
    if target.exists():
        if json.loads(target.read_text(encoding='utf-8'))!=value: raise ValueError('frozen law result changed')
    else:save(target,value)
    tags=[r['risk_tag'] for r in json.loads((ROOT/'outputs/FinRisk_正式测试集V2_20261017/official_labels.json').read_text(encoding='utf-8-sig'))]
    readiness=[]
    for phase in ['dev','confirm']:
        path=OUT/'api'/phase/'accepted.jsonl'
        if not path.exists():
            readiness.append(dict(phase=phase,status='not_run',classification_metrics=None));continue
        packets=rows(OUT/'experiment'/('dev_packets.jsonl' if phase=='dev' else 'confirm_packets.jsonl'))
        arms={p['task_id']:p['arm'] for p in packets}
        reference=rows(OUT/'experiment'/('dev_references.jsonl' if phase=='dev' else 'confirm_references.jsonl'))
        predictions=rows(path)
        result={a:classification_metrics(reference,{r['parsed']['query_id']:r['parsed'] for r in predictions if arms[r['task_id']]==a},tags) for a in ['A','B','C']}
        target=OUT/'experiment'/(phase+'_metrics_v2.json')
        if target.exists():
            if json.loads(target.read_text(encoding='utf-8'))!=result: raise ValueError('scored result changed')
        else:save(target,result)
        readiness.append(dict(phase=phase,status='actual_outputs_scored',classification_metrics=phase+'_metrics_v2.json'))
    (OUT/'experiment/inference_status.json').write_text(json.dumps(readiness,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in value.items() if k!='details'},ensure_ascii=False))

if __name__=='__main__':main()
