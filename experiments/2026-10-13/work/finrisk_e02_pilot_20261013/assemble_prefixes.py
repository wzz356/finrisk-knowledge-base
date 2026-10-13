"""Validate authored/peer-reviewed extractive backgrounds and freeze their bytes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E02小批量实验_20261013"
LABELS = {"文书主体", "片段主体", "责任角色", "行为背景", "适用条件", "材料用途", "产品背景"}


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def read(name):
    return [json.loads(s) for s in (OUT/name).read_text(encoding='utf-8').splitlines() if s.strip()]


def require(value, message):
    if not value:
        raise ValueError(message)


inputs={p['unit']['unit_id']:p for part in ('p1','p2') for p in read('prefix_inputs_'+part+'.jsonl')}
prefixes=[p for part in ('p1','p2') for p in read('prefixes_'+part+'.jsonl')]
reviews=[r for part in ('p1','p2') for r in read('prefix_reviews_'+part+'.jsonl')]
require(len(inputs)==len(prefixes)==len(reviews)==24,'incomplete prefix/review coverage')
require(len({p['unit_id'] for p in prefixes})==24,'duplicate prefix')
review_map={r['unit_id']:r for r in reviews}
require(len(review_map)==24 and set(inputs)==set(review_map),'review/inputs mismatch')
quotes=0
for p in prefixes:
    source=inputs[p['unit_id']];u=source['unit'];full=source['full_source_text']
    require(p['file_id']==u['file_id'],'prefix file mismatch')
    require(p['source_sha256']==source['source_sha256']==sha(full),'prefix source mismatch')
    require(p['base_unit_text_sha256']==sha(u['text']),'prefix base mismatch')
    require(1<=len(p['claims'])<=3,'claim dose outside profile')
    for c in p['claims']:
        span=c['span']
        require(c['label'] in LABELS,'unknown label')
        require(isinstance(c['link_reason'],str) and c['link_reason'].strip(),'missing semantic audit')
        require(type(span['start']) is type(span['end']) is int and 0<=span['start']<span['end']<=len(full),'invalid span')
        require(full[span['start']:span['end']]==c['quote'] and c['quote'].strip(),'prefix quote mismatch')
        quotes+=1
    require(p['prefix_text']=='\n'.join(c['label']+'：'+c['quote'] for c in p['claims']),'prefix render differs')
    require(len(p['prefix_text'])<=180,'prefix too long')
    r=review_map[p['unit_id']]
    require(r['prefix_sha256']==sha(p['prefix_text']) and r['source_sha256']==p['source_sha256'],'review SHA mismatch')
    require(r['status'] in ('approved_model_review','rejected'),'invalid semantic approval')
    require(r['reason'].strip(),'empty semantic review reason')
    # Approval comes from actual independent reading, never from this mechanical check.
    p['prefix_status']='candidate_model_review'
    p['human_approved']=False
for name,data in (('prefixes.jsonl',prefixes),('prefix_review.jsonl',reviews)):
    require(not (OUT/name).exists(),'refuse overwrite '+name)
    (OUT/name).write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in data),encoding='utf-8')
approved=sum(r['status']=='approved_model_review' for r in reviews)
summary={'documents':24,'units':24,'approved_model_review':approved,'rejected':24-approved,
         'quotes_verified':quotes,'max_prefix_chars':max(len(p['prefix_text']) for p in prefixes),
         'review_scope':'independent peer reader of source and original unit, no queries or prior relevance grades',
         'human_approved':False,
         'remaining_limits':['F004155 retains multiple occurrence/subject ambiguity; only document identity approved.',
                             'Document identity does not imply its party personally performed every fragment action.',
                             'Same model family authors and reviewers may share biases.'],
         'files_sha256':{name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ('prefixes.jsonl','prefix_review.jsonl','prefixes_p1.jsonl','prefixes_p2.jsonl','prefix_reviews_p1.jsonl','prefix_reviews_p2.jsonl')}}
(OUT/'prefix_quality.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
