"""Portable offline verification; standard library, no API/key/GPU dependency."""
import hashlib
import gzip
import json
import math
from collections import Counter,defaultdict
from pathlib import Path
from metrics_night import metrics

BASE=Path(__file__).resolve().parent
DATA=BASE/'data'

def rows(p):
    p=Path(p)
    if not p.exists():p=p.with_name(p.name+'.gz')
    opener=gzip.open if p.suffix=='.gz' else open
    with opener(p,'rt',encoding='utf-8-sig') as f:return [json.loads(s) for s in f if s.strip()]
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def textsha(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def mean(xs):
    xs=[x for x in xs if x is not None]
    return sum(xs)/len(xs) if xs else None

def main():
    manifest=read(BASE/'manifest.json')
    for name,record in manifest['files'].items():
        p=(BASE/name).resolve();assert BASE in p.parents and sha(p)==record['sha256'],name
    # Rebuild rankings from the earliest valid raw scores, not saved aggregate metrics.
    ranges={'specific_direct':(80,100),'concise_direct':(60,79),'partial':(20,59),'topic_only':(1,19),'none':(0,0),'insufficient':(0,0)}
    jobmap={j['pair_id']:j for j in rows(DATA/'rerank_jobs.jsonl')};scoremap={}
    for scope in ['rerank','rerank_continuation','rerank_unaffected','rerank_finish','rerank_persistent','rerank_reliable']:
        for r in rows(BASE/'audit'/(scope+'_records.jsonl')):
            job=jobmap[r['pair_id']]
            assert textsha(json.dumps(job['body'],ensure_ascii=False,allow_nan=False))==r['base_payload_sha256']
            if r['pair_id'] in scoremap or r['status']=='unknown':continue
            try:
                response=r['response'];assert response['model'] in ['deepseek-flash','deepseek-v4.1-flash']
                assert len(response['choices'])==1 and response['choices'][0]['finish_reason']=='stop'
                v=json.loads(response['choices'][0]['message']['content'])
                assert v['pair_id']==r['pair_id'] and type(v['score']) is int and v['level'] in ranges
                assert ranges[v['level']][0]<=v['score']<=ranges[v['level']][1]
                assert v['human_approved'] is False and isinstance(v['source_quote'],str)
                assert all(isinstance(v[k],str) and v[k].strip() for k in ['reason','limitation'])
                scoremap[r['pair_id']]=v
            except (ValueError,TypeError,KeyError,AssertionError):continue
    assert set(scoremap)==set(jobmap), 'incomplete unique candidate score set'
    grouped=defaultdict(list)
    for r in rows(DATA/'candidate_map.jsonl'):
        if r['pair_id'] not in scoremap:continue
        s=scoremap[r['pair_id']]
        grouped[r['query_id'],r['arm']].append(dict(file_id=r['file_id'],unit_id=r['unit_id'],pair_id=r['pair_id'],score=s['score'],level=s['level'],rrf_rank=r['rrf_rank']))
    for r in rows(DATA/'rankings.jsonl'):
        best={}
        for unit in sorted(grouped[r['query_id'],r['arm']],key=lambda x:(-x['score'],x['unit_id'],x['file_id'])):best.setdefault(unit['file_id'],unit)
        rebuilt=sorted(best.values(),key=lambda x:(-x['score'],x['unit_id'],x['file_id']))
        assert rebuilt==r['ranking']
    sources={s['file_id']:s for s in rows(DATA/'judging_sources.jsonl')}
    for s in sources.values():
        assert textsha(s['full_text'])==s['source_sha256']
        assert ''.join(p['text'] for p in s['spans'])==s['full_text']
        for span in s['spans']:assert s['full_text'][span['start']:span['end']]==span['text']
    grades=defaultdict(dict);quote_reads=0
    qrels=rows(DATA/'qrels_silver.jsonl')
    judge_jobs={j['pair_id']:j for j in rows(DATA/'relevance_jobs.jsonl')}
    judge_raw={};selected_records={};repaired_ids=set()
    for scope in ['relevance','relevance_connect_recovery']:
        for record in rows(BASE/'audit'/(scope+'_records.jsonl')):
            pid=record['pair_id'];job=judge_jobs[pid]
            assert textsha(json.dumps(job['body'],ensure_ascii=False,allow_nan=False))==record['base_payload_sha256']
            if pid in judge_raw:continue
            try:
                response=record['response']
                assert isinstance(response,dict) and json.loads(record['raw_response_text'])==response
                assert response['model'] in ['deepseek-flash','deepseek-v4.1-flash']
                assert len(response['choices'])==1 and response['choices'][0]['finish_reason']=='stop'
                value=json.loads(response['choices'][0]['message']['content'])
                # Identity repair was frozen for the original snapshot only.
                # The later four-job runner retained its already frozen strict schema.
                supplied=scope=='relevance' and 'human_approved' not in value
                if supplied:value['human_approved']=False
                assert value['pair_id']==pid and value['human_approved'] is False
                assert type(value['grade']) is int and value['grade'] in range(4)
                assert isinstance(value['reason'],str) and value['reason'].strip()
                ids=value['evidence_span_ids'];registry={s['span_id']:s for s in job['packet']['spans']}
                assert isinstance(ids,list) and len(ids)==len(set(ids)) and set(ids)<=set(registry)
                if value['grade']>=2:assert ids
                judge_raw[pid]=value;selected_records[pid]=record
                if supplied:repaired_ids.add(pid)
            except (ValueError,TypeError,KeyError,AssertionError):continue
    repairs=rows(DATA/'relevance_metadata_recovery.jsonl')
    assert repaired_ids=={r['pair_id'] for r in repairs}
    for r in repairs:
        record=selected_records[r['pair_id']];v=judge_raw[r['pair_id']]
        assert r['backend_provenance_repair']['original_raw_response_text_sha256']==textsha(record['raw_response_text'])
        assert r['backend_provenance_repair']['missing_fields']==['human_approved']
        assert all(v[k]==r['parsed'][k] for k in ['grade','evidence_span_ids','reason','human_approved'])
    old_labels={r['pair_id']:r['parsed'] for r in rows(BASE/'audit/relevance_records.jsonl') if r['status']=='accepted'}
    selection=rows(DATA/'relevance_recovery_selection_audit.jsonl')
    for r in selection:
        pid=r['pair_id']
        assert r['selected_attempt']==selected_records[pid]['attempt']
        assert r['metadata_supplied']==(pid in repaired_ids)
        assert r['grade_changed']==(pid in old_labels and old_labels[pid]['grade']!=judge_raw[pid]['grade'])
    amendment=read(DATA/'relevance_recovery_amendment.json')
    assert len(repaired_ids)==amendment['metadata_repairs'] and sum(r['grade_changed'] for r in selection)==amendment['old_accepted_grade_changes']
    old_records=rows(BASE/'audit/relevance_records.jsonl')
    for proof in rows(DATA/'relevance_preHTTP_proof.jsonl'):
        prior=[r for r in old_records if r['pair_id']==proof['pair_id']]
        assert len(prior)==proof['previous_outer_failures'] and all(r.get('no_HTTP_body_sent') is True and r.get('observed_http_status') is None for r in prior)
    assert set(judge_raw)==set(judge_jobs)
    for r in qrels:
        assert r['human_approved'] is False
        job=judge_jobs[r['pair_id']]
        assert r['query_id']==job['query_id'] and r['file_id']==job['file_id']
        assert textsha(job['packet']['source_text'])==r['source_sha256']
        assert all(r[k]==judge_raw[r['pair_id']][k] for k in ['grade','evidence_span_ids','reason','human_approved'])
        s=sources[r['file_id']];assert r['source_sha256']==s['source_sha256']
        registry={p['span_id']:p for p in s['spans']}
        expected=[s['full_text'][registry[sid]['start']:registry[sid]['end']] for sid in r['evidence_span_ids']]
        assert expected==r['source_quotes']
        if r['grade']>=2:assert expected
        quote_reads+=len(expected)
        assert r['file_id'] not in grades[r['query_id']]
        grades[r['query_id']][r['file_id']]=r['grade']
    measured=[]
    saved={(r['query_id'],r['arm']):r for r in rows(DATA/'retrieval_per_query.jsonl')}
    for ranking in rows(DATA/'rankings.jsonl'):
        if not ranking['complete_candidate_scoring']:continue
        qid=ranking['query_id'];arm=ranking['arm']
        m=metrics([x['file_id'] for x in ranking['ranking'][:20]],grades[qid])
        expected=saved[qid,arm]
        assert all(expected[k]==v for k,v in m.items()),(qid,arm)
        measured.append(expected)
    report=read(DATA/'retrieval_metrics.json')
    for group,arms in report['groups'].items():
        for arm,summary in arms.items():
            chosen=[r for r in measured if r['group']==group and r['arm']==arm]
            assert len(chosen)==summary['n']
            for name,value in summary['metrics'].items():
                calc=mean([r[name] for r in chosen])
                assert (calc is None and value is None) or math.isclose(calc,value,abs_tol=1e-12),(group,arm,name)
                assert sum(r[name] is not None for r in chosen)==summary['valid_denominators'][name]
    # Independent boundary re-count from raw accepted responses and reference mapping.
    boundary_records=rows(BASE/'audit/boundary_records.jsonl')
    predictions={}
    for r in boundary_records:
        if r['status']!='accepted':continue
        response=r['response'];assert json.loads(r['raw_response_text'])==response
        assert response['model'] in ['deepseek-flash','deepseek-v4.1-flash']
        assert len(response['choices'])==1 and response['choices'][0]['finish_reason']=='stop'
        p=json.loads(response['choices'][0]['message']['content'])
        assert p['pair_id']==r['pair_id'] and p['human_approved'] is False
        assert all(p[k]==r['parsed'][k] for k in ['state','mechanism_ids','legal_article_ids','reason','needed_facts'])
        predictions[r['pair_id']]=p
    refs={r['query_id']:r for r in rows(DATA/'law_review/boundary_reference.jsonl')}
    inputs={r['query_id']:r['text']+'\n'+r.get('background','') for r in rows(DATA/'law_review/boundary_inputs.jsonl')}
    counts=defaultdict(Counter)
    for job in rows(DATA/'boundary_jobs.jsonl'):
        p=predictions[job['pair_id']];ref=refs[job['query_id']];expected='no_clear_risk' if ref['expected_state']=='no_risk' else ref['expected_state']
        assert textsha(json.dumps(job['body'],ensure_ascii=False,allow_nan=False))==next(r['base_payload_sha256'] for r in boundary_records if r['pair_id']==job['pair_id'] and r['status']=='accepted')
        c=counts[job['arm']];c['n']+=1;c['correct']+=p['state']==expected
        c['mechanisms']+=set(p['mechanism_ids'])==set(ref['expected_supported_mechanisms'])
        assert all(q in inputs[job['query_id']] for q in p['fact_quotes'])
    for arm,summary in read(DATA/'boundary_metrics.json')['summary'].items():
        assert counts[arm]['n']==summary['n'] and counts[arm]['correct']==summary['state_correct'] and counts[arm]['mechanisms']==summary['exact_mechanism_sets']
    # Recompute cost ledger, retaining full reservations for unknown usage.
    reservations={};settled={}
    for event in rows(BASE/'audit/ledger.jsonl'):
        assert event['global_cap_usd']==2.
        rid=event['reservation_id']
        if event['event']=='reserve':assert rid not in reservations;reservations[rid]=event
        else:assert rid in reservations and rid not in settled;settled[rid]=event['booked_usd']
    booked=sum(settled.get(rid,r['reserved_usd']) for rid,r in reservations.items())
    assert len(settled)==len(reservations) and booked<=2.+1e-12
    assert math.isclose(booked,read(DATA/'fees.json')['booked_usd'],abs_tol=1e-12)
    # Legal delivery-only dependency remains literal source, not a re-scored experiment.
    law_sources={s['source_id']:s for s in rows(DATA/'legal_source_snapshots.jsonl')}
    for a in rows(DATA/'delivery_articles43.jsonl'):
        s=law_sources[a['source_id']]
        assert s['text'][a['start']:a['end']]==a['text'] and textsha(a['text'])==a['text_sha256']
        assert textsha(s['text'])==a['original_source_text_sha256'] and not a['production_active']
    result=dict(passed=True,manifest_files=len(manifest['files']),retrieval_queries=len(grades),relevance_pairs=len(qrels),
        raw_scores_rebuilt=len(scoremap),registered_quote_reads=quote_reads,boundary_judgments=sum(x['n'] for x in counts.values()),booked_usd=booked,
        metadata_identity_repairs=len(repaired_ids),earlier_response_grade_changes=sum(r['grade_changed'] for r in selection),
        full_corpus_recall=False,API_calls_by_this_replay=0)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':main()
