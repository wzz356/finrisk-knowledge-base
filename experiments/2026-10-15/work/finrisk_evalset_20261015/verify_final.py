"""补充标签/数值/文档逐项核对，封存前拒绝缺失成果。"""
import math,re
from collections import Counter
from fractions import Fraction
from common import *
checks={}
for n in ['input_freeze.json','candidate_freeze.json','api_freeze.json','qrels_freeze.json','prediction_freeze.json','supplement_input_freeze.json','supplement_qrels_freeze.json']:
 d=read(OUT/n)
 for field in ['sha256','code_sha256']:
  for p,h in d.get(field,{}).items():assert sha(p)==h,(n,p)
checks['all_seven_freezes_and_codes_unchanged']=True
assert read(OUT/'core_verification.json')['status']=='passed' and read(OUT/'retrieval_verification.json')['status']=='passed'
checks['core_and_real_retrieval_replay_passed']=True
closed=rows(OUT/'corpus.jsonl');supp=rows(OUT/'supplement_corpus.jsonl');all_docs={d['file_id']:d for d in closed+supp}
assert len(supp)==281 and len(all_docs)==381
orig={d['official_file_id']:d for d in iterrows(SOURCE) if d['official_file_id'] in all_docs}
for f,d in all_docs.items():assert d['text']==orig[f]['full_text'] and tsha(d['text'])==d['text_sha256']==orig[f]['text_sha256']
qrels=rows(OUT/'qrels.jsonl');qr={(r['query_id'],r['file_id']):r for r in qrels};sr=rows(OUT/'supplement_qrels.jsonl');sm={(r['query_id'],r['file_id']):r for r in sr}
nd=[r for r in rows(OUT/'all_results.jsonl') if r['scope']=='full9639' and r['stage']=='ND']
expected={(r['query_id'],f) for r in nd for f in r['file_ids'][:20]};assert len(sm)==len(sr)==400 and set(sm)==expected
for k,r in sm.items():
 assert r['human_approved'] is False and type(r['grade']) is int and r['grade'] in [0,1,2,3]
 assert r['source_text_sha256']==all_docs[r['file_id']]['text_sha256']
 assert r['reason'] and r['limitation'] and (not r['source_quote'] or r['source_quote'] in all_docs[r['file_id']]['text'])
 if r['grade']>=2:assert r['source_quote']
 if r['closed_reference_reused']:assert r['grade']==qr[k]['grade'] and r['source_quote']==qr[k]['source_quote'] and r['reason']==qr[k]['reason']
assert sum(r['closed_reference_reused'] for r in sr)==35 and Counter(r['grade'] for r in sr)=={0:11,1:65,2:63,3:261}
audits=read(WORK/'supplement_root_blind_audit.json')['decisions'];blind={(r['query_id'],r['file_id']):r for r in rows(OUT/'supplement_annotations_initial.jsonl')}
assert len(audits)==18 and sum(a['grade']==blind[a['query_id'],a['file_id']]['grade'] for a in audits)==17
for a in audits:
 r=sm[a['query_id'],a['file_id']];assert r['grade']==a['grade'] and r['source_quote']==a['source_quote']
checks['400_actual_full_top20_pairs_source_bound_35_closed_reused_18_spotchecks']=True
measured=[]
for r in nd:
 grades=[sm[r['query_id'],f]['grade'] for f in r['file_ids'][:20]];first=next((i for i,g in enumerate(grades,1) if g==3),None)
 measured.append({'top1_hit_rate':int(grades[0]==3),'mrr20':Fraction(1,first) if first else Fraction(),
 'success20':int(first is not None),**{f'precision{k}':Fraction(sum(g==3 for g in grades[:k]),k) for k in [5,10,20]}})
