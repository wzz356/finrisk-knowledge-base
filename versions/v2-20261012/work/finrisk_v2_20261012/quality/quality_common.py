import copy
import csv
import hashlib
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
KB = ROOT / 'finrisk-knowledge-base'
QUEUE = ROOT / 'outputs/FinRisk_剩余全量运行_v2_20261011/reports/质量验收_20261012/定向复核工作队列_v2.json'

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def canonical(o): return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def sha_json(o): return sha_bytes(canonical(o))
def jread(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
@lru_cache(None)
def index():
    return {x['file_id']:x for x in map(json.loads,(KB/'data/file_index.jsonl').read_text(encoding='utf-8-sig').splitlines())}
@lru_cache(None)
def shard(path): return (KB/path).read_text(encoding='utf-8-sig').splitlines()
def env_at(pos): return json.loads(shard(pos['path'])[pos['line']-1])
def get(fid):
    idx=index()[fid]
    c,s=env_at(idx['candidate']),env_at(idx['source'])
    assert c['file_id']==s['file_id']==fid
    assert sha_json(c['draft'])==idx['draft_json_sha256']
    assert sha_bytes(s['full_text'].encode('utf-8'))==idx['text_sha256']
    return c['draft'],s['full_text'],idx,c,s
def write_json(p,data): Path(p).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_jsonl(p,data): Path(p).write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in data),encoding='utf-8')
def dictionary():
    with (KB/'dictionary/risk_type_dictionary.csv').open(encoding='utf-8-sig',newline='') as f: return {x['risk_tag']:x for x in csv.DictReader(f)}
def tag(name,quote,reason,conditions=None,basis='explicit',confidence='high',scope='behavior_context',limitations=None):
    assert name in dictionary()
    return dict(tag=name,reason=reason,quotes=[quote] if isinstance(quote,str) else quote,necessary_conditions=conditions or ['仅限原文所述主体、行为和历史情境；进一步机制需另有证据。'],match_basis=basis,confidence=confidence,retrieval_rank=0,assignment_scope=scope,limitations=limitations or ['召回候选标签不替代事实或责任认定。'])
def build_overlay(fid,assignments,limitations=None):
    draft,text,idx,c,s=get(fid)
    updated=copy.deepcopy(draft)
    changes=[]
    missing=[]
    if 'label_policy_version' not in updated: missing.append('label_policy_version')
    updated['label_policy_version']='recall-v2'
    changes.append(dict(field='/label_policy_version',old=draft.get('label_policy_version'),old_present='label_policy_version' in draft,new='recall-v2',reason='按用户授权迁移召回候选标签政策。'))
    assert len(assignments)==len(updated['behaviors']), (fid,len(assignments),len(updated['behaviors']))
    for i,(b,items) in enumerate(zip(updated['behaviors'],assignments)):
        assert 1<=len(items)<=3
        for rank,t in enumerate(items,1):
            t['retrieval_rank']=rank
            assert all(q and q in text for q in t['quotes']), (fid,i,t['tag'],t['quotes'])
            if b['actor_role']=='unknown':
                assert t['match_basis']=='inferred' and t['assignment_scope']=='document_related',(fid,i)
            if t['match_basis']=='inferred': assert t['limitations']
        for key,val in [('risk_tags',items),('zero_tag_reason',None)]:
            if key not in b: missing.append(f'behaviors[{i}].{key}')
            changes.append(dict(field=f'/behaviors/{i}/{key}',local_key=b['local_key'],old=copy.deepcopy(b.get(key)),old_present=key in b,new=copy.deepcopy(val),reason='逐行为重判召回标签；非空标签对应zero_tag_reason=null。'))
            b[key]=copy.deepcopy(val)
    for k,v in [('semantic_status','candidate'),('human_review_status','pending')]:
        if k not in updated: missing.append(k)
        if updated.get(k)!=v:
            changes.append(dict(field='/'+k,old=updated.get(k),old_present=k in updated,new=v,reason='新标签独立模型候选，不能继承旧批准。'))
            updated[k]=v
    return dict(file_id=fid,base_draft_json_sha256=idx['draft_json_sha256'],base_text_sha256=idx['text_sha256'],base_original_candidate_byte_sha256=c.get('original_candidate_sha256'),base_candidate_shard_line_sha256=sha_bytes(shard(idx['candidate']['path'])[idx['candidate']['line']-1].encode('utf-8')),updated_draft=updated,updated_draft_json_sha256=sha_json(updated),changes=changes,limitations=(limitations or [])+['模型核查，仅为candidate/pending；不是人工批准。','事实字段逐值保留；新标签不能沿用旧提案审核。'],missing_historical_fields=missing,source_locator=idx['source'],candidate_locator=idx['candidate'])

def compact(o,text):
    # All fields remain visible; repeated exact source strings point to already displayed text.
    if isinstance(o,str) and len(o)>20 and o in text:
        start=text.index(o)
        return {'source_span':[start,start+len(o)]}
    if isinstance(o,list): return [compact(x,text) for x in o]
    if isinstance(o,dict): return {k:compact(v,text) for k,v in o.items()}
    return o

def factored(o):
    from collections import Counter
    counts=Counter()
    values={}
    def count(v):
        k=canonical(v).decode('utf-8')
        if len(k)>60:
            counts[k]+=1
            values[k]=v
        if isinstance(v,dict):
            for x in v.values(): count(x)
        elif isinstance(v,list):
            for x in v: count(x)
    count(o)
    ids={k:'R'+str(i+1) for i,k in enumerate(k for k,n in counts.items() if n>1)}
    def replace(v,skip=None):
        k=canonical(v).decode('utf-8')
        if k in ids and k!=skip: return {'ref':ids[k]}
        if isinstance(v,dict): return {a:replace(b) for a,b in v.items()}
        if isinstance(v,list): return [replace(a) for a in v]
        return v
    return {'definitions':{rid:replace(values[k],skip=k) for k,rid in ids.items()},'draft':replace(o)}

def show(fid,kind='early',full=True):
    draft,text,idx,c,s=get(fid)
    parts=kind.split(':')
    if parts[0]=='priority':
        rec=next(x for x in jread(OUT/'selection_manifest.json')['selected'] if x['file_id']==fid)
        draft=jread(rec['candidate_path'])
    print('FILE',fid,'TEXT_CHARS',len(text),'DRAFT_SHA',sha_json(draft))
    if len(parts)>1:
        if parts[1]=='text': print(text)
        elif parts[1]=='behaviors':
            a,b=int(parts[2]),int(parts[3])
            print(json.dumps(factored(compact(draft['behaviors'][a:b],text)),ensure_ascii=False,separators=(',',':')))
        elif parts[1]=='meta':
            print(json.dumps(factored(compact({k:v for k,v in draft.items() if k!='behaviors'},text)),ensure_ascii=False,separators=(',',':')))
        return
    if full:
        print('FULL_TEXT_BEGIN')
        print(text)
        print('FULL_TEXT_END')
        print('FULL_DRAFT_WITH_EXACT_SOURCE_SPAN_REFERENCES')
        print(json.dumps(factored(compact(draft,text)),ensure_ascii=False,separators=(',',':')))
    else:
        for i,b in enumerate(draft.get('behaviors',[])):
            print(i,b['local_key'],b['actor_role'],b['finding_quote'],[t['tag'] for t in b.get('risk_tags',[])])

if __name__=='__main__':
    import sys
    for fid in sys.argv[2:]: show(fid,kind=sys.argv[1])
