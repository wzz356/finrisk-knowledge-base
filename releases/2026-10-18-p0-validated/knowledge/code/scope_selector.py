"""Compare supplied scope with a reviewed side table, never decide legality."""
AXES={
    'actor':{'insurer','insurance_agent','insurance_broker','insurance_salesperson','policyholder','insured','beneficiary','insurance_participant','consumer','general','unknown'},
    'product':{'universal_life','investment_linked','participating','all_insurance','personal_insurance','property_insurance','general','unknown'},
    'stage':{'contract_signing','post_sale_review','pre_sale','telemarketing','information_disclosure','surrender','claims','general','unknown'}}

def validate_scope_facts(facts,current_text):
    if facts is None:facts={}
    if not isinstance(facts,dict) or not set(facts)<=set(AXES):raise ValueError('unknown scope fact axis')
    values={axis:'unknown' for axis in AXES};evidence={}
    for axis,item in facts.items():
        if not isinstance(item,dict) or item.get('value') not in AXES[axis]:raise ValueError('invalid scope value')
        if item.get('origin')!='current_input':raise ValueError('scope evidence must be from current input')
        value=item['value'];quote=item.get('quote');start=item.get('start');end=item.get('end')
        if value=='unknown' and not quote:
            if not isinstance(item.get('reason'),str) or not item['reason'].strip():raise ValueError('unknown scope needs reason')
        else:
            if not isinstance(current_text,str) or not current_text or not isinstance(quote,str) or not quote or type(start) is not int or type(end) is not int or not 0<=start<end<=len(current_text) or current_text[start:end]!=quote:raise ValueError('invalid current-input scope quotation')
        values[axis]=value;evidence[axis]=dict(item)
    return dict(values=values,evidence=evidence,literal_references_checked=True,current_business_facts_verified=False,
        classification_origin='caller_supplied_scope_not_independent_semantic_judgment')

def _axis_match(axis,registered,value):
    if not isinstance(registered,list) or not registered or any(v not in AXES[axis] for v in registered):raise ValueError('invalid registered scope')
    tags=set(registered)
    if value in ['unknown','general'] or tags&{'unknown','general'}:return 'conditional'
    if value in tags:return 'matched'
    if axis=='product' and 'all_insurance' in tags:return 'matched'
    if axis=='actor':
        organizations={'insurer','insurance_agent','insurance_broker'}
        if value in organizations and tags<=organizations:return 'mismatch'
        return 'conditional'  # Conduct actor and accountable entity are different axes in law.
    if axis=='product':
        designs={'universal_life','investment_linked','participating'}
        if value in designs and tags<=designs:return 'mismatch'
        if value=='personal_insurance' and tags=={'property_insurance'}:return 'mismatch'
        if value=='property_insurance' and tags=={'personal_insurance'}:return 'mismatch'
        return 'conditional'
    # Time, channel and disclosure obligations overlap; no validated disjoint
    # stage relation is registered in this coarse enumeration.
    return 'conditional'

def match_article(scope,validated_facts):
    if not isinstance(scope,dict) or scope.get('scope_status') not in ['direct_literal','conditional','broader','unknown']:raise ValueError('unknown registered scope status')
    if not isinstance(validated_facts,dict) or validated_facts.get('literal_references_checked') is not True or set(validated_facts.get('values',{}))!=set(AXES):raise ValueError('validated scope facts required')
    axes={axis:_axis_match(axis,scope[axis+'_scope'],validated_facts['values'][axis]) for axis in AXES}
    basis=scope.get('assertion_basis',{})
    # An unknown axis does not erase a separately explicit subject/product boundary.
    mismatched=[axis for axis,value in axes.items() if value=='mismatch' and
        (basis.get(axis)=='direct_literal' or (not basis and scope['scope_status']=='direct_literal'))]
    decision='mismatch' if mismatched else ('matched' if scope['scope_status']=='direct_literal' and all(v=='matched' for v in axes.values()) else 'conditional')
    return dict(article_id=scope['article_id'],decision=decision,axes=axes,mismatched_axes=mismatched,
        current_business_facts_verified=False,legal_applicability_confirmed=False,
        decision_identity='candidate_reading_priority_only',
        limitation='mismatch excludes direct-use assembly under supplied scope; article remains readable by ID; no legal verdict')
