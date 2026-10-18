"""Offline KB handoff consistency checks; not an Agent or legal classifier."""
def mechanism_status(rule,assessment,current_sources):
    required={p['predicate_id'] for p in rule['predicates'] if p.get('required_for_risk')}
    given=assessment.get('predicates',[])
    mapping={p['predicate_id']:p for p in given}
    if len(mapping)!=len(given) or set(mapping)!=required:raise ValueError('required predicate set mismatch')
    for pid,p in mapping.items():
        if p.get('status') not in ['met','not_met','unknown']:raise ValueError('invalid condition status')
        if not isinstance(p.get('reason'),str) or not p['reason'].strip():raise ValueError('condition reason missing')
        evidence=p.get('evidence',[])
        if p['status'] in ['met','not_met'] and not evidence:raise ValueError('determinate condition needs current facts')
        for e in evidence:
            if e.get('origin') not in ['current_input','scenario_given_fact']:raise ValueError('case or rule is not a current fact')
            sid=e['source_id']
            if sid not in current_sources or not isinstance(e.get('start'),int) or not isinstance(e.get('end'),int):raise ValueError('unknown current source/range')
            text=current_sources[sid];start,end=e['start'],e['end']
            if not 0<=start<end<=len(text) or text[start:end]!=e.get('quote'):raise ValueError('current fact quote mismatch')
    status='supported' if all(p['status']=='met' for p in mapping.values()) else 'not_supported' if any(p['status']=='not_met' for p in mapping.values()) else 'unknown'
    if assessment.get('mechanism_state')!=status:raise ValueError('claimed mechanism state contradicts condition evidence')
    return dict(mechanism_id=rule['mechanism_id'],mechanism_state=status,
                alert_candidate=assessment.get('alert_candidate',False),legal_determination=False,
                canonical_label_is_automatic=False,semantic_fact_judgment_independently_verified=False)
