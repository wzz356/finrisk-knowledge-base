"""Local JSONL worker: retain one validated reader for repeated tool calls."""
import argparse
import json
import sys
import sqlite3
from pathlib import Path
from evidence_runtime import EvidenceRuntime
from runtime_common import read,sha

OPERATIONS={'list_mechanisms','read_mechanism','read_article','read_case','read_span','get_coverage','get_dependencies','get_input_coverage','get_evidence_bundle'}

def dispatch(runtime,request):
    if not isinstance(request,dict) or set(request)!={'operation','arguments'} or request['operation'] not in OPERATIONS or not isinstance(request['arguments'],dict):raise ValueError('registered operation and named arguments required')
    return getattr(runtime,request['operation'])(**request['arguments'])

def handle_line(runtime,line):
    try:return dict(ok=True,result=dispatch(runtime,json.loads(line)))
    except (ValueError,TypeError,KeyError,sqlite3.Error) as exc:return dict(ok=False,error_type=type(exc).__name__,message=str(exc))

def main():
    p=argparse.ArgumentParser(description='只读本地知识工具；serve保持实例，避免逐请求全库冷启动。')
    p.add_argument('--root',type=Path,required=True);p.add_argument('--pin',required=True)
    p.add_argument('command',choices=['status','verify','serve','request']);p.add_argument('--request-file',type=Path)
    args=p.parse_args();mp=args.root/'contracts/runtime_manifest.json'
    if sha(mp)!=args.pin:raise ValueError('runtime manifest pin mismatch')
    manifest=read(mp)
    if args.command=='status':
        report=dict(schema=manifest['schema'],manifest_pin_verified=True,full_payload_and_records_checked_this_process=False,
            registered_counts=dict(documents=9639,units=110878,legal_articles=67,mechanisms=12),
            versions=manifest['full_reader']['versions'],API_calls=0,production_active=False)
        print(json.dumps(report,ensure_ascii=False));return
    with EvidenceRuntime(args.root,args.pin) as runtime:
        if args.command=='verify':
            print(json.dumps(dict(passed=True,full_reader_validation=runtime.reader.validation,startup_seconds=runtime.reader.startup_seconds,cache=runtime.reader.cache_info(),API_calls=0),ensure_ascii=False));return
        if args.command=='request':
            if args.request_file is None:p.error('--request-file required')
            print(json.dumps(dispatch(runtime,read(args.request_file)),ensure_ascii=False));return
        print(json.dumps(dict(ready=True,operations=sorted(OPERATIONS),startup_seconds=runtime.reader.startup_seconds),ensure_ascii=False),flush=True)
        for line in sys.stdin:
            if not line.strip():continue
            print(json.dumps(handle_line(runtime,line),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
