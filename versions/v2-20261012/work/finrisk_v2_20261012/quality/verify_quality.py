from quality_common import *
from collections import Counter

def strip_labels(d):
    d=copy.deepcopy(d)
    for k in ['label_policy_version','semantic_status','human_review_status']: d.pop(k,None)
    for b in d['behaviors']:
        for k in ['risk_tags','zero_tag_reason']: b.pop(k,None)
    return d

def verify_early():
    rows=[json.loads(s) for s in (OUT/'early30_overlays.jsonl').read_text(encoding='utf-8').splitlines()]
    expected={i['file_id'] for i in index().values() if i.get('batch')=='early30'}
    assert len(rows)==30 and {r['file_id'] for r in rows}==expected
    checked=[]; counts=Counter()
    for r in rows:
        d,t,idx,*_=get(r['file_id']); u=r['updated_draft']
        assert sha_json(d)==r['base_draft_json_sha256']
        assert sha_bytes(t.encode('utf-8'))==r['base_text_sha256']
        assert strip_labels(d)==strip_labels(u),r['file_id']
        assert u['semantic_status']=='candidate' and u['human_review_status']=='pending'
        assert u['label_policy_version']=='recall-v2'
        assert sha_json(u)==r['updated_draft_json_sha256']
        for bi,b in enumerate(u['behaviors']):
            assert 1<=len(b['risk_tags'])<=3 and b['zero_tag_reason'] is None
            counts['behaviors']+=1
            for rank,tagrec in enumerate(b['risk_tags'],1):
                assert tagrec['tag'] in dictionary()
                assert tagrec['retrieval_rank']==rank
                assert tagrec['match_basis'] in ['explicit','inferred']
                assert tagrec['confidence'] in ['high','medium','low']
                assert tagrec['assignment_scope'] in ['behavior_context','document_related']
                assert tagrec['reason'] and tagrec['necessary_conditions'] and tagrec['limitations']
                if b['actor_role']=='unknown':
                    assert tagrec['match_basis']=='inferred' and tagrec['assignment_scope']=='document_related'
                    counts['unknown_actor_tags']+=1
                for q in tagrec['quotes']:
                    assert q and q in t
                    start=t.index(q)
                    checked.append(dict(file_id=r['file_id'],behavior_index=bi,tag=tagrec['tag'],quote=q,start=start,end=start+len(q),text_sha256=r['base_text_sha256']))
                    counts['quotes']+=1
                counts['tags']+=1
    write_jsonl(OUT/'early30_quote_verification.jsonl',checked)
    result=dict(documents=len(rows),**counts,fact_preservation='PASS: recursively equal after excluding only permitted label/status fields',sha_bindings='PASS',quote_exact_contiguous='PASS',human_approved=0,model_review_only=True)
    write_json(OUT/'early30_verification.json',result)
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__': verify_early()
