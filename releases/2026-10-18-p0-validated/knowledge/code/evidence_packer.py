"""Pack whole legal roots and registered context, before explanatory guides."""

def _joined(previous,parts):return '\n\n'.join(([previous] if previous else [])+parts)

def _source_note(source):
    validity=source.get('axes',{}).get('current_validity',{})
    cutoff=validity.get('evidence_cutoff') or validity.get('observed_at') or '未登记截止日'
    return '[来源 '+source['source_id']+'；版本 '+source.get('version_id','unknown')+'；效力证据 '+validity.get('status','unknown')+'；证据时点 '+cutoff+'；当前适用未核]'

def assemble_legal(roots,registry,scope_decisions,guide_blocks,*,budget_chars):
    if type(budget_chars) is not int or not 1<=budget_chars<=8000:raise ValueError('legal budget must be 1..8000 chars')
    if not isinstance(roots,list) or any(not isinstance(a,str) or a not in registry.articles for a in roots) or len(set(roots))!=len(roots):raise ValueError('unique registered roots required')
    if any(a not in scope_decisions or scope_decisions[a].get('decision') not in ['matched','conditional','mismatch'] for a in registry.articles):raise ValueError('complete scope decisions required')
    if not isinstance(guide_blocks,list) or any(not isinstance(g,(list,tuple)) or len(g)!=2 or not isinstance(g[0],str) or not isinstance(g[1],str) for g in guide_blocks):raise ValueError('guide blocks required')
    intro='资料为已存法规文本/阅读快照，非官网原始文件；效力/历史适用与当前事实未核准。范围匹配只用于本次阅读选择。'
    closure=registry.dependency_closure(roots) if roots else dict(resolved=[],missing=[],unread=[],status='partial')
    text='';included=[];sources=[];groups=[];excluded=set();budget_omitted=set();unresolved=set(closure['missing'])|set(closure['unread'])
    order=sorted(enumerate(roots),key=lambda item:(0 if scope_decisions[item[1]]['decision']=='matched' else 1,item[0]))
    for _,root in order:
        if scope_decisions[root]['decision']=='mismatch':
            excluded.add(root);groups.append(dict(root_article_id=root,status='scope_excluded',included_ids=[]));continue
        group=registry.dependency_closure([root]);unresolved.update(group['missing']);unresolved.update(group['unread'])
        bad=[a for a in group['resolved'] if scope_decisions[a]['decision']=='mismatch'];excluded.update(bad)
        ids=[a for a in group['resolved'] if a not in bad and a not in included]
        parts=[];new_sources=[]
        if not text:parts.append(intro)
        for aid in ids:
            article=registry.articles[aid];sid=article['source_id']
            if sid not in sources and sid not in new_sources:
                parts.append(_source_note(registry.sources[sid]));new_sources.append(sid)
            status='范围相符但适用未核' if scope_decisions[aid]['decision']=='matched' else '条件候选，适用待核'
            parts.append('[法规 '+aid+'；'+status+']\n'+article['text'])
        proposed=_joined(text,parts)
        if len(proposed)<=budget_chars:
            text=proposed;included.extend(ids);sources.extend(new_sources)
            groups.append(dict(root_article_id=root,status='included' if not bad and group['status']=='complete' else 'included_with_scope_or_dependency_limits',included_ids=ids,scope_excluded_context=bad))
        else:
            budget_omitted.update(ids);groups.append(dict(root_article_id=root,status='budget_omitted_whole_group',included_ids=[],unread_ids=ids,required_chars=len(proposed)-len(text)))
    kept_guides=[];omitted_guides=[]
    for gid,body in guide_blocks:
        parts=([intro] if not text else [])+[body]
        proposed=_joined(text,parts)
        if len(proposed)<=budget_chars:text=proposed;kept_guides.append(gid)
        else:omitted_guides.append(gid)
    # A later root can supply context that an earlier too-large group had omitted.
    budget_omitted.difference_update(included)
    unresolved.update(a for a in closure['resolved'] if a not in included and a not in excluded)
    next_read=sorted((budget_omitted|unresolved)-set(excluded)-set(included))
    # The joint limit is diagnostic: later per-root closures can supply its
    # initially unread IDs. Compute final coverage from the actual union.
    partial=bool(next_read or omitted_guides or excluded or not roots)
    return dict(text=text,used_chars=len(text),budget_chars=budget_chars,included_article_ids=included,included_guide_ids=kept_guides,
        included_source_ids=sources,scope_excluded_article_ids=sorted(excluded),budget_omitted_article_ids=sorted(budget_omitted),
        omitted_guide_ids=omitted_guides,next_read_article_ids=next_read,dependency_closure=closure,groups=groups,
        coverage_status='partial' if partial else 'complete_for_requested_registered_items',
        assembled_dependency_status='partial' if next_read or excluded or not roots else 'complete_for_requested_registered_items',
        current_input_facts_assessed=False,legal_applicability_confirmed=False,human_approved=False,
        model_text_policy='Use this text with separately returned case_text; structured provenance is not additional normative evidence')
