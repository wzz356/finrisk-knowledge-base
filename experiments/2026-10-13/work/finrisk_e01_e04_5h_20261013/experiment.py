"""Five-hour E01/E02/E03/E04 experiment, actual local inference only.

The immutable source unit ID is a parent reference; changed views carry a
text-SHA representation ID. No old reranker logits or query vectors are reused.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import sys
import time
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"
E02_OUT = ROOT / "outputs/FinRisk_E02小批量实验_20261013"
E04_OUT = ROOT / "outputs/FinRisk_E04小批量实验_20261012"
E04_CODE = ROOT / "work/finrisk_e04_pilot_20261012/experiment.py"
E04_CODE_SHA = "dc2269e588af38966be1e2675fb7c86f1caab60f0e11e88e535574cd3a07c46e"
E04_DELIVERY_SHA = "6626ef4872f3b70e2a5c110601ae612db24dfb50336c287656448f879547e30a"
ARMS = {"B0":dict(weights=[1,1],depth=100,view="B0"),
        "S1":dict(weights=[1,1],depth=100,view="S1"),
        "C2":dict(weights=[1,1],depth=100,view="C2"),
        "W4":dict(weights=[2,1],depth=100,view="B0"),
        "M3":dict(weights=[1,1,1],depth=100,view="B0")}
CARD_TOP_K = 2
SIDECARS = ("", ".partial", ".run.json", ".failure.json", ".score_pool.jsonl", ".token_audit.jsonl")
LABELS = {"文书主体", "片段主体", "责任角色", "行为背景", "适用条件", "材料用途", "产品背景"}
GAP = "\n\n[原文间隔，分段摘录]\n\n"
PREFIX_HEADER = "【仅适用于下方命中片段的背景（原文摘录，候选）】"
SCOPE_BODY_HEADER = "【命中原话的对应原文（逐段独立，不合并主体）】"


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""): digest.update(block)
    return digest.hexdigest()


def check_sha(path, expected):
    if sha_file(path) != expected: raise ValueError("SHA256 mismatch: "+str(path))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def save_json(path, value):
    Path(path).write_bytes(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False).encode("utf-8")+b"\n")


def emit(event, **fields):
    print(json.dumps(dict(event=event,**fields),ensure_ascii=True,allow_nan=False),flush=True)


@lru_cache(maxsize=1)
def frozen_e04():
    check_sha(E04_CODE,E04_CODE_SHA)
    spec = importlib.util.spec_from_file_location("fiveh_frozen_e04",E04_CODE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_new_output(output):
    for suffix in SIDECARS:
        path = Path(str(output)+suffix)
        if path.exists(): raise FileExistsError("refusing to overwrite output/sidecar: "+str(path))


def validate_cache_path(cache):
    path = Path(cache).resolve()
    if path == HERE or not path.is_relative_to(HERE):
        raise ValueError("cache must be an isolated child of new five-hour work directory")
    return path


def validate_freeze(path, required):
    hashes = read_json(path).get("files_sha256")
    if not isinstance(hashes,dict) or not hashes: raise ValueError("execution freeze files_sha256 missing")
    normalized = {}
    for name,digest in hashes.items():
        target = Path(name)
        if not target.is_absolute() or not isinstance(digest,str) or len(digest)!=64:
            raise ValueError("execution freeze requires absolute paths and SHA256")
        key = str(target.resolve())
        if key in normalized: raise ValueError("duplicate execution freeze path")
        check_sha(target,digest)
        normalized[key] = digest
    if not {str(Path(p).resolve()) for p in required}.issubset(normalized):
        raise ValueError("required input/code absent from execution freeze")
    normalized[str(Path(path).resolve())] = sha_file(path)
    return normalized


def validate_queries(queries, replay):
    allowed = {"query_id","text","group","query_role","replay_origin"}
    if len(queries)!=42 or len({q.get("query_id") for q in queries})!=42:
        raise ValueError("requires exactly 42 unique inputs")
    old_texts = {q["text"] for q in replay.values()}
    seen_replay, new_roles = set(), []
    for query in queries:
        if set(query)!=allowed or any(not isinstance(query.get(k),str) or not query[k].strip() for k in ("query_id","text","group")) or query.get("query_role") not in {"risk","boundary"}:
            raise ValueError("invalid query schema/text/role")
        if query["query_id"] in replay:
            original = replay[query["query_id"]]
            if any(query[k]!=original[k] for k in ("query_id","text","group","query_role")) or not query["replay_origin"]:
                raise ValueError("replay differs from frozen E04 input")
            seen_replay.add(query["query_id"])
        else:
            if query["replay_origin"] not in {None,"new_business_text_not_human_gold"} or query["text"] in old_texts:
                raise ValueError("new input contains replay text/origin")
            new_roles.append(query["query_role"])
    if seen_replay != set(replay) or len(seen_replay)!=22 or len(new_roles)!=20 or new_roles.count("risk")!=10 or new_roles.count("boundary")!=10:
        raise ValueError("requires old22 plus new10 risk/new10 boundary inputs")
    return dict(new=20,replay=22,new_risk=10,new_boundary=10)


def quote_span(source, text, span):
    if not isinstance(text,str) or not text or not isinstance(span,dict): raise ValueError("invalid source quote/span")
    start,end = span.get("start"),span.get("end")
    if type(start) is not int or type(end) is not int or not 0<=start<end<=len(source) or source[start:end]!=text:
        raise ValueError("exact source quote/span mismatch")


def all_spans(source, text):
    spans, position = [],0
    while True:
        start = source.find(text,position)
        if start<0: break
        spans.append(dict(start=start,end=start+len(text)))
        position = start+1
    return spans


def validate_review(review, row, input_sha, field, *, source_sha=None):
    if not isinstance(review,dict) or review.get("status") not in {"approved_model_review","rejected"} or review.get(field)!=input_sha or review.get("row_sha256")!=hashlib.sha256(canonical(row)).hexdigest() or not isinstance(review.get("reason"),str) or not review["reason"].strip() or review.get("human_approved") is not False:
        raise ValueError("review status/full-input/row SHA/reason binding differs")
    if source_sha is not None and review.get("source_sha256")!=source_sha:
        raise ValueError("review source SHA binding differs")


def validate_scope_units(rows, reviews, cohort, unit_map, sources, input_sha):
    selected = {r["unit_id"]:r for r in cohort["rows"]}
    by_id = {r["unit_id"]:r for r in rows}
    review_map = {r["unit_id"]:r for r in reviews}
    if len(selected)!=len(cohort["rows"]) or len(by_id)!=len(rows) or set(by_id)!=set(selected) or len(review_map)!=len(reviews) or set(review_map)!=set(by_id):
        raise ValueError("scope/review cohort population differs")
    approved = {}
    for uid,row in by_id.items():
        unit = unit_map.get(uid)
        source = sources.get(row.get("file_id"))
        if unit is None or not isinstance(source,str) or row.get("file_id")!=unit["file_id"]:
            raise ValueError("scope source/unit identity differs")
        expected = dict(file_id=unit["file_id"],source_sha256=sha_text(source),base_unit_text_sha256=sha_text(unit["text"]))
        if unit["source_sha256"]!=expected["source_sha256"] or any(row.get(k)!=v or selected[uid].get(k)!=v for k,v in expected.items()):
            raise ValueError("scope source/base-unit SHA binding differs")
        segments,status = row.get("segments"),row.get("scope_status")
        if not isinstance(segments,list) or not 1<=len(segments)<=4 or status not in {"scoped","single_subject","ambiguous_unchanged"} or not isinstance(row.get("scope_reason"),str) or not row["scope_reason"].strip():
            raise ValueError("invalid scope status/segments/reason")
        for segment in segments:
            quote_span(source,segment.get("text"),segment.get("span"))
            if not isinstance(segment.get("role"),str) or not segment["role"] or not isinstance(segment.get("reason"),str) or not segment["reason"].strip():
                raise ValueError("scope segment role/reason missing")
        if row.get("indexed_text")!="\n".join(s["text"] for s in segments):
            raise ValueError("scope indexed text differs from exact joined segments")
        spans = all_spans(source,unit["text"])
        if not spans or not any(unit["text"] in s["text"] for s in segments):
            raise ValueError("scope must include original unit as source quote")
        if len(spans)>1 and status!="ambiguous_unchanged" and any(not any(s["span"]["start"]<=p["start"] and p["end"]<=s["span"]["end"] for s in segments) for p in spans):
            raise ValueError("scope drops ambiguous original unit occurrences")
        claims = row.get("prefix_claims")
        if not isinstance(claims,list) or len(claims)>3: raise ValueError("invalid prefix claims")
        rendered=[]
        for claim in claims:
            if claim.get("label") not in LABELS or not isinstance(claim.get("link_reason"),str) or not claim["link_reason"].strip():
                raise ValueError("invalid prefix label/link reason")
            quote_span(source,claim.get("quote"),claim.get("span"))
            rendered.append(claim["label"]+"："+claim["quote"])
        if row.get("prefix_text")!="\n".join(rendered) or len(row["prefix_text"])>180:
            raise ValueError("prefix must equal labelled exact source quotes, <=180 characters")
        if status=="ambiguous_unchanged" and (row["indexed_text"]!=unit["text"] or claims or row["prefix_text"]):
            raise ValueError("ambiguous unchanged scope cannot alter text or apply exclusive prefix")
        validate_review(review_map[uid],row,input_sha,"scope_units_sha256",source_sha=expected["source_sha256"])
        if review_map[uid]["status"]=="approved_model_review" and status!="ambiguous_unchanged": approved[uid]=row
    return approved


def validate_mechanism_cards(cards, reviews, unit_map, sources, input_sha, *, minimum=3):
    if not minimum<=len(cards)<=5 or len({c.get("card_id") for c in cards})!=len(cards):
        raise ValueError("requires 3-5 unique candidate mechanism cards")
    review_map={r["card_id"]:r for r in reviews}
    if len(review_map)!=len(reviews) or set(review_map)!={c["card_id"] for c in cards}:
        raise ValueError("mechanism review population differs")
    approved=[]
    for card in cards:
        if not isinstance(card.get("card_id"),str) or not card["card_id"] or card.get("status")!="candidate_model" or card.get("human_approved") is not False or any(not isinstance(card.get(k),str) or not card[k].strip() for k in ("title","mechanism","retrieval_text")) or not card.get("conditions") or "boundary_notes" not in card or not card.get("limitations"):
            raise ValueError("invalid candidate mechanism schema")
        supports=card.get("supports")
        if not isinstance(supports,list) or len({s.get("file_id") for s in supports})<2:
            raise ValueError("mechanism requires support from at least two sources")
        for support in supports:
            unit=unit_map.get(support.get("unit_id"));source=sources.get(support.get("file_id"))
            if unit is None or not isinstance(source,str) or support.get("file_id")!=unit["file_id"] or support.get("source_sha256")!=sha_text(source) or unit["source_sha256"]!=sha_text(source):
                raise ValueError("mechanism support unit/source binding differs")
            quote_span(source,support.get("quote"),support.get("span"))
            # A source-complete fact can restore a parent's clipped paragraph
            # and stop before the following proof paragraph. Require an actual
            # nonempty source-position intersection, rather than text containment.
            sp=support["span"]
            matching=all_spans(source,unit["text"])
            if not any(max(sp["start"],p["start"])<min(sp["end"],p["end"]) and
                source[max(sp["start"],p["start"]):min(sp["end"],p["end"])].strip() for p in matching):
                raise ValueError("mechanism support quote does not identify recalled unit")
            if not isinstance(support.get("role"),str) or not support["role"]: raise ValueError("support role missing")
        validate_review(review_map[card["card_id"]],card,input_sha,"mechanism_cards_sha256")
        if review_map[card["card_id"]]["status"]=="approved_model_review": approved.append(card)
    if len(approved)<minimum: raise ValueError("too few approved mechanism cards")
    return approved


def representation_id(unit, text):
    return unit["unit_id"]+":5h-view:"+sha_text(text)


def make_views(units, approved):
    if not set(approved).issubset({u["unit_id"] for u in units}): raise ValueError("scope overlay unknown unit")
    views={"B0":units,"S1":[],"C2":[]}
    for unit in units:
        row=approved.get(unit["unit_id"])
        for name in ("S1","C2"):
            if row is None:
                views[name].append(unit)
            else:
                text = row["indexed_text"]
                if name=="C2" and row["prefix_text"]: text=row["prefix_text"]+"\n"+text
                views[name].append(dict(unit,text=text,representation_id=representation_id(unit,text),
                    original_unit_text=unit["text"],representation_profile="5h-scoped-v1"))
    return views


def decorate_hit(hit, unit_map, approved, arm, sources):
    if arm not in ARMS: raise ValueError("unknown arm")
    uid=hit["unit_id"]
    if arm not in {"S1","C2"} or uid not in approved: return copy.deepcopy(hit)
    unit,row=unit_map[uid],approved[uid]
    if hit["file_id"]!=unit["file_id"] or hit["indexed_text"]!=unit["text"]:
        raise ValueError("aggregate winner differs from original unit")
    source=sources[unit["file_id"]]
    segments=[dict(text=s["text"],span=copy.deepcopy(s["span"])) for s in row["segments"]]
    spans=all_spans(source,unit["text"])
    body="【命中原话】\n"+unit["text"]+"\n\n"+SCOPE_BODY_HEADER+"\n"+GAP.join(s["text"] for s in segments)
    prefix=row["prefix_text"] if arm=="C2" else ""
    indexed=row["indexed_text"] if not prefix else prefix+"\n"+row["indexed_text"]
    result=copy.deepcopy(hit)
    result.update(text=PREFIX_HEADER+"\n"+prefix+"\n\n"+body if prefix else body,
        source_text="".join(s["text"] for s in segments),source_segments=segments,
        source_spans=[copy.deepcopy(s["span"]) for s in segments],indexed_text=indexed,
        indexed_source_text="".join(s["text"] for s in segments),indexed_source_spans=[copy.deepcopy(s["span"]) for s in segments],
        original_unit_text=unit["text"],original_unit_spans=spans,base_context_text=hit["text"],
        representation_id=representation_id(unit,indexed),scope_profile="5h-scoped-v1",
        scope_review_status="approved_model_review",scope_source_sha256=row["source_sha256"],
        scope_indexed_text_sha256=sha_text(row["indexed_text"]),scope_status=row["scope_status"],
        scope_reason=row["scope_reason"],scope_segments=copy.deepcopy(row["segments"]),
        occurrence_ambiguity=bool(row.get("occurrence_ambiguity") or len(spans)>1),matched_occurrences=spans,
        context_ambiguous=bool(row.get("occurrence_ambiguity") or len(spans)>1),prefix=prefix)
    if prefix:
        result.update(prefix_claims=copy.deepcopy(row["prefix_claims"]),prefix_source_unit_id=uid,
            prefix_profile="5h-extractive-v1",prefix_review_status="approved_model_review",
            prefix_source_sha256=row["source_sha256"],prefix_sha256=sha_text(prefix))
    return result


def score_binding(query, unit, manifest_sha, runtime, inputs):
    return dict(query_id=query["query_id"],query_text_sha256=sha_text(query["text"]),unit_id=unit["unit_id"],
        file_id=unit["file_id"],source_sha256=unit["source_sha256"],indexed_text_sha256=sha_text(unit["text"]),
        representation_id=representation_id(unit,unit["text"]),
        manifest_sha256=manifest_sha,runtime=runtime,experiment_inputs=inputs)


def validate_score_binding(actual, expected):
    if canonical(actual)!=canonical(expected): raise ValueError("stale score binding; query/text/source/runtime/input differ")


def audit_inputs(tokenizer,texts,ids,max_length,handle,*,stage,pairs=None,query_id=None,bindings=None):
    if len(texts)!=len(ids) or (pairs is not None and len(pairs)!=len(texts)):
        raise ValueError("token audit input count differs")
    encoded=tokenizer(texts,pairs,truncation=False,padding=False) if pairs is not None else tokenizer(texts,truncation=False,padding=False)
    lengths=[len(row) for row in encoded["input_ids"]]
    if len(lengths)!=len(texts): raise ValueError("token audit length population differs")
    for i,(uid,text,length) in enumerate(zip(ids,texts,lengths)):
        handle.write(canonical(dict(stage="strict_preflight_"+stage,id=uid,query_id=query_id,input_tokens=length,
            max_length=max_length,input_text_sha256=sha_text(text),paired_text_sha256=sha_text(pairs[i]) if pairs is not None else None,
            rejected=length>max_length,truncation_allowed=False,binding=bindings[i] if bindings else None)).decode("utf-8")+"\n")
    handle.flush()
    if any(n>max_length for n in lengths): raise ValueError("token limit exceeded; refusing silent truncation: "+str(query_id or stage))
    return dict(inputs=len(texts),max_input_tokens=max(lengths,default=0),rejected=0,max_length=max_length)


def score_candidates(models,query,candidates,unit_map,arm,*,manifest_sha,runtime,inputs,pool,pool_handle):
    ids=[r["unit_id"] for r in candidates]
    if len(ids)!=len(set(ids)) or not set(ids).issubset(unit_map): raise ValueError("rerank candidate IDs invalid")
    bound={uid:score_binding(query,unit_map[uid],manifest_sha,runtime,inputs) for uid in ids}
    keys={uid:hashlib.sha256(canonical(bound[uid])).hexdigest() for uid in ids}
    missing=[r for r in candidates if keys[r["unit_id"]] not in pool]
    for uid in ids:
        if keys[uid] in pool: validate_score_binding(pool[keys[uid]]["binding"],bound[uid])
    started=time.perf_counter()
    if missing:
        if hasattr(models,"rerank_tokenizer"):
            audit_inputs(models.rerank_tokenizer,[query["text"]]*len(missing),[r["unit_id"] for r in missing],
                models.args.max_length,models.token_handle,stage="rerank",pairs=[unit_map[r["unit_id"]]["text"] for r in missing],
                query_id=query["query_id"],bindings=[bound[r["unit_id"]] for r in missing])
        computed=models.rerank(query["text"],missing,unit_map,"5h_"+arm,query["query_id"])
        if len(computed)!=len(missing) or {r["unit_id"] for r in computed}!={r["unit_id"] for r in missing}:
            raise ValueError("real reranker IDs incomplete/duplicate")
        for row in computed:
            score=row["score"]
            if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score):
                raise ValueError("nonfinite real reranker score")
            uid=row["unit_id"]
            pool[keys[uid]]=dict(score=float(score),binding=bound[uid],first_arm=arm)
    seconds=time.perf_counter()-started
    missing_ids={r["unit_id"] for r in missing}
    scores={}
    for uid in ids:
        entry=pool[keys[uid]];scores[uid]=entry["score"]
        pool_handle.write(canonical(dict(query_id=query["query_id"],arm=arm,unit_id=uid,score=entry["score"],
            pool_key=keys[uid],binding=bound[uid],provenance=dict(kind="actual_local_gpu_rerank" if uid in missing_ids else "same_run_exact_model_input_shared",
                first_arm=entry["first_arm"],old_rerank_scores_reused=False))).decode("utf-8")+"\n")
    pool_handle.flush()
    return scores,dict(newly_scored_units=len(missing),reused_units=len(ids)-len(missing),rerank_seconds=seconds)


def mechanism_route(cards,similarities,unit_map,*,card_top_k=CARD_TOP_K):
    if card_top_k!=CARD_TOP_K or len(cards)>5 or len(similarities)!=len(cards):
        raise ValueError("mechanism route requires frozen card_top_k=2 and <=5 cards")
    if any(isinstance(v,bool) or not isinstance(float(v),float) or not math.isfinite(float(v)) for v in similarities):
        raise ValueError("nonfinite card similarity")
    order=sorted(range(len(cards)),key=lambda i:(-float(similarities[i]),cards[i]["card_id"]))[:card_top_k]
    selected,rows,seen=[],[],set()
    for i in order:
        card=cards[i]
        selected.append(dict(card_id=card["card_id"],score=float(similarities[i]),rank=len(selected)+1))
        for support in card["supports"]:
            uid=support["unit_id"]
            if uid not in unit_map: raise ValueError("mechanism route illegal support unit ID")
            if uid in seen: continue
            seen.add(uid)
            rows.append(dict(unit_id=uid,score=float(similarities[i]),rank=len(rows)+1,support_card_id=card["card_id"]))
    return rows,selected


def candidates_for_arm(routes,arm):
    if arm not in ARMS or len(routes)!=(3 if arm=="M3" else 2): raise ValueError("wrong arm/routes")
    return frozen_e04().weighted_rrf([r[:100] for r in routes],ARMS[arm]["weights"],k=60,top_k=300 if arm=="M3" else 200)[:100]


def build_record(query,arm,routes,scores,unit_map,adapter,*,timing,provenance):
    candidates=candidates_for_arm(routes,arm)
    hits=[]
    for row in candidates:
        uid=row["unit_id"];score=scores.get(uid)
        if uid not in unit_map or isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score):
            raise ValueError("missing/nonfinite rerank score or unknown original unit")
        hits.append(dict(unit_id=uid,score=float(score)))
    e04=frozen_e04()
    reranked=e04.ranked(sorted(hits,key=lambda r:(-r["score"],r["unit_id"])))
    cases,files=adapter.aggregate(reranked,unit_map)
    bounded=[r[:100] for r in routes]
    union=e04.weighted_rrf(bounded,ARMS[arm]["weights"],k=60,top_k=300 if arm=="M3" else 200)
    stages=dict(bm25=bounded[0],dense=bounded[1],rrf_union=union,rrf_top100=union[:100],rerank_candidates=candidates,rerank=reranked)
    if arm=="M3": stages["mechanism"]=bounded[2]
    return dict(query_id=query["query_id"],text=query["text"],group=query.get("group"),query_role=query.get("query_role"),
        replay_origin=query.get("replay_origin"),corpus="structured",arm=arm,files=files,cases=cases,stages=stages,
        configuration=dict(rrf_k=60,route_top_k=100,card_top_k=CARD_TOP_K if arm=="M3" else None,**ARMS[arm]),
        timing=timing,provenance=provenance)


def delivery_file_hashes(delivery):
    rows=delivery["output_files"]+delivery["work_code_notes_and_logs"]
    hashes={r["path"]:r["sha256"] for r in rows}
    if len(hashes)!=len(rows): raise ValueError("duplicate old delivery paths")
    return hashes


def load_inputs(args, e04):
    # All old inputs are independently frozen in execution_freeze. Historical
    # provenance is verified by the original preparation helper, used read-only.
    backend,adapter,old_log,manifest,units,unit_map,_,source_audit=e04.prepare_inputs([],"dev")
    if len(units)!=65475 or len({u["file_id"] for u in units})!=9639: raise ValueError("must retain full 9639/65475 population")
    replay={}
    check_sha(E04_OUT/"delivery_manifest.json",E04_DELIVERY_SHA)
    delivery=read_json(E04_OUT/"delivery_manifest.json")
    delivered=delivery_file_hashes(delivery)
    for phase in ("dev","confirmation"):
        path=E04_OUT/(phase+"_queries.jsonl")
        check_sha(path,delivered[path.relative_to(ROOT).as_posix()])
        for query in read_jsonl(path):
            query=dict(query);query.setdefault("query_role","boundary" if query["group"]=="boundary_condition_change" else "risk")
            if query["query_id"] in replay: raise ValueError("duplicate frozen replay query")
            replay[query["query_id"]]=query
    queries=read_jsonl(args.queries)
    query_split=validate_queries(queries,replay)
    cohort=read_json(E02_OUT/"cohort.json")
    if len(cohort["rows"])!=24 or len({r["file_id"] for r in cohort["rows"]})!=24: raise ValueError("requires exact 24-source cohort")
    sources,selected={},set()
    for name in ("prefix_inputs_p1.jsonl","prefix_inputs_p2.jsonl"):
        for row in read_jsonl(E02_OUT/name):
            uid,fid=row["unit"]["unit_id"],row["file_id"]
            if uid in selected or fid in sources or canonical(row["unit"])!=canonical(unit_map.get(uid)) or sha_text(row["full_source_text"])!=row["source_sha256"]:
                raise ValueError("source author input differs from frozen full population")
            selected.add(uid);sources[fid]=row["full_source_text"]
    if selected!={r["unit_id"] for r in cohort["rows"]}: raise ValueError("source author population differs from cohort")
    approved=validate_scope_units(read_jsonl(args.scope_units),read_jsonl(args.scope_reviews),cohort,unit_map,sources,sha_file(args.scope_units))
    cards=validate_mechanism_cards(read_jsonl(args.mechanism_cards),read_jsonl(args.mechanism_reviews),unit_map,sources,sha_file(args.mechanism_cards))
    return queries,query_split,backend,adapter,old_log,manifest,units,unit_map,source_audit,sources,approved,cards


def build_indices(model_args, views):
    sys.path.insert(0,str(model_args.project_src.resolve()))
    from retrieval.sparse import RetrievalDocument,SparseRetrievalIndex
    indices,timing={},{}
    for name,units in views.items():
        emit("bm25_build_start",view=name,units=len(units))
        started=time.perf_counter()
        indices[name]=SparseRetrievalIndex([RetrievalDocument(unit_id=u["unit_id"],case_ids=(u["case_id"],),text=u["text"],source="structured",weight=1.0) for u in units],k1=1.5,b=0.75)
        timing[name]=time.perf_counter()-started
        emit("bm25_build_complete",view=name,seconds=timing[name])
    return indices,timing


def encode_views(models,backend,e04,old_log,manifest,units,views,queries,cards,log):
    started=time.perf_counter()
    seed=e04.seed_document_cache(old_log,manifest,units,models,backend)
    log["document_cache_seed"]=seed
    metadata=read_json(models.args.cache/(seed["key"]+".json"))
    if any(r.get("truncated") for r in metadata["token_audit"]): raise ValueError("frozen document vectors truncated")
    base=models.encode(units,"document","structured")
    if not models.log["cache_events"][-1].get("hit") or models.log["cache_events"][-1].get("key")!=seed["key"]:
        raise ValueError("base vectors must use verified read-only source cache copy")
    query_texts=[backend.QUERY_INSTRUCTION+q["text"] for q in queries]
    log["query_token_preflight"]=audit_inputs(models.embed_tokenizer,query_texts,[q["query_id"] for q in queries],models.args.max_length,models.token_handle,stage="query_embedding")
    query_vectors=models.encode(queries,"query","5h_shared_42_queries")
    if models.log["cache_events"][-1].get("hit"): raise ValueError("42 queries require fresh actual encoding exactly once")
    changed,position={}, {u["unit_id"]:i for i,u in enumerate(units)}
    for name in ("S1","C2"):
        for old,new in zip(units,views[name]):
            if old["unit_id"]!=new["unit_id"]: raise ValueError("view source order differs")
            if old["text"]!=new["text"]: changed[new["representation_id"]]=new
    encoded_rows=[dict(u,unit_id=rid,parent_unit_id=u["unit_id"]) for rid,u in changed.items()]
    if encoded_rows:
        log["overlay_token_preflight"]=audit_inputs(models.embed_tokenizer,[u["text"] for u in encoded_rows],[u["unit_id"] for u in encoded_rows],models.args.max_length,models.token_handle,stage="changed_document_embedding")
        encoded=models.encode(encoded_rows,"document","5h_unique_modified_views")
        if models.log["cache_events"][-1].get("hit"): raise ValueError("changed representation vectors require fresh encoding")
        if encoded.shape!=(len(encoded_rows),base.shape[1]) or encoded.dtype!=base.dtype or not models.np.isfinite(encoded).all():
            raise ValueError("changed document vector shape/dtype/values differ")
    else: encoded=models.np.empty((0,base.shape[1]),dtype="float32")
    vector_map={u["unit_id"]:encoded[i] for i,u in enumerate(encoded_rows)}
    vectors={"B0":base}
    dose={}
    for name in ("S1","C2"):
        overlay=base.copy();changed_positions=[]
        for unit in views[name]:
            rid=unit.get("representation_id")
            if rid in vector_map:
                row=position[unit["unit_id"]];overlay[row]=vector_map[rid];changed_positions.append(row)
        vectors[name]=overlay
        dose[name]=dict(representation_rows=sum("representation_id" in u for u in views[name]),
            changed_text_rows=len(changed_positions),changed_unit_rows=len(changed_positions),changed_positions=changed_positions,
            ordered_text_sha256=backend.ordered_text_sha(views[name]),array_sha256=hashlib.sha256(overlay.tobytes(order="C")).hexdigest())
    card_rows=[dict(unit_id=c["card_id"]+":5h-card:"+sha_text(c["retrieval_text"]),text=c["retrieval_text"]) for c in cards]
    log["card_token_preflight"]=audit_inputs(models.embed_tokenizer,[c["text"] for c in card_rows],[c["unit_id"] for c in card_rows],models.args.max_length,models.token_handle,stage="mechanism_card_embedding")
    card_vectors=models.encode(card_rows,"document","5h_mechanism_cards")
    if models.log["cache_events"][-1].get("hit"): raise ValueError("mechanism cards require fresh real BGE encoding")
    log["vector_operation"]=dict(actual_query_encoding_rows=len(queries),query_encoding_calls=1,
        unique_modified_document_encoding_rows=len(encoded_rows),mechanism_card_encoding_rows=len(cards),
        unchanged_document_reencoding_rows=0,base_document_encoding_origin="verified_frozen_cache_copy",
        old_query_vectors_used=False,old_reranker_scores_used=False,shape=list(base.shape),dtype=str(base.dtype),
        base_array_sha256=hashlib.sha256(base.tobytes(order="C")).hexdigest(),views=dose,seconds=time.perf_counter()-started)
    return query_vectors,vectors,card_vectors


def dose_record(record,approved,cards):
    return dict(scope_rerank_units=sum(r["unit_id"] in approved for r in record["stages"]["rerank"]),
        scope_top5_unit_ids=[r["unit_id"] for r in record["files"][:5] if r["unit_id"] in approved],
        actual_scoped_top5_unit_ids=[r["unit_id"] for r in record["files"][:5] if r.get("scope_profile")],
        background_top5_unit_ids=[r["unit_id"] for r in record["files"][:5] if r.get("prefix")],
        mechanism_support_top5_unit_ids=[r["unit_id"] for r in record["files"][:5] if r["unit_id"] in {s["unit_id"] for c in cards for s in c["supports"]}])


def run(args):
    assert_new_output(args.output)
    if not args.output.resolve().is_relative_to(OUT.resolve()): raise ValueError("output must remain inside new experiment output directory")
    cache=validate_cache_path(args.cache)
    if cache.exists() and any(cache.iterdir()): raise FileExistsError("new experiment requires empty isolated cache")
    required=[Path(__file__),args.queries,args.scope_units,args.scope_reviews,args.mechanism_cards,args.mechanism_reviews,
              E02_OUT/"cohort.json",E02_OUT/"prefix_inputs_p1.jsonl",E02_OUT/"prefix_inputs_p2.jsonl",E04_CODE]
    inputs=validate_freeze(args.freeze,required)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    started,models=time.perf_counter(),None
    log_path,partial_path,pool_path=[Path(str(args.output)+s) for s in (".run.json",".partial",".score_pool.jsonl")]
    log=dict(status="partial",arms=list(ARMS),query_count=42,completed_queries=0,result_rows=0,input_sha256=inputs,
        searchable_units=65475,source_population=9639,configuration=ARMS,card_top_k=CARD_TOP_K,
        cache=str(cache),actual_local_inference=True,network="local_files_only; no paid API",
        mechanism_limitations="Only 3-5 candidate cards; Top2 can still expose many/all supports and is not a full mechanism graph")
    save_json(log_path,log)
    try:
        e04=frozen_e04()
        queries,split,backend,adapter,old_log,manifest,units,unit_map,source_audit,sources,approved,cards=load_inputs(args,e04)
        views=make_views(units,approved)
        view_maps={name:{u["unit_id"]:u for u in rows} for name,rows in views.items()}
        log.update(query_split=split,source_audit=source_audit,approved_scope_units=len(approved),
            rejected_or_unchanged_scope_units=24-len(approved),approved_mechanism_cards=len(cards),
            approved_scope_unit_ids=list(approved),base_ordered_text_sha256=backend.ordered_text_sha(units),
            manifest_sha256=e04.MANIFEST_SHA,runner_sha256=e04.BACKEND_SHA,adapter_sha256=e04.ADAPTER_SHA)
        model_args=e04.make_model_args(args.output,old_log);model_args.cache=cache
        log["parameters"]={k:str(v) if isinstance(v,Path) else v for k,v in vars(model_args).items()}
        emit("model_load_start",queries=len(queries),approved_scope_units=len(approved),cards=len(cards))
        models=backend.LocalModels(model_args)
        e04.validate_models(models,old_log)
        runtime=e04.runtime_binding(old_log);log["runtime_binding"]=runtime
        query_vectors,doc_vectors,card_vectors=encode_views(models,backend,e04,old_log,manifest,units,views,queries,cards,log)
        indices,index_timing=build_indices(model_args,views)
        log["bm25_index_seconds"]=index_timing
        save_json(log_path,log)
        card_pattern_counts={}
        with partial_path.open("x",encoding="utf-8") as output,pool_path.open("x",encoding="utf-8") as pool_handle:
            for qi,query in enumerate(queries):
                query_started=time.perf_counter();qid=query["query_id"]
                emit("query_start",query_id=qid,index=qi+1,total=len(queries))
                route_map,route_timing={},{}
                for name in views:
                    route_map[name],route_timing[name]=e04.confirmation_routes(models,indices[name],query_vectors[qi],doc_vectors[name],views[name],query)
                    for route in route_map[name]: e04.validate_ranked(route,unit_map,100)
                t=time.perf_counter()
                card_similarities=card_vectors@query_vectors[qi]
                third,selected_cards=mechanism_route(cards,card_similarities,unit_map)
                card_seconds=time.perf_counter()-t
                pattern=",".join(c["card_id"] for c in selected_cards)
                card_pattern_counts[pattern]=card_pattern_counts.get(pattern,0)+1
                # The pool lives for one query and is keyed by complete exact
                # model input/runtime/source SHA, never by unit ID alone.
                score_pool={}
                for arm,config in ARMS.items():
                    view=config["view"]
                    routes=route_map[view]+[third] if arm=="M3" else route_map[view]
                    candidates=candidates_for_arm(routes,arm)
                    if len(candidates)!=100: raise ValueError("every arm requires actual rerank100 candidates")
                    scores,score_stats=score_candidates(models,query,candidates,view_maps[view],arm,
                        manifest_sha=e04.MANIFEST_SHA,runtime=runtime,inputs=inputs,pool=score_pool,pool_handle=pool_handle)
                    timing=dict(**route_timing[view],**score_stats,bm25_index_seconds=index_timing[view],
                        query_embedding_shared=True,same_query_scores_shared=True,mechanism_route_seconds=card_seconds if arm=="M3" else 0.0)
                    provenance=dict(routes_origin="actual_local_full_population_bm25_and_bge",rerank_origin="same_run_real_exact_input_pool",
                        experiment_inputs=inputs,runtime_binding=runtime,manifest_sha256=e04.MANIFEST_SHA,
                        query_text_sha256=sha_text(query["text"]),ordered_view_text_sha256=backend.ordered_text_sha(views[view]),
                        score_pool_path=str(pool_path.resolve()),returned_context="original V2 context" if view=="B0" else "source-reviewed scope; parent unit and quote preserved",
                        old_query_vectors_used=False,old_rerank_scores_used=False,
                        mechanism_cards_are_citation=False,mechanism_card_top_k=CARD_TOP_K if arm=="M3" else None)
                    record=build_record(query,arm,routes,scores,unit_map,adapter,timing=timing,provenance=provenance)
                    for key in ("files","cases"):
                        record[key]=[decorate_hit(h,unit_map,approved,arm,sources) for h in record[key]]
                    if arm=="M3":
                        record["stages"]["mechanism_cards"]=selected_cards
                        record["provenance"].update(mechanism_support_units=len(third),mechanism_support_scope="ordered deduplicated supports from true BGE Top2 cards; original case units reranked/returned")
                    record["dose"]=dose_record(record,approved,cards)
                    record["timing"]["shared_query_elapsed_seconds"]=time.perf_counter()-query_started
                    output.write(canonical(record).decode("utf-8")+"\n")
                    log["result_rows"]+=1
                output.flush()
                log.update(completed_queries=qi+1,elapsed_seconds=time.perf_counter()-started,models=models.log,
                    mechanism_card_selection_patterns=card_pattern_counts)
                save_json(log_path,log)
                emit("query_complete",query_id=qid,arms=list(ARMS),shared_actual_score_inputs=len(score_pool),mechanism_units=len(third),seconds=time.perf_counter()-query_started)
        if log["result_rows"]!=210 or log["completed_queries"]!=42: raise RuntimeError("incomplete 42x5 results")
        for path,digest in inputs.items(): check_sha(path,digest)
        if args.output.exists(): raise FileExistsError("output appeared during run; refusing overwrite")
        partial_path.rename(args.output)
        log.update(status="complete",output_path=str(args.output.resolve()),output_sha256=sha_file(args.output),
            score_pool_sha256=sha_file(pool_path),elapsed_seconds=time.perf_counter()-started)
    except BaseException as exc:
        log.update(status="failure",error=f"{type(exc).__name__}: {exc}",elapsed_seconds=time.perf_counter()-started)
        save_json(Path(str(args.output)+".failure.json"),log)
        emit("run_failure",error=log["error"],result_rows=log["result_rows"])
        raise
    finally:
        if models is not None:
            models.token_handle.close();log["models"]=models.log
            token_path=Path(str(args.output)+".token_audit.jsonl")
            if token_path.exists(): log["token_audit_sha256"]=sha_file(token_path)
        save_json(log_path,log)
    emit("run_complete",rows=log["result_rows"],seconds=log["elapsed_seconds"],output=str(args.output))
    return log


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("queries","scope-units","scope-reviews","mechanism-cards","mechanism-reviews","freeze","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--cache",type=Path,default=HERE/"vector_cache")
    run(parser.parse_args())


if __name__=="__main__": main()
