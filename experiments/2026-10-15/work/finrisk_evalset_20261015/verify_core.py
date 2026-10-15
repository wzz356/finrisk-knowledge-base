"""独立重算四指标/费用并核验完整标签、实际响应、来源与冻结文件。"""
import math,re
from collections import Counter
from fractions import Fraction
from common import *
from labels import validate_decisions
checks={}
for n in ['input_freeze.json','candidate_freeze.json','api_freeze.json','qrels_freeze.json','prediction_freeze.json','supplement_input_freeze.json']:
 d=read(OUT/n)
 for field in ['sha256','code_sha256']:
  for p,h in d.get(field,{}).items():assert sha(p)==h,(n,p)
checks['all_freeze_and_code_hashes']=True
queries=rows(OUT/'queries.jsonl');corpus=rows(OUT/'corpus.jsonl');refs=rows(OUT/'qrels.jsonl')
qm={q['query_id']:q for q in queries};cm={d['file_id']:d for d in corpus};key=lambda r:(r['query_id'],r['file_id'])
gm={key(r):r for r in refs};expected={(q,f) for q in qm for f in cm}
assert len(qm)==20 and len(cm)==100 and len(gm)==len(refs)==2000 and set(gm)==expected
for q in queries:assert tsha(q['text'])==q['text_sha256'] and not re.search(r'F\d{6}|KBT\d{3}',q['text'])
original={d['official_file_id']:d for d in iterrows(SOURCE) if d['official_file_id'] in cm}
for f,d in cm.items():
 assert original[f]['full_text']==d['text'] and tsha(d['text'])==d['text_sha256']==original[f]['text_sha256']
 assert original[f]['source_id']==d['source_id']
for r in refs:
 assert type(r['grade']) is int and r['grade'] in [0,1,2,3] and r['human_approved'] is False
 assert r['explicit_matrix_decision'] and r['source_text_sha256']==cm[r['file_id']]['text_sha256']
 if r['grade']>=2:assert r['source_quote'] and r['source_quote'] in cm[r['file_id']]['text'] and r['reason'] and r['limitation']
for round_name in ['annotations','reviews']:
 dd=[]
 for i in [1,2,3]:dd+=rows(WORK/f'{round_name}/part_{i}/decisions.jsonl')
 assert len(validate_decisions(dd,corpus,rows(OUT/'query_specs.jsonl')))==2000
initial={key(r):r for r in rows(OUT/'qrels_initial.jsonl')};second={key(r):r for r in rows(OUT/'qrels_second_blind_review.jsonl')}
material={k for k in expected if initial[k]['grade']!=second[k]['grade'] and max(initial[k]['grade'],second[k]['grade'])>=2}
adj=rows(OUT/'adjudication_log.jsonl');assert len(adj)==len(material)==25 and {key(r) for r in adj}==material
for a in adj:assert gm[key(a)]['grade']==a['final_grade'] and gm[key(a)]['root_reason']==a['root_reason']
for a in read(WORK/'negative_audit.json')['decisions']:assert gm[key(a)]['grade']==a['grade_confirmed']
assert Counter(r['grade'] for r in refs)=={0:1550,1:232,2:78,3:140}
assert len({r['file_id'] for r in refs if r['grade']==3})==read(OUT/'reference_summary.json').get('unique_direct_documents',len({r['file_id'] for r in refs if r['grade']==3}))
checks['complete_2000_source_bound_labels_two_blind_rounds_25_adjudications_6_negatives']=True
for name,mapper in [('qrels_direct.txt',lambda g:int(g==3)),('qrels_graded_levels.txt',lambda g:2 if g==3 else int(g==2)),('qrels_graded_gain.txt',lambda g:3 if g==3 else int(g==2))]:
 expected_lines=[f"{r['query_id']} 0 {r['file_id']} {mapper(r['grade'])}" for r in refs]
 assert (OUT/name).read_text(encoding='utf-8').splitlines()==expected_lines
