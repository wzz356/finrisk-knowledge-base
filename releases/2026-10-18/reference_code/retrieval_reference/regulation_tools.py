"""Read-only, registered-ID regulation tools. No answer fields, API, URL or path arguments."""
import argparse
import json
from datetime import date
from source_registry import OUT
from rule_cards import rows, dependency_closure

EFFECTIVE = dict(L001='2015-04-24',L002='2024-03-01',L003='2026-02-01',L004='2023-06-30',
                 L005='2023-06-30',L006='2024-07-01',L007='2025-05-01',L008='2021-01-01',
                 L009='2019-01-01',L010='2021-04-29')

# Generic law-structure links, frozen before testing. No query, label answer or predicted state used.
ANCHORS={
 'M01':['L002-A0035','L005-A0011','L005-A0016','L005-A0025'],
 'M02':['L002-A0035','L005-A0016'],
 'M03':['L008-A0538','L008-A0539','L008-A0540','L008-A0541','L008-A0542','L009-A0004'],
 'M04':['L001-A0116','L001-A0131'],
 'M05':['L005-A0008','L005-A0012','L007-S01-I01'],
 'M06':['L005-A0006'], 'M07':['L005-A0007'],
 'M08':['L001-A0017','L002-A0026','L004-A0011','L004-A0029'],
 'M09':['L002-A0019','L010-A0028'], 'M10':['L001-A0119','L002-A0003'],
 'M11':['L002-A0029','L002-A0033','L005-A0004','L005-A0017'], 'M12':['L006-A0024']}


def fuse(routes, k=60):
    scores={}
    for route in routes:
        if len(route)!=len(set(route)): raise ValueError('duplicate route IDs')
        for rank,key in enumerate(route,1): scores[key]=scores.get(key,0)+1/(k+rank)
    return [dict(article_id=key,score=value,rank=i) for i,(key,value) in
            enumerate(sorted(scores.items(),key=lambda item:(-item[1],item[0])),1)]


def article_dense_scores(ids, scores):
    result={}
    for key,score in zip(ids,scores): result[key]=max(result.get(key,float('-inf')),float(score))
    return sorted(result.items(),key=lambda item:(-item[1],item[0]))