metrics=read(OUT/'full_ND_actual_helpfulness.json');assert metrics['true_global_recall_reported'] is False and metrics['complete_global_NDCG_reported'] is False
for k in measured[0]:assert math.isclose(float(sum(r[k] for r in measured)/20),metrics['summary'][k],abs_tol=1e-12)
checks['actual_full_top1_MRR_precision_independently_recomputed_no_global_recall']=True
closed_summary=read(OUT/'closed_metrics_summary.json')
for stage in closed_summary['stages']:
 metrics=read(OUT/f"metrics/closed100_{stage['stage']}.json")
 for k in [5,10,20]:
  values=[]
  for rank in rows(OUT/f"rankings/closed100_{stage['stage']}.jsonl"):
   levels={f:2 if r['grade']==3 else int(r['grade']==2) for (q,f),r in qr.items() if q==rank['query_id']}
   actual_levels=[levels[f] for f in rank['file_ids'][:k]];ideal=sorted(levels.values(),reverse=True)[:k]
   dcg=sum((2**g-1)/math.log2(i+1) for i,g in enumerate(actual_levels,1));idcg=sum((2**g-1)/math.log2(i+1) for i,g in enumerate(ideal,1))
   values.append(dcg/idcg)
  assert math.isclose(sum(values)/20,metrics['auxiliary_graded_summary'][f'ndcg{k}'],abs_tol=1e-12)
checks['auxiliary_graded_NDCG_independent_formula_recalculation']=True
ndm=read(OUT/'metrics/closed100_ND.json');assert read(OUT/'metrics/standalone_cli_ND.json')==ndm
assert sum(r['relevant_count20'] for r in ndm['primary_per_query'])==122 and sum(r['positive_reference_count'] for r in ndm['primary_per_query'])==140
theoretical=sum(min(20,r['positive_reference_count'])/r['positive_reference_count'] for r in ndm['primary_per_query'])/20
assert round(theoretical*100,2)==99.09
checks['macro_vs_micro_examples_theoretical_cap_and_CLI_verified']=True
miss=read(OUT/'closed_miss_diagnostics.json');assert miss['missing_direct_pairs_from_top20']==18 and miss['candidate_absent']==8 and miss['rank_after20']==10
for r in miss['misses']:assert qr[r['query_id'],r['file_id']]['grade']==3 and r['direct_quote']==qr[r['query_id'],r['file_id']]['source_quote']
checks['miss_diagnostics_fixed_references']=True
specs=rows(OUT/'query_specs.jsonl');assert len({s['group'] for s in specs})==14 and sum(s['input_type']=='boundary' for s in specs)==5
selection=read(OUT/'selection_audit.json');assert set(selection['selected'])=={d['file_id'] for d in closed} and not set(selection['excluded_previous12_reference_files'])&set(selection['selected'])
checks['source_selection_queries14_groups5_boundaries_exclusion_checked']=True
report=(OUT/'指标报告.md').read_text(encoding='utf-8');readme=(OUT/'README.md').read_text(encoding='utf-8');samples=(OUT/'人工验收样例.md').read_text(encoding='utf-8')
assert all(s in report for s in ['90.73%','0.9375','0.8868','31.81%','65.25%','261/400','122/140','8个','10个'])
assert "--rankings '.\\rankings\\closed100_ND.jsonl'" in readme and '\r' not in readme
for q,f in [('KBT001','F001827'),('KBT004','F001928'),('KBT011','F000495'),('KBT017','F001748'),('KBT020','F000699')]:
 r=qr[q,f];assert r['grade']==3 and r['source_quote'].replace('\n','\n> ') in samples
required=['README.md','指标报告.md','人工验收样例.md','evaluate.py','evaluator_metrics.py','queries.jsonl','corpus.jsonl','qrels.jsonl','qrels_direct.txt','qrels_graded_gain.txt','qrels_graded_levels.txt','closed_index_units.jsonl','supplement_qrels.jsonl','full_ND_actual_helpfulness.json']
assert all((OUT/n).is_file() for n in required)
checks['deliverable_files_report_numbers_examples_and_command_checked']=True
import common
common.PRIOR=ROOT/'work/finrisk_deepseek_rerank_20261014';sys.path.insert(0,str(common.PRIOR))
from api_adapter import read_key
credential_bytes=read_key().encode();scanned=0
for parent in [OUT,WORK]:
 for p in parent.rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix in ['.json','.jsonl','.md','.py','.txt']:
   blob=p.read_bytes();assert credential_bytes not in blob and not re.search(rb'(?<![A-Za-z0-9_])sk-[A-Za-z0-9_-]{16,}',blob),str(p);scanned+=1
checks['outputs_and_work_text_secret_scan']=True
save('final_verification.json',{'status':'passed','checks':checks,'check_count':len(checks),'scanned_text_files':scanned,
 'human_approved':False,'global_true_recall_claimed':False,'verified_at_utc':datetime.now(timezone.utc).isoformat()})
print(json.dumps(read(OUT/'final_verification.json'),ensure_ascii=False))
