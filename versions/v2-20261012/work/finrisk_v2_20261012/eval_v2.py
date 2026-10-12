"""Offline source-grounded union-pool evaluation. Never assigns semantic grades.

Only exported source texts are loaded; candidate tables and frozen V1 tools are
not imported. A variant is an explicit label for one result JSONL file.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUBRIC = ROOT / 'work/finrisk_retrieval_20261012/judging_instructions.md'
GAP = '\n\n[原文间隔，分段摘录]\n\n'
FILE_FIELDS = ('help_grade','help_type','mechanism_match','conditions_match',
               'source_quote','reason','limitations','misleading_risk')
MAIN_METRICS = ('useful_at5','support_coverage_at5','strong_coverage_at5','mean_help_at5',
                'pool_conditional_ndcg_at5','context_useful_at5','context_coverage_at5',
                'context_strong_coverage_at5','mean_context_help_at5','context_pool_conditional_ndcg_at5',
                'misleading_at5','context_misleading_at5')
AUX_METRICS = ('known_source_hit_at5','known_source_hit_at10','known_source_hit_at20','known_source_rr_at20')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text_sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def pair_id(qid, fid):
    return 'J' + text_sha(qid+':'+fid)[:12]


def context_id(text):
    return 'C' + text_sha(text)[:12]


def read_rows(path):
    with Path(path).open(encoding='utf-8-sig') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')


def save_json(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def input_hashes(paths):
    return {str(Path(p).resolve()):file_sha(p) for p in paths}


def unique(rows, key, label):
    mapping = {}
    for row in rows:
        identity = row[key]
        require(identity not in mapping, f'duplicate {label}: {identity}')
        mapping[identity] = row
    return mapping


def load_queries(path):
    queries = unique(read_rows(path),'query_id','query')
    require(len(queries)==50, 'frozen evaluation requires exactly 50 queries')
    for q in queries.values():
        require(isinstance(q.get('text'),str) and q['text'].strip(), 'empty query text')
        require(isinstance(q.get('known_positive_file_ids',[]),list), 'known positives must be a list')
    return queries


def load_results(variants, queries):
    require(bool(variants),'no explicitly named result variants')
    results, groups, identities = [],defaultdict(set),set()
    for variant,path in variants.items():
        require(isinstance(variant,str) and bool(variant.strip()),'empty variant')
        rows = read_rows(path)
        require(bool(rows),f'empty results: {variant}')
        for original in rows:
            row = dict(original,variant=variant)
            qid = row['query_id']
            require(qid in queries, f'unknown query: {qid}')
            require(row['text']==queries[qid]['text'],f'query text drift: {qid}')
            require(all(isinstance(row.get(k),str) and row[k].strip() for k in ('corpus','arm')),'invalid group')
            identity = (variant,row['corpus'],row['arm'],qid)
            require(identity not in identities,f'duplicate result: {identity}')
            identities.add(identity)
            groups[identity[:3]].add(qid)
            hits = row['files']
            require(isinstance(hits,list),'files must be list')
            require(len({h['file_id'] for h in hits})==len(hits),f'duplicate files: {identity}')
            for rank,h in enumerate(hits,1):
                require(type(h.get('rank')) is int and h['rank']==rank,f'noncontiguous rank: {identity}')
                require(isinstance(h.get('unit_id'),str) and bool(h['unit_id']),f'missing unit: {identity}')
            results.append(row)
    for group,ids in groups.items():
        require(ids==set(queries), f'group must cover all 50 frozen queries: {group}')
    return results


def load_sources(repo):
    paths = sorted((Path(repo)/'data/sources').glob('*.jsonl'))
    require(bool(paths),'explicit repo/data/sources JSONL directory is empty')
    sources = {}
    for path in paths:
        with path.open(encoding='utf-8-sig') as stream:
            for line in stream:
                if not line.strip():continue
                row = json.loads(line);fid = row['file_id'];body = row['full_text']
                require(fid not in sources,f'duplicate source: {fid}')
                require(isinstance(body,str) and text_sha(body)==row['text_sha256'],f'source SHA mismatch: {fid}')
                sources[fid] = {'full_text':body,'text_sha256':row['text_sha256']}
    return sources, paths


def valid_span(span, source, text):
    require(isinstance(span,dict) and type(span.get('start')) is int and type(span.get('end')) is int,'invalid span')
    require(0<=span['start']<span['end']<=len(source),'span outside source')
    require(source[span['start']:span['end']]==text,'span text differs from exact source')


def validate_context(hit, source):
    prefix = hit.get('prefix','')
    require(isinstance(prefix,str),'invalid prefix')
    body,text,spans = hit['source_text'],hit['text'],hit['source_spans']
    require(isinstance(body,str) and bool(body.strip()) and isinstance(text,str),'empty or invalid context')
    require(isinstance(spans,list) and bool(spans),'missing source spans')
    context = {'context_id':context_id(text),'text':text,'prefix':prefix,
               'source_text':body,'source_spans':copy.deepcopy(spans)}
    if 'source_segments' in hit:
        segments = hit['source_segments']
        require(isinstance(segments,list) and bool(segments),'V2 context segments missing')
        require(not prefix,'V2 context prefix must be empty')
        require(len(segments)==len(spans),'segments/spans count mismatch')
        for segment,span in zip(segments,spans):
            require(isinstance(segment,dict) and isinstance(segment.get('text'),str) and bool(segment['text'].strip()),'invalid segment')
            require(segment.get('span')==span,'segment span binding mismatch')
            valid_span(span,source,segment['text'])
        require(body==''.join(s['text'] for s in segments),'marker-free source text differs from segments')
        require(text==GAP.join(s['text'] for s in segments),'visible gap marker or context text mismatch')
        context['source_segments'] = copy.deepcopy(segments)
    else:
        require(text==(prefix+'\n'+body if prefix else body),'V1 prefix/body mismatch')
        for span in spans:valid_span(span,source,body)
    for key in ('evidence_ambiguous','prefix_evidence_ambiguous','ambiguity_reason','context_long','context_ambiguous'):
        if key in hit:context[key] = copy.deepcopy(hit[key])
    return context


def validate_pool(rows):
    pool = unique(rows,'pair_id','pair')
    for pid,p in pool.items():
        require(pid==pair_id(p['query_id'],p['file_id']),f'forged pair: {pid}')
        require(text_sha(p['full_source_text'])==p['source_sha256'],f'pool source SHA drift: {pid}')
        contexts = unique(p['contexts'],'context_id','context')
        for cid,c in contexts.items():
            require(cid==context_id(c['text']),f'forged context: {cid}')
            checked = validate_context(c,p['full_source_text'])
            require(checked['context_id']==cid,'context hash mismatch')
    return pool


def validate_file_judgment(row, p):
    pid = p['pair_id']
    require(type(row.get('help_grade')) is int and 0<=row['help_grade']<=3,f'invalid file grade: {pid}')
    for key,options in [('help_type',('support','boundary','irrelevant')),
                        ('mechanism_match',('same','partial','different')),
                        ('conditions_match',('compatible','partial','conflict','unknown'))]:
        require(row.get(key) in options,f'invalid {key}: {pid}')
    require(isinstance(row.get('reason'),str) and row['reason'].strip(),f'missing reason: {pid}')
    require(isinstance(row.get('limitations'),list) and all(isinstance(x,str) for x in row['limitations']),f'invalid limitations: {pid}')
    require(type(row.get('misleading_risk')) is bool,f'invalid misleading risk: {pid}')
    quote = row.get('source_quote','')
    require(isinstance(quote,str) and (not quote or quote in p['full_source_text']),f'file quote not exact source: {pid}')
    require(row['help_grade']<2 or bool(quote.strip()),f'positive file grade without source quote: {pid}')


def validate_context_judgment(j, c, source):
    cid = c['context_id']
    require(type(j.get('help_grade')) is int and 0<=j['help_grade']<=3,f'invalid context grade: {cid}')
    require(isinstance(j.get('reason'),str) and j['reason'].strip(),f'missing context reason: {cid}')
    require(type(j.get('misleading_risk')) is bool,f'invalid context risk: {cid}')
    quote = j.get('evidence_quote','')
    require(isinstance(quote,str) and (not quote or (quote in c['text'] and quote in source)),f'context quote not continuous original source: {cid}')
    require(j['help_grade']<2 or bool(quote.strip()),f'positive context without exact source quote: {cid}')


def validate_judgment(row, p):
    validate_file_judgment(row,p)
    actual = unique(row.get('contexts',[]),'context_id','context judgment')
    expected = {c['context_id']:c for c in p['contexts']}
    require(set(actual)==set(expected),f'context coverage mismatch: {p["pair_id"]}')
    for cid,j in actual.items():validate_context_judgment(j,expected[cid],p['full_source_text'])


def cache_reusable(pool, queries_path, cache_pool, cache_judgments, cache_queries):
    if cache_pool is None:
        require(cache_judgments is None and cache_queries is None,'cache arguments must be supplied together')
        return [],[]
    require(cache_judgments is not None and cache_queries is not None,'cache requires pool, judgments and queries')
    paths = [cache_pool,cache_judgments,cache_queries]
    old = validate_pool(read_rows(cache_pool))
    old_queries = load_queries(cache_queries)
    judgments = unique(read_rows(cache_judgments),'pair_id','cached judgment')
    require(set(old)==set(judgments),'cached judgment coverage mismatch')
    for pid,p in old.items():
        require(p['query_id'] in old_queries and p['query_text']==old_queries[p['query_id']]['text'],'cache query binding mismatch')
        validate_judgment(judgments[pid],p)
    if file_sha(queries_path)!=file_sha(cache_queries):return [],paths
    reusable = []
    for pid,p in pool.items():
        previous = old.get(pid)
        if previous is None:continue
        if previous['source_sha256']!=p['source_sha256'] or previous['query_text']!=p['query_text']:continue
        row = {'pair_id':pid,**{k:copy.deepcopy(judgments[pid].get(k,'')) for k in FILE_FIELDS},'contexts':[]}
        old_contexts = {c['context_id']:c for c in previous['contexts']}
        old_j = {c['context_id']:c for c in judgments[pid]['contexts']}
        for c in p['contexts']:
            cid = c['context_id']
            if cid in old_contexts and old_contexts[cid]['text']==c['text']:
                validate_context_judgment(old_j[cid],c,p['full_source_text'])
                row['contexts'].append(copy.deepcopy(old_j[cid]))
        reusable.append(row)
    return reusable,paths


def build_pool(variants, queries_path, repo, output, *, cache_pool=None, cache_judgments=None, cache_queries=None):
    queries = load_queries(queries_path)
    results = load_results(variants,queries)
    sources,source_paths = load_sources(repo)
    pool,provenance = {},[]
    for r in results:
        qid = r['query_id']
        for rank,h in enumerate(r['files'][:5],1):
            fid = h['file_id'];pid = pair_id(qid,fid)
            require(fid in sources,f'unknown full source: {fid}')
            source = sources[fid]
            if pid not in pool:
                pool[pid] = {'pair_id':pid,'query_id':qid,'query_text':queries[qid]['text'],'file_id':fid,
                             'full_source_text':source['full_text'],'source_sha256':source['text_sha256'],'contexts':{}}
            p = pool[pid]
            require((p['query_id'],p['file_id'])==(qid,fid),'truncated pair hash collision')
            c = validate_context(h,source['full_text']);cid = c['context_id']
            if cid in p['contexts']:
                previous = p['contexts'][cid]
                require(previous['text']==c['text'] and previous['source_text']==c['source_text'] and previous['prefix']==c['prefix'],'context collision/inconsistent source binding')
                if 'source_segments' not in previous and 'source_segments' not in c:
                    c['source_spans'] = [dict(start=a,end=b) for a,b in sorted({(s['start'],s['end']) for s in previous['source_spans']+c['source_spans']})]
                for flag in ('evidence_ambiguous','prefix_evidence_ambiguous','context_ambiguous','context_long'):
                    if flag in previous or flag in c:c[flag] = bool(previous.get(flag)) or bool(c.get(flag))
                c['ambiguity_reason'] = c.get('ambiguity_reason') or previous.get('ambiguity_reason')
            p['contexts'][cid] = c
            provenance.append({'pair_id':pid,'context_id':cid,'query_id':qid,'file_id':fid,
                               'variant':r['variant'],'corpus':r['corpus'],'arm':r['arm'],'rank':rank,'unit_id':h['unit_id']})
    rows = list(pool.values())
    for p in rows:p['contexts'] = sorted(p['contexts'].values(),key=lambda c:c['context_id'])
    checked = validate_pool(rows)
    cached,cache_paths = cache_reusable(checked,queries_path,cache_pool,cache_judgments,cache_queries)
    cache_map = {c['pair_id']:c for c in cached}
    random.Random(20261012).shuffle(rows)
    pending = []
    for p in rows:
        cache = cache_map.get(p['pair_id'])
        old_ids = {c['context_id'] for c in cache['contexts']} if cache else set()
        missing = [c for c in p['contexts'] if c['context_id'] not in old_ids]
        if cache is None or missing:
            pending.append({**p,'contexts':missing,'needs_file_judgment':cache is None})
    out = Path(output);out.mkdir(parents=True,exist_ok=True)
    artifacts = {'blind_judgment_pool.jsonl':rows,'judgment_provenance.jsonl':provenance,'cached_judgments.jsonl':cached}
    query_parts = {qid:i%3 for i,qid in enumerate(sorted(queries))}
    for i in range(3):artifacts[f'judgment_part_{i+1}.jsonl'] = [p for p in pending if query_parts[p['query_id']]==i]
    for name,data in artifacts.items():write_rows(out/name,data)
    manifest = {'status':'complete','evaluation':'model_review_only','human_judgments':0,'human_approved':False,
                'queries':50,'source_files':len(sources),'retrieval_results':len(results),'unique_query_file_pairs':len(rows),
                'context_variants':sum(len(p['contexts']) for p in rows),'top5_slots':len(provenance),
                'pending_pairs':len(pending),'cached_files':len(cached),
                'cached_contexts':sum(len(c['contexts']) for c in cached),'blind_to_algorithm_and_rank':True,
                'variants':{k:str(Path(v).resolve()) for k,v in variants.items()},'queries_path':str(Path(queries_path).resolve()),
                'rubric_path':str(RUBRIC.resolve()),
                'input_sha256':input_hashes([queries_path,*variants.values(),*source_paths,*cache_paths,RUBRIC,Path(__file__)]),
                'artifact_sha256':{name:file_sha(out/name) for name in artifacts},
                'limitations':['source verification covers exported text only','model judgments are not human acceptance',
                               'nDCG is conditional on the union Top5 judged pool']}
    save_json(out/'judgment_pool_manifest.json',manifest)
    return manifest


def load_review(review):
    review = Path(review)
    manifest = json.loads((review/'judgment_pool_manifest.json').read_text(encoding='utf-8'))
    for path,expected in manifest['input_sha256'].items():
        require(file_sha(path)==expected,f'input SHA changed: {path}')
    for name,expected in manifest['artifact_sha256'].items():
        require(file_sha(review/name)==expected,f'review artifact SHA changed: {name}')
    pool = validate_pool(read_rows(review/'blind_judgment_pool.jsonl'))
    queries = load_queries(manifest['queries_path'])
    for p in pool.values():
        require(p['query_id'] in queries and p['query_text']==queries[p['query_id']]['text'],'pool/query binding mismatch')
    return manifest,pool,queries


def merge_judgments(review, judgment_paths, output):
    manifest,pool,_ = load_review(review)
    cached = unique(read_rows(Path(review)/'cached_judgments.jsonl'),'pair_id','cached judgment')
    pending = unique(sum((read_rows(Path(review)/f'judgment_part_{i}.jsonl') for i in range(1,4)),[]),'pair_id','pending pair')
    submitted = unique(sum((read_rows(p) for p in judgment_paths),[]),'pair_id','submitted judgment')
    require(set(submitted)==set(pending),f'pending pair coverage mismatch: missing={sorted(set(pending)-set(submitted))[:10]}, extra={sorted(set(submitted)-set(pending))[:10]}')
    rows = []
    for pid,p in pool.items():
        previous,new = cached.get(pid),submitted.get(pid)
        require(previous is not None or new is not None,f'missing judgment: {pid}')
        if previous is not None:
            validate_file_judgment(previous,p)
            row = {'pair_id':pid,**{k:copy.deepcopy(previous.get(k,'')) for k in FILE_FIELDS}}
            if new is not None:
                for k in FILE_FIELDS:
                    require(k not in new or new[k]==row[k],f'cached file grade may not be overwritten: {pid}:{k}')
        else:
            validate_file_judgment(new,p)
            row = {'pair_id':pid,**{k:copy.deepcopy(new.get(k,'')) for k in FILE_FIELDS}}
        old_contexts = previous['contexts'] if previous else []
        new_contexts = new.get('contexts',[]) if new else []
        if new is not None:
            current = unique(new_contexts,'context_id','new context judgment')
            require(set(current)=={c['context_id'] for c in pending[pid]['contexts']},f'pending contexts coverage mismatch: {pid}')
        row['contexts'] = sorted(unique(old_contexts+new_contexts,'context_id','merged context judgment').values(),key=lambda c:c['context_id'])
        validate_judgment(row,p);rows.append(row)
    out = Path(output);out.mkdir(parents=True,exist_ok=True)
    write_rows(out/'validated_judgments.jsonl',rows)
    save_json(out/'judgment_merge_manifest.json',{'status':'complete','evaluation':'model_review_only','human_judgments':0,
              'files':len(rows),'contexts':sum(len(r['contexts']) for r in rows),
              'input_sha256':{**manifest['input_sha256'],**input_hashes([Path(review)/'judgment_pool_manifest.json',*judgment_paths])},
              'validated_sha256':file_sha(out/'validated_judgments.jsonl')})
    return rows


def dcg(grades):
    return sum((2**g-1)/math.log2(i+2) for i,g in enumerate(grades))


def compute_metrics(review, judgments_path, output):
    manifest,pool,queries = load_review(review)
    merge_inputs = {}
    merge_path = Path(judgments_path).parent/'judgment_merge_manifest.json'
    if merge_path.exists():
        merge_manifest = json.loads(merge_path.read_text(encoding='utf-8'))
        require(file_sha(judgments_path)==merge_manifest['validated_sha256'],'merged judgment SHA changed')
        merge_inputs = merge_manifest['input_sha256']
        for path,expected in merge_inputs.items():
            require(file_sha(path)==expected,f'original judgment input SHA changed: {path}')
        merge_inputs = {**merge_inputs,**input_hashes([merge_path])}
    judgments = unique(read_rows(judgments_path),'pair_id','validated judgment')
    require(set(judgments)==set(pool),'complete judgment coverage required')
    for pid,j in judgments.items():validate_judgment(j,pool[pid])
    results = load_results(manifest['variants'],queries)
    provenance = read_rows(Path(review)/'judgment_provenance.jsonl')
    slots = {}
    for p in provenance:
        key = (p['variant'],p['corpus'],p['arm'],p['query_id'],p['rank'])
        require(key not in slots,'duplicate provenance slot');slots[key] = p
    ideal,context_ideal = defaultdict(list),defaultdict(list)
    for pid,p in pool.items():
        ideal[p['query_id']].append(judgments[pid]['help_grade'])
        # One best context per query/file prevents repeated contexts inflating ideal ranking.
        context_ideal[p['query_id']].append(max(c['help_grade'] for c in judgments[pid]['contexts']))
    per_query,groups,seen_slots = [],defaultdict(list),set()
    for result in results:
        qid = result['query_id'];identity = (result['variant'],result['corpus'],result['arm'])
        grades,cgrades,risky,crisky,details = [],[],[],[],[]
        for rank,hit in enumerate(result['files'][:5],1):
            key = (*identity,qid,rank);seen_slots.add(key)
            require(key in slots,'missing provenance slot')
            pid = pair_id(qid,hit['file_id']);cid = context_id(hit['text']);slot = slots[key]
            expected = {'pair_id':pid,'context_id':cid,'query_id':qid,'file_id':hit['file_id'],
                        'variant':identity[0],'corpus':identity[1],'arm':identity[2],'rank':rank,'unit_id':hit['unit_id']}
            require(slot==expected,'result/provenance identity mismatch')
            require(pid in pool,'result pair outside pool')
            validate_context(hit,pool[pid]['full_source_text'])
            j = judgments[pid];context = unique(j['contexts'],'context_id','context')[cid]
            grades.append(j['help_grade']);cgrades.append(context['help_grade'])
            risky.append(j['misleading_risk']);crisky.append(context['misleading_risk'])
            details.append({'rank':rank,'file_id':hit['file_id'],'unit_id':hit['unit_id'],'pair_id':pid,'context_id':cid,
                            'help_grade':j['help_grade'],'context_help_grade':context['help_grade'],
                            'reason':j['reason'],'context_reason':context['reason'],'source_quote':j['source_quote'],
                            'evidence_quote':context.get('evidence_quote',''),'limitations':j['limitations']})
        n = len(grades);grades += [0]*(5-n);cgrades += [0]*(5-n)
        denominator = dcg(sorted(ideal[qid],reverse=True)[:5]);cdenominator = dcg(sorted(context_ideal[qid],reverse=True)[:5])
        row = {'variant':identity[0],'corpus':identity[1],'arm':identity[2],'query_id':qid,
               'query_text':queries[qid]['text'],'group':queries[qid].get('group','unspecified'),'returned_files':n,
               'useful_at5':sum(g>=2 for g in grades)/5,'support_coverage_at5':int(any(g>=2 for g in grades)),
               'strong_coverage_at5':int(any(g==3 for g in grades)),'mean_help_at5':sum(grades)/5,
               'pool_conditional_ndcg_at5':dcg(grades)/denominator if denominator else None,
               'context_useful_at5':sum(g>=2 for g in cgrades)/5,'context_coverage_at5':int(any(g>=2 for g in cgrades)),
               'context_strong_coverage_at5':int(any(g==3 for g in cgrades)),'mean_context_help_at5':sum(cgrades)/5,
               'context_pool_conditional_ndcg_at5':dcg(cgrades)/cdenominator if cdenominator else None,
               'misleading_at5':sum(risky)/5,'context_misleading_at5':sum(crisky)/5,'top5':details,
               'timing':result.get('timing',{})}
        positives = set(queries[qid].get('known_positive_file_ids',[]))
        if positives:
            hits = [h['file_id'] for h in result['files'][:20]]
            for k in (5,10,20):row[f'known_source_hit_at{k}'] = int(bool(positives.intersection(hits[:k])))
            first = next((i for i,h in enumerate(hits,1) if h in positives),None)
            row['known_source_rr_at20'] = 1/first if first else 0
        groups[identity].append(row);per_query.append(row)
    require(seen_slots==set(slots),'extra provenance slots')
    summaries = []
    for identity,rows in sorted(groups.items()):
        summary = {'variant':identity[0],'corpus':identity[1],'arm':identity[2],'queries':len(rows),
                   'actual_top5_slots':sum(r['returned_files'] for r in rows)}
        for metric in MAIN_METRICS+AUX_METRICS:
            values = [r[metric] for r in rows if r.get(metric) is not None]
            summary[metric] = statistics.mean(values) if values else None;summary[metric+'_n'] = len(values)
        summary['by_group'] = {}
        for group in sorted({r['group'] for r in rows}):
            sub = [r for r in rows if r['group']==group];stats = {'n':len(sub)}
            for metric in MAIN_METRICS:
                values = [r[metric] for r in sub if r.get(metric) is not None]
                stats[metric] = statistics.mean(values) if values else None;stats[metric+'_n'] = len(values)
            summary['by_group'][group] = stats
        summaries.append(summary)
    paths = [Path(review)/'judgment_pool_manifest.json',judgments_path,
             *[Path(review)/name for name in manifest['artifact_sha256']]]
    summary = {'status':'complete','evaluation':'model_review_only','human_judgments':0,'human_approved':False,
               'queries':50,'unique_query_file_pairs':len(pool),'context_variants':sum(len(p['contexts']) for p in pool.values()),
               'metrics':summaries,'input_sha256':{**manifest['input_sha256'],**merge_inputs,**input_hashes(paths)},
               'metric_scope':'helpfulness and known-source recovery; nDCG conditional on union Top5 judged pool',
               'limitations':manifest['limitations']}
    out = Path(output);out.mkdir(parents=True,exist_ok=True)
    write_rows(out/'validated_judgments.jsonl',judgments.values())
    write_rows(out/'per_query_metrics.jsonl',per_query);save_json(out/'metrics.json',summary)
    return summary


def parse_variants(values):
    variants = {}
    for value in values:
        variant,separator,path = value.partition('=')
        require(bool(separator) and bool(path) and variant not in variants,'results must be unique variant=path')
        variants[variant] = path
    return variants


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    build = commands.add_parser('build-pool')
    build.add_argument('--results',nargs='+',required=True,metavar='VARIANT=PATH')
    build.add_argument('--queries',required=True);build.add_argument('--repo',required=True);build.add_argument('--output',required=True)
    build.add_argument('--cache-pool');build.add_argument('--cache-judgments');build.add_argument('--cache-queries')
    merge = commands.add_parser('merge');merge.add_argument('--review',required=True)
    merge.add_argument('--judgments',nargs='*',default=[]);merge.add_argument('--output',required=True)
    metrics = commands.add_parser('metrics');metrics.add_argument('--review',required=True)
    metrics.add_argument('--judgments',required=True);metrics.add_argument('--output',required=True)
    args = parser.parse_args()
    if args.command=='build-pool':
        result = build_pool(parse_variants(args.results),args.queries,args.repo,args.output,
                            cache_pool=args.cache_pool,cache_judgments=args.cache_judgments,cache_queries=args.cache_queries)
        print(json.dumps({k:result[k] for k in ('status','retrieval_results','unique_query_file_pairs','context_variants','pending_pairs','cached_files','cached_contexts')},ensure_ascii=False))
    elif args.command=='merge':
        result = merge_judgments(args.review,args.judgments,args.output)
        print(json.dumps({'status':'complete','files':len(result),'contexts':sum(len(r['contexts']) for r in result)}))
    else:
        result = compute_metrics(args.review,args.judgments,args.output)
        print(json.dumps({'status':result['status'],'queries':result['queries'],'groups':len(result['metrics'])}))


if __name__=='__main__':main()