class RegulationStore:
    def __init__(self):
        self.articles={r['article_id']:r for r in rows(OUT/'articles.jsonl')}
        self.sources={r['source_id']:r for r in rows(OUT/'source_registry.jsonl')}
        self.rules={r['rule_id']:r for r in rows(OUT/'rules.jsonl')}
        self.views={r['article_id']:r for r in rows(OUT/'article_model_views.jsonl')}
        self.dependencies=json.loads((OUT/'article_dependencies.json').read_text(encoding='utf-8'))

    def read_regulation(self, registered_id, version_id=None):
        if registered_id in self.rules:
            rule=self.rules[registered_id]
            if version_id is not None: raise ValueError('rule cites multiple article versions; use article ID')
            return dict(rule=rule,articles=[self.read_regulation(i) for i in rule['article_refs']])
        if registered_id not in self.articles: raise ValueError('unregistered regulation ID')
        article=self.articles[registered_id]
        if version_id is not None and version_id!=article['version_id']: raise ValueError('version mismatch')
        source=self.sources[article['source_id']]
        return dict(article=article,source={k:source[k] for k in ['source_id','title','version_id','legal_status',
                    'official_url','retrieval_url','representation','original_artifact_acquired']},
                    dependencies=self.dependencies[registered_id],model_view=self.views[registered_id])

    def bundle(self, primary, facts=None, mode='current', review_date=None, include_pending=False,
               fact_evidence=None,input_text=None):
        if mode not in ['current','historical']: raise ValueError('unknown time mode')
        if mode=='historical' and not review_date: raise ValueError('historical review requires behavior date')
        review_date=review_date or '2026-10-17'
        date.fromisoformat(review_date)
        if review_date>'2026-10-17': raise ValueError('requested date exceeds frozen legal review')
        facts=facts or {}
        if set(facts)-{'group_person_insurance'} or any(type(v) is not bool for v in facts.values()):
            raise ValueError('only explicit supported scope facts accepted')
        fact_evidence=fact_evidence or {}
        for key in facts:
            evidence=fact_evidence.get(key,{})
            start,end=evidence.get('start'),evidence.get('end')
            if (not isinstance(input_text,str) or type(start) is not int or type(end) is not int
                or not 0<=start<end<=len(input_text) or input_text[start:end]!=evidence.get('quote')):
                raise ValueError('scope fact requires exact current-input evidence span')
        selected_mechanisms={m for m,anchors in ANCHORS.items() if set(anchors)&set(primary)}
        selected_rules=[r for r in self.rules.values() if r['mechanism_id'] in selected_mechanisms]
        supporting=[key for r in selected_rules for key in r['article_refs']]
        expanded=dependency_closure(list(dict.fromkeys(primary+supporting)),self.dependencies)
        articles,excluded=[],[]
        for key in expanded:
            a=self.articles[key]; sid=a['source_id']; s=self.sources[sid]
            if EFFECTIVE[sid]>review_date:
                excluded.append(dict(article_id=key,reason='not_yet_effective')); continue
            pending=s['legal_status']!='official_catalog_marked_current'
            if pending and not include_pending:
                excluded.append(dict(article_id=key,reason='legal_status_pending')); continue
            # Old current-catalog assertions cannot establish historical validity for arbitrary dates.
            historical_unverified=mode=='historical'
            outside=sid=='L004' and facts.get('group_person_insurance') is True
            articles.append(dict(article_id=key,version_id=a['version_id'],title=s['title'],
                 source_id=sid,official_url=s['official_url'],retrieval_url=s['retrieval_url'],
                 legal_status=s['legal_status'],legal_review_date='2026-10-17',
                 source_representation=s['representation'],original_artifact_acquired=False,
                 scope_status='known_outside_L004_scope' if outside else 'not_evaluated_unknown',
                 temporal_status='historical_validity_not_certified' if historical_unverified else 'frozen_current_catalog_or_pending',
                 source_currentness_check_passed=not pending,
                 eligible_as_definitive_basis=False,
                 role='primary' if key in primary else 'scope_definition_or_exception',
                 excerpts=self.views[key]['spans'],partial_article=self.views[key]['partial'],
                 withheld_reason=self.views[key]['withheld_reason']))
        returned={a['article_id'] for a in articles}
        rules=[r for r in selected_rules if set(r['article_refs'])<=returned]
        return dict(primary_article_ids=primary,primary_count=len(primary),expanded_count=len(expanded),
                    returned_count=len(articles),articles=articles,rules=rules,excluded=excluded,
                    missing_dependency_ids=sorted(set(expanded)-returned),context_truncated=False,
                    scope_facts=facts,time_mode=mode,review_date=review_date,
                    scope_fact_evidence=fact_evidence,
                    applicability_requires_semantic_review=True,
                    experimental_include_pending=include_pending,
                    rule_bundle_mechanisms=sorted(selected_mechanisms),
                    warning='解释卡是模型整理；效力待核或范围未知不构成已确认适用。原始网页/PDF未下载。')

    def search_regulations(self, query, top_k=20, facts=None, include_pending=False,fact_evidence=None):
        if not isinstance(query,str) or not query.strip() or len(query)>10000: raise ValueError('invalid query')
        if type(top_k) is not int or not 1<=top_k<=20: raise ValueError('top_k must be 1..20')
        from law_index import LawIndex
        if not hasattr(self,'index'): self.index=LawIndex()
        ranking=self.index.search(query)[:top_k]
        result=self.bundle([r['article_id'] for r in ranking[:5]],facts=facts,include_pending=include_pending,
                           fact_evidence=fact_evidence,input_text=query)
        result['ranking']=ranking
        result['query']=query
        return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query'); parser.add_argument('--id')
    parser.add_argument('--include-pending',action='store_true')
    args=parser.parse_args()
    store=RegulationStore()
    if bool(args.query)==bool(args.id): parser.error('provide exactly one of --query / --id')
    value=store.search_regulations(args.query,include_pending=args.include_pending) if args.query else store.read_regulation(args.id)
    print(json.dumps(value,ensure_ascii=False,indent=2))
