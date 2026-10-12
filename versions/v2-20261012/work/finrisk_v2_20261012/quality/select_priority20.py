from quality_common import *

q=jread(QUEUE)
seen={x['file_id'] for x in jread(KB/'quality/2026-10-12/sample100_manifest.json')['records']}
pool=[]
for rec in q['records']:
    codes=[s['code'] for s in rec['signals']]
    if rec['file_id'] in seen: continue
    if not set(codes)&{'TABLE_DIRECT_PERSON_ROLE_REVIEW','PERSON_SPECIFIC_RECALL_CANDIDATE_REVIEW'}: continue
    draft,_,idx,c,s=get(rec['file_id'])
    original=jread(rec['candidate_path'])
    # Bundle is current exported candidate; bind both hashes and confirm same values.
    assert sha_json(original)==sha_json(draft),(rec['file_id'],'queue/index mismatch')
    assert sha_bytes(Path(rec['candidate_path']).read_bytes())==rec['candidate_sha256']
    person_count=sum(c.get('party_type')=='person' for c in draft['cases'])
    risky_roles=sum(b.get('actor_role') in ('direct_person_violation','unknown') for b in draft['behaviors'])
    sort_metrics=[person_count,risky_roles,len(draft['behaviors']),len(codes)]
    pool.append(dict(rec,sort_metrics=sort_metrics,person_count=person_count,risky_roles=risky_roles,behavior_count=len(draft['behaviors']),base_draft_json_sha256=idx['draft_json_sha256'],base_text_sha256=idx['text_sha256']))
selected=[]
for code,n in [('TABLE_DIRECT_PERSON_ROLE_REVIEW',12),('PERSON_SPECIFIC_RECALL_CANDIDATE_REVIEW',8)]:
    lane=[x for x in pool if code in [s['code'] for s in x['signals']] and x['file_id'] not in {s['file_id'] for s in selected}]
    lane.sort(key=lambda x:tuple(-n for n in x['sort_metrics'])+(x['file_id'],))
    for x in lane[:n]:
        x['selection_lane']=code
        x['selection_rank_in_lane']=len([y for y in selected if y['selection_lane']==code])+1
        selected.append(x)
assert len(selected)==20
manifest=dict(queue_path=str(QUEUE),queue_byte_sha256=sha_bytes(QUEUE.read_bytes()),queue_records=len(q['records']),previous100_excluded=len(seen),rule='固定配额：表格个人角色12份，个人候选归属8份。各层按个人主体数、unknown/direct_person角色数、行为数、信号数降序，file_id升序；第二层排除第一层。使用原队列记录和知识库当前稿，两个稿的canonical SHA必须一致。每份全文核金额、日期、否定、个人责任和漏行为。信号非错误。',model_review_only=True,selected=selected)
write_json(OUT/'selection_manifest.json',manifest)
print(json.dumps({'selected':[{k:x[k] for k in ['file_id','selection_lane','sort_metrics','candidate_path']} for x in selected]},ensure_ascii=False,indent=2))