checks['trec_formats_explicit_full_matrix']=True
packets=rows(OUT/'score_inputs.jsonl');pm={p['pair_id']:p for p in packets};maps=rows(OUT/'candidate_map.jsonl');scores=rows(OUT/'scores.jsonl');sm={s['pair_id']:s for s in scores}
assert len(pm)==len(packets)==len(sm)==len(scores)==3877 and set(pm)==set(sm)
assert len(maps)==4000 and len({(m['scope'],m['query_id'],m['unit_id']) for m in maps})==4000
units_wanted={m['unit_id'] for m in maps};um={u['unit_id']:u for u in iterrows(INDEX) if u['unit_id'] in units_wanted}
for m in maps:
 p=pm[m['pair_id']];u=um[m['unit_id']];assert u['file_id']==m['file_id'] and u['text']==p['unit_text'] and qm[m['query_id']]['text']==p['query_text']
for p in packets:assert tsha(p['query_text'])==p['query_text_sha256'] and tsha(p['unit_text'])==p['unit_text_sha256']
import common
common.PRIOR=ROOT/'work/finrisk_deepseek_rerank_20261014';sys.path.insert(0,str(common.PRIOR))
adapter=module(common.PRIOR/'api_adapter.py','verified_API_schema');citation=module(ROOT/'work/finrisk_official_only_20261015/citation.py','verified_literal_citation')
requests=rows(OUT/'requests.jsonl');responses=rows(OUT/'responses.jsonl')
response_map={(r['pair_id'],r['response']['id']):r for r in responses}
accepted=[r for r in requests if r['status']=='accepted'];assert len(accepted)==3877
for s in scores:
 r=response_map[s['pair_id'],s['response_id']];valid=citation.validate_completion(pm[s['pair_id']],r['response'])
 for field in ['score','level','source_quote','reason','limitation','human_approved']:assert valid[field]==s[field]
 assert s['returned_model']==r['response']['model']=='deepseek-flash'
 assert s['origin']=='actual_deepseek_flash_API' and s['query_text_sha256']==pm[s['pair_id']]['query_text_sha256'] and s['unit_text_sha256']==pm[s['pair_id']]['unit_text_sha256']
assert {r['pair_id'] for r in accepted}==set(pm)
usd=0.;known_peak=0.;unknown_reserve=0.;usage=Counter();periods=Counter()
for r in requests:
 if r['cost'] is None:unknown_reserve+=r['budget_booked_peak_bound_usd'];continue
 raw=response_map[r['pair_id'],r['response_id']]['response']['usage'];n=raw['prompt_tokens'];out=raw['completion_tokens'];hit=raw['prompt_cache_hit_tokens'];miss=n-hit
 utc=datetime.fromisoformat(r['utc']);h=utc.hour+utc.minute/60;peak=utc.weekday()<5 and (1<=h<4 or 6<=h<10)
 bound=(miss*.3+hit*.006+out*1.2)/1e6;estimate=bound if peak else bound/2
 assert math.isclose(bound,r['budget_booked_peak_bound_usd'],abs_tol=1e-12) and math.isclose(estimate,r['cost']['estimated_usd'],abs_tol=1e-12)
 usd+=estimate;known_peak+=bound;periods['peak' if peak else 'off_peak']+=1
 usage.update(prompt=n,completion=out,cache_hit=hit,cache_miss=miss)
booked=sum(r['budget_booked_peak_bound_usd'] for r in requests)
assert math.isclose(booked,known_peak+unknown_reserve,abs_tol=1e-10) and math.isclose(booked,read(OUT/'api_completion.json')['booked_peak_bound_usd'],abs_tol=1e-10) and booked<2
save('api_cost_audit.json',{'requests':len(requests),'accepted':len(accepted),'rejected':len(requests)-len(accepted),'responses_with_usage':len(responses),
 'unknown_usage_requests':sum(r['cost'] is None for r in requests),'usage_tokens':dict(usage),'pricing_periods':dict(periods),
 'usage_based_estimated_usd':usd,'unknown_usage_peak_reserved_usd':unknown_reserve,'conservative_peak_booked_bound_usd':booked,
 'not_account_statement':True,'includes_rejected_requests_with_usage':True,'price_source':'https://api-docs.deepseek.com/quick_start/pricing/'})
