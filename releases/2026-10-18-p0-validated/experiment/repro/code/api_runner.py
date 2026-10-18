"""One bounded, resumable DeepSeek owner; preserves every attempt and charge."""
import argparse
import http.client
import math
import os
import re
import ssl
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor,as_completed
from effect_common import *
from protocol import validate_job,validate_result,strict_json

LOCAL=threading.local()
ALLOWED_MODELS={'deepseek-flash','deepseek-v4.1-flash','deepseek-v4.1-flash-1017'}

def append(path,value):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a',encoding='utf-8') as f:f.write(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())

class Ledger:
    def __init__(self,path,cap):
        if type(cap) not in (int,float) or not math.isfinite(cap) or cap<=0:raise ValueError('positive finite cap required')
        self.path=Path(path);self.cap=cap;self.lock=threading.RLock();self.reservations={};self.settled={};self.total=0.
        for r in rows(self.path) if self.path.exists() else []:
            if r['cap']!=cap:raise ValueError('budget cap cannot change')
            rid=r['reservation_id']
            if r['event']=='reserve':
                if rid in self.reservations:raise ValueError('duplicate reservation')
                self.reservations[rid]=r;self.total+=r['amount']
            elif r['event']=='settle':
                if rid not in self.reservations or rid in self.settled:raise ValueError('orphan/double settlement')
                self.settled[rid]=r;self.total+=r['booked_usd']-self.reservations[rid]['amount']
            else:raise ValueError('unknown ledger event')
    def booked(self):
        with self.lock:return self.total
    def reserve(self,phase,pid,amount,base_payload_sha256=None):
        with self.lock:
            if type(amount) not in (int,float) or not math.isfinite(amount) or amount<=0 or self.total+amount>self.cap+1e-12:raise ValueError('budget cap reached before dispatch')
            rid=uuid.uuid4().hex;r=dict(event='reserve',reservation_id=rid,phase=phase,pair_id=pid,amount=amount,base_payload_sha256=base_payload_sha256,cap=self.cap,utc=utc())
            append(self.path,r);self.reservations[rid]=r;self.total+=amount;return rid
    def settle(self,rid,cost):
        with self.lock:
            if rid not in self.reservations or rid in self.settled:raise ValueError('absent/double settlement')
            amount=self.reservations[rid]['amount'];charge=amount if cost is None else cost
            if type(charge) not in (int,float) or not math.isfinite(charge) or charge<0:raise ValueError('invalid charge')
            r=dict(event='settle',reservation_id=rid,booked_usd=charge,unknown_usage=cost is None,cap=self.cap,utc=utc())
            append(self.path,r);self.settled[rid]=r;self.total+=charge-amount
            if charge>amount+1e-12:raise ValueError('actual usage exceeded worst-case reservation; stop')

def validate_authorization(auth,plan,plan_sha):
    if auth.get('authorized') is not True or auth.get('scope')!=plan.get('scope') or auth.get('model')!='deepseek-flash' or type(auth.get('hard_cap_usd')) not in (int,float) or not 0<auth['hard_cap_usd']<=plan['proposed_hard_cap_usd'] or auth.get('request_plan_sha256')!=plan_sha or not auth.get('human_authorization_reference'):raise ValueError('new scoped human fee authorization required before key access')
    return True

def usage_bound(u):
    if not isinstance(u,dict):raise ValueError('invalid provider usage object')
    n=u.get('prompt_tokens');o=u.get('completion_tokens')
    if 'prompt_cache_hit_tokens' in u:hit=u['prompt_cache_hit_tokens']
    else:
        details=u.get('prompt_tokens_details') or {}
        if not isinstance(details,dict):raise ValueError('invalid usage details')
        hit=details.get('cached_tokens',0)
    if type(n) is not int or type(o) is not int or type(hit) is not int or not 0<=hit<=n or o<0:raise ValueError('invalid provider usage')
    return ((n-hit)*.3+hit*.006+o*1.2)/1e6

def decode_response(raw):
    value=strict_json(raw)
    if not isinstance(value,dict):raise ValueError('provider response must be an object')
    return value

def redact(text,key):return re.sub(r'sk-[A-Za-z0-9_-]{16,}','[REDACTED]',str(text).replace(key,'[REDACTED]'))

