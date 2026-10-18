"""Pin and replay scope assertions against sealed legal text; not a legal review."""
from runtime_common import rows,sha,textsha
from scope_selector import AXES

def load_scopes(path,expected_sha256,assets):
    if not expected_sha256 or sha(path)!=expected_sha256:raise ValueError('scope table fingerprint mismatch')
    out={};legal=assets.legal
    for row in rows(path):
        aid=row.get('article_id')
        if aid in out or aid not in legal.articles:raise ValueError('duplicate/unregistered scope article')
        article=legal.articles[aid]
        if any(row.get(k)!=article[k] for k in ('source_id','version_id','text_sha256')):raise ValueError('scope article version mismatch')
        if row.get('human_approved') is not False or row.get('research_only') is not True or row.get('review_origin')!='current_session_model':raise ValueError('scope origin changed')
        restrictions=row.get('restrictions',{})
        if restrictions.get('production_active') is not False or restrictions.get('current_business_fact_proof') is not False:raise ValueError('scope cannot prove current facts or production admission')
        if row.get('scope_status') not in {'direct_literal','conditional','broader','unknown'}:raise ValueError('invalid scope status')
        for axis in AXES:
            values=row.get(axis+'_scope')
            if not isinstance(values,list) or not values or any(v not in AXES[axis] for v in values):raise ValueError('invalid scope enumeration')
            basis=row.get('assertion_basis',{}).get(axis)
            if basis not in {'direct_literal','source_title_scope','assistant_interpretation'}:raise ValueError('invalid scope assertion basis')
            if not any(e.get('axis')==axis and e.get('basis')==basis for e in row.get('evidence',[])):raise ValueError('scope assertion lacks evidence')
        for e in row.get('evidence',[]):
            if e.get('source_type')=='article_text':
                target=legal.articles.get(e.get('article_id'))
                if not target or target['source_id']!=e.get('source_id'):raise ValueError('scope evidence article identity mismatch')
                text=target['text']
            elif e.get('source_type')=='source_title':
                if e.get('source_id') not in legal.sources:raise ValueError('scope evidence source missing')
                text=legal.sources[e['source_id']]['title']
            elif e.get('source_type')=='snapshot_text':
                name=e.get('file')
                if not isinstance(name,str):raise ValueError('scope evidence file missing')
                p=(assets.root/'legal'/name).resolve()
                if not p.is_relative_to((assets.root/'legal').resolve()):raise ValueError('scope evidence outside legal root')
                text=p.read_text(encoding='utf-8-sig')
            else:raise ValueError('unknown scope evidence representation')
            a,b=e.get('start'),e.get('end')
            if type(a) is not int or type(b) is not int or not 0<=a<b<=len(text) or text[a:b]!=e.get('text') or text[a:b]!=e.get('literal'):raise ValueError('scope evidence quotation mismatch')
        for s in row.get('subclauses',[]):
            a,b=s.get('start'),s.get('end')
            if type(a) is not int or type(b) is not int or not 0<=a<b<=len(article['text']) or article['text'][a:b]!=s.get('text') or s.get('requires_full_article') is not True or s.get('may_independently_determine_applicability') is not False:raise ValueError('invalid independent subclause')
        if textsha(article['text'])!=row['text_sha256']:raise ValueError('scope article text fingerprint mismatch')
        out[aid]=row
    if set(out)!=set(legal.articles):raise ValueError('scope table must cover exact sealed legal article set')
    return out