checks['3877_real_API_scores_4000_bindings_raw_response_replay_cost_bound']=True
# 与交付函数无关地直接计算每题四指标和宏平均。
allr=rows(OUT/'all_results.jsonl');assert len(allr)==200
for stage in ['BM25','BGE','RRF','N0','ND']:
 measured=[]
 for r in allr:
  if r['scope']!='closed100' or r['stage']!=stage:continue
  fs=r['file_ids'];assert len(fs)==len(set(fs)) and set(fs)<=set(cm)
  pos={fid for (q,fid),g in gm.items() if q==r['query_id'] and g['grade']==3}
  first=next((i for i,fid in enumerate(fs[:20],1) if fid in pos),None)
  d={'top1_hit_rate':float(fs[0] in pos),'mrr20':1/first if first else 0}
  for k in [5,10,20]:
   d[f'recall{k}']=len(set(fs[:k])&pos)/len(pos)
   dcg=sum(1/math.log2(i+1) for i,fid in enumerate(fs[:k],1) if fid in pos)
   ideal=sum(1/math.log2(i+1) for i in range(1,min(k,len(pos))+1));d[f'ndcg{k}']=dcg/ideal
  measured.append(d)
 summary=read(OUT/f'metrics/closed100_{stage}.json')['primary_summary'];assert len(measured)==20
 for k in measured[0]:
  expected_value=sum(m[k] for m in measured)/20;actual_value=summary[k]['value'] if isinstance(summary[k],dict) else summary[k]
  assert math.isclose(expected_value,actual_value,abs_tol=1e-12),(stage,k)
checks['five_stages_four_metrics_independent_formula_recalculation']=True
sys.path.insert(0,str(OUT));entry=module(OUT/'evaluate.py','portable_entry')
nd=rows(OUT/'rankings/closed100_ND.jsonl');assert entry.evaluate(OUT,nd)['primary_summary']==read(OUT/'metrics/closed100_ND.json')['primary_summary']
bad=[dict(r) for r in nd];bad[0]={**bad[0],'file_ids':['F_OUTSIDE']}
try:entry.evaluate(OUT,bad)
except ValueError:pass
else:raise AssertionError('outside corpus must be rejected')
checks['portable_evaluator_real_ranking_and_unknown_guard']=True
for s in read(OUT/'full_known_reference_coverage.json')['stages']:
 for p in s['per_query']:
  rr=next(r for r in allr if r['scope']=='full9639' and r['stage']==s['stage'] and r['query_id']==p['query_id'])
  positives={f for (q,f),g in gm.items() if q==p['query_id'] and g['grade']==3}
  for k in [5,10,20,100]:assert math.isclose(p[f'known_reference_coverage{k}'],len(set(rr['file_ids'][:k])&positives)/len(positives),abs_tol=1e-12)
checks['full_known_coverage_not_true_recall']=True
old=ROOT/'outputs/FinRisk_官方检索文本对照_20261015';manifest=read(old/'delivery_manifest.json')
for f in manifest['files']:
 p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and sha(p)==f['sha256']
checks['previous_sealed_experiment_unchanged']=True
for p in OUT.rglob('*'):
 if p.is_file() and '__pycache__' not in p.parts:
  assert not re.search(rb'sk-[A-Za-z0-9_-]{16,}',p.read_bytes()),str(p)
checks['new_outputs_no_API_keys']=True
save('core_verification.json',{'status':'passed','checks':checks,'check_count':len(checks),'verified_at_utc':datetime.now(timezone.utc).isoformat()})
print(json.dumps(read(OUT/'core_verification.json'),ensure_ascii=False))