def request(payload,key):
    conn=getattr(LOCAL,'conn',None);sent=False
    try:
        if conn is None or conn.sock is None:
            conn=http.client.HTTPSConnection('api.deepseek.com',timeout=20,context=ssl.create_default_context());conn.connect();conn.sock.settimeout(90);LOCAL.conn=conn
        sent=True;conn.request('POST','/chat/completions',body=payload,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        response=conn.getresponse();status=response.status;raw=redact(response.read().decode('utf-8'),key)
        if response.will_close or status!=200:conn.close();LOCAL.conn=None
        return dict(http_status=status,raw_response_text=raw,error=None if status==200 else 'HTTP '+str(status),no_HTTP_body_sent=False)
    except Exception as exc:
        if conn:conn.close()
        LOCAL.conn=None
        return dict(http_status=None,raw_response_text=None,error=redact(type(exc).__name__+': '+str(exc),key),no_HTTP_body_sent=not sent)

def save_phase(folder,result,completion,attempt_count):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    if completion.get('terminal',completion['complete']):
        path=folder/'accepted.jsonl'
        if path.exists():
            if list(rows(path))!=result:raise ValueError('complete accepted phase snapshot changed')
        else:save(path,result,True)
        completion={**completion,'accepted_sha256':sha(path)}
        p=folder/'completion.json'
        if p.exists():
            if read(p)['accepted_sha256']!=completion['accepted_sha256']:raise ValueError('completed phase changed')
        else:save(p,completion)
    else:
        p=folder/('checkpoint_'+str(attempt_count).zfill(6)+'.json')
        if not p.exists():save(p,completion)
    return completion

def run(phase):
    if phase not in {'development_initial','development_judgment','holdout_initial','holdout_judgment'}:raise ValueError('unregistered experiment phase')
    plan_path=OUT/'contracts/api_request_plan.json';plan=read(plan_path);auth=read(OUT/'authorization.json');validate_authorization(auth,plan,sha(plan_path))
    verify(read(OUT/'contracts/pre_inference_freeze.json')['sha256'])
    if phase.startswith('holdout'):
        gate=read(OUT/'api/development_judgment/completion.json')
        if not gate.get('terminal') or not gate['all_tasks_attempted']:raise ValueError('development must be terminal before holdout')
    jp=OUT/'api_jobs'/(phase+'.jsonl');verify(read(jp.with_suffix('.freeze.json'))['sha256']);jobs=list(rows(jp))
    if len({j['pair_id'] for j in jobs})!=len(jobs):raise ValueError('duplicate task ID')
    for j in jobs:validate_job(j)
    (OUT/'api').mkdir(exist_ok=True);handle=(OUT/'api/run.lock').open('a+b');handle.seek(0,os.SEEK_END)
    if handle.tell()==0:handle.write(b'0');handle.flush()
    import msvcrt
    handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
    try:
        ledger=Ledger(OUT/'api/ledger.jsonl',auth['hard_cap_usd']);records=list(rows(OUT/'api/records.jsonl')) if (OUT/'api/records.jsonl').exists() else []
        # A crashed in-flight request remains charged at the complete reservation.
        for rid in set(ledger.reservations)-set(ledger.settled):ledger.settle(rid,None)
        cache={};bindings={};kind_ids={k:set() for k in plan['max_unique_tasks']}
        for r in records:
            key=(r['pair_id'],r['base_payload_sha256']);prior=bindings.setdefault(r['pair_id'],r['base_payload_sha256'])
            if prior!=r['base_payload_sha256']:raise ValueError('same task ID changed request')
            kind_ids[r['kind']].add(r['pair_id'])
            if r['status']=='accepted':
                if key in cache:raise ValueError('duplicate accepted paid identity')
                cache[key]=r
        accepted={};todo=[];attempts={};budget_lock=threading.RLock();stop=threading.Event();errors=[]
        for j in jobs:
            pid=j['pair_id'];digest=canonical_sha(j['body']);kind_ids[j['kind']].add(pid)
            if pid in bindings and bindings[pid]!=digest:raise ValueError('request changed across resume')
            prior=[r for r in ledger.reservations.values() if r['pair_id']==pid]
            if any(r.get('base_payload_sha256') not in (None,digest) for r in prior):raise ValueError('reservation request binding differs')
            attempts[pid]=len(prior)
            if (pid,digest) in cache:validate_result(j,cache[(pid,digest)]['parsed']);accepted[pid]=cache[(pid,digest)]
            elif attempts[pid]<plan['max_attempts_per_task']:todo.append(j)
        if any(len(ids)>plan['max_unique_tasks'][kind] for kind,ids in kind_ids.items()):raise ValueError('authorized unique-task cap exceeded')
        # Every scope/job/freeze/cache/amount check above precedes credential access.
        matches=set(re.findall(r'sk-[A-Za-z0-9_-]{16,}',Path('C:/Users/11051/Desktop/deepseek.txt').read_text(encoding='utf-8-sig')))
        if len(matches)!=1:raise ValueError('credential file must contain one recognizable key')
        key=next(iter(matches));matches=None;runner_sha=sha(Path(__file__));source=OUT/'api/runner_sources'/(runner_sha+'.py');source.parent.mkdir(exist_ok=True)
        if not source.exists():source.write_bytes(Path(__file__).read_bytes())
        def worker(j):
            feedback=None;pid=j['pair_id'];base=canonical_sha(j['body'])
            for attempt in range(attempts[pid]+1,plan['max_attempts_per_task']+1):
                if stop.is_set():return
                b=j['body'] if feedback is None else {**j['body'],'messages':j['body']['messages']+[dict(role='user',content=feedback)]}
                payload=json.dumps(b,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
                amount=((len(payload)+2048)*.3+b['max_tokens']*1.2)/1e6
                try:rid=ledger.reserve(phase,pid,amount,base)
                except ValueError as exc:stop.set();errors.append(str(exc));return
                started=time.perf_counter();obs=request(payload,key);parsed=None;usage=None;cost=None;error=obs['error'];fatal=False;model=None
                if obs['http_status']==200:
                    try:
                        response=decode_response(obs['raw_response_text']);model=response.get('model')
                        if not isinstance(model,str):raise ValueError('returned model must be a string')
                        if model not in ALLOWED_MODELS:fatal=True;raise ValueError('unapproved returned model: '+str(model))
                        usage=response.get('usage')
                        try:cost=usage_bound(usage)
                        except ValueError:cost=None
                        choices=response['choices']
                        if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict) or choices[0].get('finish_reason')!='stop' or not isinstance(choices[0].get('message'),dict):raise ValueError('incomplete completion')
                        parsed=validate_result(j,strict_json(choices[0]['message']['content']))
                    except (ValueError,KeyError,TypeError,IndexError) as exc:error=str(exc)
                if obs['no_HTTP_body_sent']:cost=0
                unknown=obs['http_status'] is None and not obs['no_HTTP_body_sent']
                record=dict(pair_id=pid,kind=j['kind'],phase=phase,attempt=attempt,reservation_id=rid,base_payload_sha256=base,payload_sha256=textsha(payload.decode('utf-8')),runner_sha256=runner_sha,
                    status='accepted' if parsed is not None else 'unknown' if unknown else 'rejected',parsed=parsed,usage=usage,returned_model=model,reserved_usd=amount,booked_peak_bound_usd=amount if cost is None else cost,
                    error=redact(error,key),seconds=time.perf_counter()-started,utc=utc(),**{k:v for k,v in obs.items() if k!='error'})
                with budget_lock:
                    append(OUT/'api/records.jsonl',record);ledger.settle(rid,cost)
                    if parsed is not None:
                        accepted[pid]=record
                        if len(accepted)%50==0 or len(accepted)==len(jobs):print(json.dumps(dict(phase=phase,accepted=len(accepted),total=len(jobs),booked_peak_bound_usd=ledger.booked())),flush=True)
                if parsed is not None:return
                if fatal or obs['http_status'] in (400,401,402,403):stop.set();errors.append(str(error));return
                feedback=None if unknown or obs['no_HTTP_body_sent'] else '只修正JSON结构、缺字段或当前输入逐字引用，不改变判断标准，不提供答案。结构错误：'+str(error)
                if attempt<plan['max_attempts_per_task']:stop.wait(attempt)
        try:
            with ThreadPoolExecutor(max_workers=plan['max_workers']) as pool:
                futures=[pool.submit(worker,j) for j in todo]
                for f in as_completed(futures):
                    try:f.result()
                    except Exception:stop.set();raise
        finally:key=None
        folder=OUT/'api'/phase
        result=[accepted[j['pair_id']] for j in jobs if j['pair_id'] in accepted]
        all_pids={r['pair_id'] for r in ledger.reservations.values()};completion=dict(complete=len(result)==len(jobs),all_tasks_attempted=all(j['pair_id'] in all_pids or j['pair_id'] in accepted for j in jobs),
            accepted=len(result),tasks=len(jobs),missing=[j['pair_id'] for j in jobs if j['pair_id'] not in accepted],jobs_sha256=sha(jp),booked_peak_bound_usd=ledger.booked(),actual_invoice_verified=False,errors=errors)
        counts={}
        for r in ledger.reservations.values():counts[r['pair_id']]=counts.get(r['pair_id'],0)+1
        completion['terminal']=completion['complete'] or all(counts.get(pid,0)>=plan['max_attempts_per_task'] for pid in completion['missing'])
        completion=save_phase(folder,result,completion,len(ledger.reservations));print(json.dumps(completion,ensure_ascii=False),flush=True)
        if not completion['complete'] and not (phase.endswith('_judgment') and completion['terminal']):raise RuntimeError('phase incomplete; failures retained, no default scores')
    finally:
        handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1);handle.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase');a=p.parse_args();run(a.phase)
