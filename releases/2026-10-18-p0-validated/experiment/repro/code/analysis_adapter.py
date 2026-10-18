"""Post-inference normalization and paired group-resampling; no tuning."""
import random
from scoring import _valid_prediction

def normalize_prediction(j,record,qid,arm):
    d=j['data'];p=record['parsed'] if record else None
    result=dict(query_id=qid,arm=arm,valid=p is not None,
        state=p.get('state') if p else None,mechanism_ids=p.get('mechanism_ids',[]) if p else [],
        predicates=p.get('predicates',{}) if p else {},case_unit_ids=p.get('case_unit_ids',[]) if p else [],
        legal_article_ids=p.get('legal_article_ids',[]) if p else [],current_text=d['current_text'],
        displayed_case_ids=d['case_unit_ids'],displayed_article_ids=d['article_ids'],
        validation_errors=[] if p else ['no structurally accepted judgment after authorized attempts'],
        reason=p.get('reason') if p else None,limitations=p.get('limitations',[]) if p else [])
    if p is not None and not _valid_prediction(result):
        result.update(valid=False,validation_errors=['normalized prediction does not satisfy frozen scorer structure'])
    return result

def group_bootstrap(points,iterations=5000,seed=20261018):
    groups={}
    for p in points:groups.setdefault(p['group_id'],[]).append(int(p['new_correct'])-int(p['old_correct']))
    result=dict(n=len(points),group_count=len(groups),iterations=iterations,seed=seed,point_delta=None,lower=None,upper=None,
        unit='story group, paired arms retained; question-weighted sampled mean',interpretation='descriptive small-group percentile interval; no generalization proof')
    if not points:return result
    rng=random.Random(seed);keys=sorted(groups);values=[]
    for _ in range(iterations):
        sample=[v for key in rng.choices(keys,k=len(keys)) for v in groups[key]];values.append(sum(sample)/len(sample))
    values.sort();result.update(point_delta=sum(sum(v) for v in groups.values())/len(points),lower=values[int(.025*(iterations-1))],upper=values[int(.975*(iterations-1))])
    return result
