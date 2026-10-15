"""固定1200候选逐对调用；先1条试跑，8路有界并发，失败不补分。"""
import argparse, hashlib, json, sys, time, threading
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from api_adapter import request,read_key,redact,validate_completion,usage_cost,payload,MODEL,ENDPOINT

sys.stdout.reconfigure(encoding='utf-8')
WORK=Path(__file__).resolve().parent;ROOT=WORK.parents[1]
OLD=ROOT/'outputs/FinRisk_官方测试重排确认_20261014'
FOUR=ROOT/'outputs/FinRisk_赛事四指标补测_20261014'
OUT=ROOT/'outputs/FinRisk_DeepSeek重排对照_20261014'
OUT.mkdir(parents=True,exist_ok=True)
BUDGET=2.0;CONCURRENCY=8;MAX_ATTEMPTS=3
def rows(p):return [json.loads(s) for s in Path(p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tsha(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def save(name,obj,jsonl=False):
 with (OUT/name).open('x',encoding='utf-8') as f:
  if jsonl:
   for g in obj:f.write(json.dumps(g,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n')
  else:f.write(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def append(name,obj):
 with (OUT/name).open('a',encoding='utf-8') as f:f.write(json.dumps(obj,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n')
def emit(**kw):print(json.dumps(kw,ensure_ascii=False),flush=True)
def verify_manifest(folder):
 for f in read(folder/'delivery_manifest.json')['files']:
  p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and sha(p)==f['sha256']
def freeze_check():
 expected=read(OUT/'input_freeze.json')['sha256']
 if (OUT/'network_resume_patch.json').exists():expected.update(read(OUT/'network_resume_patch.json')['updated_sha256'])
 if (OUT/'score_format_patch.json').exists():expected.update(read(OUT/'score_format_patch.json')['updated_sha256'])
 if (OUT/'quote_whitespace_patch.json').exists():expected.update(read(OUT/'quote_whitespace_patch.json')['updated_sha256'])
 for p,h in expected.items():assert sha(p)==h,p

EXPECTED_PAIRS=0

def run(pilot):
 freeze_check();key=read_key();rules=(OUT/'重排规则.md').read_text(encoding='utf-8')
 allpack=rows(OUT/'score_inputs.jsonl');pm={p['pair_id']:p for p in allpack}
 prior=rows(OUT/'scores.jsonl') if (OUT/'scores.jsonl').exists() else []
 assert len(prior)==len({g['pair_id'] for g in prior})
 for g in prior:assert validate_completion(pm[g['pair_id']],{'model':MODEL,'choices':[{'finish_reason':'stop','message':{'content':json.dumps({k:g[k] for k in ['pair_id','score','level','source_quote','reason','limitation','human_approved']})}}]})
 pending=[p for p in allpack if p['pair_id'] not in {g['pair_id'] for g in prior}]
 if pilot:pending=pending[:1]
 logs=rows(OUT/'requests.jsonl') if (OUT/'requests.jsonl').exists() else []
 spent=sum(l.get('budget_booked_peak_bound_usd',0) for l in logs)
 lock=threading.Lock();state={'spent':spent,'reserved':0.0,'attempts':len(logs),'aborts':0}
 last_errors={l['pair_id']:l['error'] for l in logs if l.get('status')=='rejected' and l.get('error','').startswith('ValueError:')}
 def feedback_for(error):
  return ('上一输出未通过格式校验：'+error+'。请只依据原输入和规则重新给出一个合法JSON。score必须为整数；specific_direct=80—100，concise_direct=60—79，partial=20—59，topic_only=1—19，none/insufficient=0；等级必须与分数对应。引文逐字连续包含于原unit_text，保留换行；不得改变事实、补默认评分或给参考答案。')
 def call(p):
  # UTF8字节数充当保守输入token上界，实际usage记账；每次调用预留最大输出费用。
  reserve=(len(json.dumps(payload(p,rules),ensure_ascii=False).encode('utf-8'))*.3+512*1.2)/1e6
  feedback=feedback_for(last_errors[p['pair_id']]) if p['pair_id'] in last_errors else None
  for attempt in range(1,MAX_ATTEMPTS+1):
   with lock:
    if state['spent']+state['reserved']+reserve>BUDGET:raise RuntimeError('预算保护触发，停止新调用')
    state['reserved']+=reserve
   started=datetime.now(timezone.utc);t=time.perf_counter();response=None;cost=None;error=None;opinion=None
   try:
    response=request(p,rules,key,feedback);cost=usage_cost(response.get('usage',{}),started)
    opinion=validate_completion(p,response)
   except Exception as e:error=redact(type(e).__name__+': '+str(e),key)
   with lock:
    state['reserved']-=reserve;state['attempts']+=1
    # 未拿到usage的异常请求按整个预留值计保守上界，不遗漏不确定收费。
    booked=cost['peak_price_bound_usd'] if cost else reserve
    state['spent']+=booked
    log={'pair_id':p['pair_id'],'attempt_in_run':attempt,'utc':started.isoformat(),
     'seconds':time.perf_counter()-t,'status':'accepted' if opinion else 'rejected',
     'cost':cost,'budget_booked_peak_bound_usd':booked,'error':error,
     'returned_model':response.get('model') if response else None,
     'response_id':response.get('id') if response else None,
     'had_validation_feedback':bool(feedback),
     'finish_reason':response.get('choices',[{}])[0].get('finish_reason') if response else None}
    append('requests.jsonl',log)
    if response:append('responses.jsonl',{'pair_id':p['pair_id'],'utc':started.isoformat(),'response':response})
    if opinion:
     g={**opinion,'query_text_sha256':p['query_text_sha256'],'unit_text_sha256':p['unit_text_sha256'],
      'origin':'actual_deepseek_flash_API','response_id':response.get('id'),'returned_model':response.get('model')}
     append('scores.jsonl',g);return g
   if error and ('HTTP 401' in error or 'HTTP 402' in error or 'HTTP 403' in error or 'HTTP 400' in error):raise RuntimeError(error)
   if attempt==MAX_ATTEMPTS:raise RuntimeError(error or '未知响应错误')
   if error and error.startswith('ValueError:'):feedback=feedback_for(error)
   time.sleep(1 if attempt==1 else 2)
 complete=len(prior);failures=[];started=time.perf_counter();last_emit=started
 with ThreadPoolExecutor(max_workers=1 if pilot else CONCURRENCY) as pool:
  it=iter(pending);active={}
  def schedule():
   p=next(it,None)
   if p is not None:active[pool.submit(call,p)]=p['pair_id']
  for _ in range(1 if pilot else CONCURRENCY):schedule()
  stop=False
  while active:
   done,_=wait(active,timeout=15,return_when=FIRST_COMPLETED)
   for f in done:
    pid=active.pop(f)
    try:f.result();complete+=1
    except Exception as e:failures.append({'pair_id':pid,'error':redact(str(e),key)});stop=True
    if not stop:schedule()
   if time.perf_counter()-last_emit>=20 or (not active):
    emit(status='running' if active else 'finished' if not failures else 'stopped',completed=complete,
     total=EXPECTED_PAIRS,requests=state['attempts'],booked_peak_bound_usd=round(state['spent'],6),
     elapsed_seconds=round(time.perf_counter()-started,2),failures=failures[:3]);last_emit=time.perf_counter()
 if failures:raise RuntimeError('有候选未完成，已增量保存，未补默认分；详见requests.jsonl')
 if pilot and complete:
  gg=rows(OUT/'scores.jsonl')[-1];emit(status='pilot_passed',returned_model=gg['returned_model'],score=gg['score'],level=gg['level'])
 if complete==EXPECTED_PAIRS:
  freeze_check();gg=rows(OUT/'scores.jsonl');assert len(gg)==len({g['pair_id'] for g in gg})==EXPECTED_PAIRS
  save('api_completion.json',{'status':'complete','scores':EXPECTED_PAIRS,'requests':state['attempts'],
   'concurrency':CONCURRENCY,'booked_peak_bound_usd':state['spent'],'human_approved':False})

