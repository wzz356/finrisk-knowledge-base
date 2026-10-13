"""Offline E04 blind-pool preparation and source-verified model-review metrics.

This module never assigns semantic judgments or calls a model/API/GPU.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "outputs/FinRisk_知识库V2_20261012/normalized_final/data/documents.jsonl"
LEGACY_PATH = ROOT / "work/finrisk_v2_20261012/eval_v2.py"
_spec = importlib.util.spec_from_file_location("e04_readonly_eval_v2", LEGACY_PATH)
_legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy)
FILE_FIELDS = _legacy.FILE_FIELDS
ARMS = ("A0", "A1", "A2", "A3")
OUTPUT_ROOTS = (ROOT / "outputs/FinRisk_E04小批量实验_20261012",)
OUTPUT_NAMES = ("blind_judgment_pool.jsonl", "judgment_provenance.jsonl", "cached_judgments.jsonl",
                "validated_judgments.jsonl", "remaining_pool.jsonl", "file_context_disagreements.jsonl",
                "reuse_provenance.json", "judgment_pool_manifest.json", "metrics.json", "metrics.md", "per_query_metrics.jsonl")
METRIC_FIELDS = ("useful_at5", "support_coverage_at5", "mean_help_at5",
                 "context_useful_at5", "context_coverage_at5", "mean_context_help_at5",
                 "misleading_at5", "context_misleading_at5")
AUX_FIELDS = ("known_source_hit_at5", "known_source_hit_at10", "known_source_hit_at20")
RUBRIC = {
    "evaluation": "model_review_only",
    "task": "分别判断完整文书和实际返回片段对当前业务输入的风险判断是否有帮助；边界对照也可以有用，不能由相似案例直接断定输入违规。",
    "grades": {"0": "无关或没有判断帮助", "1": "弱关联，关键机制或条件缺失", "2": "有用，支持风险判断或揭示适用边界", "3": "强帮助，机制和适用条件清楚且原话足够"},
    "file_fields": list(FILE_FIELDS),
    "file_enums": {"help_type": ["support", "boundary", "irrelevant"],
                   "mechanism_match": ["same", "partial", "different"],
                   "conditions_match": ["compatible", "partial", "conflict", "unknown"]},
    "context_fields": ["context_id", "help_grade", "evidence_quote", "reason", "misleading_risk"],
    "quote_rule": "评分>=2必须附逐字原话。source_quote必须连续出现在全文；evidence_quote必须同时连续出现在当前片段和完整原文，不能拼接或改写。",
    "cache_rule": "needs_file_judgment=false时无需重评全文，只补contexts列出的片段，不提交或改写已有全文评分。",
    "risk_rule": "misleading_risk为布尔值，标记案例或片段会误导对业务输入的判定；条件未记载不得自动当作符合。",
    "output_rule": "每行含pair_id，需评分的全文字段及contexts数组；仅补片段时可只写pair_id和contexts。limitations为字符串数组，reason须说明帮助或缺口。",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_rows(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")


def save_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def paths(value):
    if value is None:
        return []
    if isinstance(value, (str, Path)):
        return [Path(value)]
    return [Path(item) for item in value]


def check_output_dir(path):
    resolved = Path(path).resolve()
    require(any(resolved != root.resolve() and resolved.is_relative_to(root.resolve()) for root in OUTPUT_ROOTS), "output must be a real phase subdirectory within new E04 outputs")
    return resolved


def check_input_output_isolation(out, input_paths):
    """Reject resolved aliases, links outside the phase, and multiply linked files."""
    inputs = [Path(path).resolve() for path in input_paths]
    for name in OUTPUT_NAMES:
        target = (out / name).resolve()
        require(target.is_relative_to(out), f"output resolves outside phase: {name}")
        for source in inputs:
            require(target != source, f"output aliases explicit input: {name}:{source}")
            if target.exists() and source.exists():
                require(not target.samefile(source), f"output hardlink aliases explicit input: {name}:{source}")
        if target.exists():
            require(target.is_file(), f"output artifact is not a file: {name}")
            require(target.stat().st_nlink <= 1, f"output artifact has hardlinks: {name}")


def verify_prepared_manifest(out, expected_inputs):
    manifest_path = out / "judgment_pool_manifest.json"
    if not manifest_path.exists():
        require(not any((out / name).exists() for name in OUTPUT_NAMES), "output has unknown artifacts without a binding manifest")
        return None
    previous = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(previous.get("input_sha256") == expected_inputs, "existing phase input binding SHA drift; use a new phase directory")
    for path, expected in previous.get("reuse_input_sha256", {}).items():
        require(file_sha(path) == expected, f"reuse input SHA drift: {path}")
    for name, expected in previous["artifact_sha256"].items():
        require(name in OUTPUT_NAMES, "unknown manifest artifact")
        require(file_sha(out / name) == expected, f"prepared artifact SHA drift: {name}")
    return previous


def verify_resume_rows(out):
    candidate = Path(out) / "validated_judgments.jsonl"
    if not candidate.exists():
        return
    digest = file_sha(candidate)
    for name, key in (("metrics.json", "judgments_sha256"), ("reuse_provenance.json", "validated_judgments_sha256")):
        metadata = Path(out) / name
        if metadata.exists():
            previous = json.loads(metadata.read_text(encoding="utf-8"))
            if key in previous:
                require(previous[key] == digest, "validated judgment resume SHA drift")


def unique(rows, key, label):
    mapping = {}
    for row in rows:
        require(isinstance(row, dict) and key in row, f"invalid {label}")
        identity = row[key]
        require(identity not in mapping, f"duplicate {label}: {identity}")
        mapping[identity] = row
    return mapping


def load_queries(path):
    rows = unique(read_rows(path), "query_id", "query")
    require(bool(rows), "empty queries")
    for qid, row in rows.items():
        require(isinstance(qid, str) and qid, "invalid query id")
        require(isinstance(row.get("text"), str) and row["text"].strip(), f"empty query text: {qid}")
        require(isinstance(row.get("known_positive_file_ids", []), list), f"invalid known sources: {qid}")
        if "query_sha256" in row:
            require(row["query_sha256"] == text_sha(row["text"]), f"query SHA drift: {qid}")
    return rows


def load_sources(path=SOURCES):
    sources = {}
    for row in read_rows(path):
        fid = row["official_file_id"]
        require(fid not in sources, f"duplicate source: {fid}")
        body = row["full_text"]
        require(isinstance(body, str) and body.strip(), f"invalid full source: {fid}")
        digest = text_sha(body)
        for key in ("text_sha256", "source_sha256"):
            require(row.get(key) == digest, f"source SHA mismatch: {fid}:{key}")
        sources[fid] = {"full_text": body, "text_sha256": digest}
    require(bool(sources), "empty sources")
    return sources


def validate_results(queries, results):
    groups, identities = defaultdict(set), set()
    require(bool(results), "empty results")
    for r in results:
        qid, arm = r["query_id"], r["arm"]
        require(arm in ARMS, f"unknown E04 arm: {arm}")
        require(qid in queries, f"unknown query: {qid}")
        require(r.get("text") == queries[qid]["text"], f"query text drift: {qid}")
        if "query_sha256" in r:
            require(r["query_sha256"] == text_sha(r["text"]), f"result query SHA drift: {qid}")
        identity = (arm, qid)
        require(identity not in identities, f"duplicate arm/query result: {identity}")
        identities.add(identity)
        groups[arm].add(qid)
        require(isinstance(r.get("files"), list), f"invalid files: {identity}")
        require(len({h["file_id"] for h in r["files"]}) == len(r["files"]), f"duplicate returned file: {identity}")
        for rank, h in enumerate(r["files"], 1):
            require(type(h.get("rank")) is int and h["rank"] == rank, f"noncontiguous rank: {identity}")
            require(isinstance(h.get("unit_id"), str) and h["unit_id"], f"missing unit: {identity}")
    for arm, qids in groups.items():
        require(qids == set(queries), f"arm must cover all queries: {arm}")


def checked_context(hit, full_source):
    c = _legacy.validate_context(hit, full_source)
    if "context_spans" in hit:
        require(hit["context_spans"] == hit["source_spans"], "context/source span mismatch")
    c["context_spans"] = copy.deepcopy(c["source_spans"])
    c["text_sha256"] = text_sha(c["text"])
    return c


def validate_pool(rows):
    pool = _legacy.validate_pool(rows)
    for pid, p in pool.items():
        require(isinstance(p.get("query_text"), str) and p["query_text"].strip(), f"missing query binding: {pid}")
        if "query_sha256" in p:
            require(p["query_sha256"] == text_sha(p["query_text"]), f"pool query SHA drift: {pid}")
        for c in p["contexts"]:
            checked_context(c, p["full_source_text"])
            if "text_sha256" in c:
                require(c["text_sha256"] == text_sha(c["text"]), f"context SHA drift: {pid}")
    return pool


def build_pool(queries, results, sources):
    """Return a blinded pair map plus unblinded per-slot provenance (Top5 only)."""
    validate_results(queries, results)
    pool, provenance = {}, []
    for r in sorted(results, key=lambda row: (row["arm"], row["query_id"])):
        qid, q = r["query_id"], queries[r["query_id"]]
        for rank, h in enumerate(r["files"][:5], 1):
            fid = h["file_id"]
            require(fid in sources, f"unknown full source: {fid}")
            source = sources[fid]
            body = source["full_text"]
            digest = text_sha(body)
            require(source["text_sha256"] == digest, f"source SHA mismatch: {fid}")
            for key in ("source_sha256", "text_sha256"):
                if key in h:
                    require(h[key] == digest, f"hit source SHA mismatch: {fid}")
            pid = _legacy.pair_id(qid, fid)
            if pid not in pool:
                task = {key: copy.deepcopy(q[key]) for key in ("mechanism_description", "relevant_conditions", "distinguishing_conditions", "expected_help") if key in q}
                pool[pid] = {"pair_id": pid, "query_id": qid, "query_text": q["text"],
                             "query_sha256": text_sha(q["text"]), "file_id": fid,
                             "full_source_text": body, "source_sha256": digest,
                             "query_task": task, "scoring_instructions": copy.deepcopy(RUBRIC),
                             "contexts": {}, "file_judgment_from_cache": False,
                             "needs_file_judgment": True}
            p = pool[pid]
            require((p["query_id"], p["file_id"]) == (qid, fid), "pair hash collision")
            c = checked_context(h, body)
            cid = c["context_id"]
            if cid in p["contexts"]:
                previous = p["contexts"][cid]
                require(previous["text"] == c["text"] and previous["source_text"] == c["source_text"] and previous["prefix"] == c["prefix"], "context collision")
                # Different valid occurrences remain available in provenance.
            else:
                p["contexts"][cid] = c
            provenance.append({"pair_id": pid, "context_id": cid, "query_id": qid,
                               "file_id": fid, "arm": r["arm"], "rank": rank,
                               "unit_id": h["unit_id"], "source_sha256": digest,
                               "text": h["text"], "source_text": h["source_text"],
                               "source_spans": copy.deepcopy(h["source_spans"]),
                               "source_segments": copy.deepcopy(h.get("source_segments", [])),
                               "returned_hit": copy.deepcopy(h)})
    for p in pool.values():
        p["contexts"] = sorted(p["contexts"].values(), key=lambda c: c["context_id"])
    return validate_pool(sorted(pool.values(), key=lambda p: p["pair_id"])), provenance


def file_fields(row):
    return {key: copy.deepcopy(row.get(key, "")) for key in FILE_FIELDS}


def judgment_binding(p):
    return {key: p[key] for key in ("pair_id", "query_id", "query_text", "file_id", "source_sha256")} | {"query_sha256": text_sha(p["query_text"])}


def has_file_judgment(row):
    return row is not None and "help_grade" in row


def validate_partial_judgment(row, p):
    require(row.get("pair_id") == p["pair_id"], "judgment pair mismatch")
    for key, value in judgment_binding(p).items():
        if key in row:
            require(row[key] == value, f"judgment binding drift: {p['pair_id']}:{key}")
    if any(key in row for key in FILE_FIELDS):
        _legacy.validate_file_judgment(row, p)
    actual = unique(row.get("contexts", []), "context_id", "context judgment")
    expected = {c["context_id"]: c for c in p["contexts"]}
    require(set(actual) <= set(expected), f"unknown context judgment: {p['pair_id']}")
    for cid, j in actual.items():
        _legacy.validate_context_judgment(j, expected[cid], p["full_source_text"])


def reuse_judgments(pool, old_pool_rows, old_judgment_rows, origin=""):
    """Reuse only exact qid/text/source SHA/body and independently exact contexts."""
    old = validate_pool(old_pool_rows)
    old_j = {}
    for row in old_judgment_rows:
        pid = row["pair_id"]
        require(pid in old, f"cached judgment outside old pool: {pid}")
        validate_partial_judgment(row, old[pid])
        if pid not in old_j:
            old_j[pid] = {**judgment_binding(old[pid]), "contexts": []}
        target = old_j[pid]
        if has_file_judgment(row):
            if has_file_judgment(target):
                require(file_fields(target) == file_fields(row), f"cached file overwrite: {pid}")
            target.update(file_fields(row))
        ctx = {c["context_id"]: c for c in target["contexts"]}
        for c in row.get("contexts", []):
            require(c["context_id"] not in ctx or ctx[c["context_id"]] == c, f"cached context overwrite: {pid}")
            ctx[c["context_id"]] = copy.deepcopy(c)
        target["contexts"] = sorted(ctx.values(), key=lambda c: c["context_id"])
    reusable, accepted, rejected = {}, [], []
    for pid, p in pool.items():
        previous, j = old.get(pid), old_j.get(pid)
        if previous is None or j is None:
            continue
        if any(previous[key] != p[key] for key in ("query_id", "query_text", "file_id", "source_sha256", "full_source_text")):
            rejected.append({"pair_id": pid, "origin": origin, "reason": "query_or_source_binding_changed"})
            continue
        row = {**judgment_binding(p), "contexts": []}
        if has_file_judgment(j):
            row.update(file_fields(j))
        old_contexts = {c["context_id"]: c for c in previous["contexts"]}
        old_context_j = {c["context_id"]: c for c in j["contexts"]}
        for c in p["contexts"]:
            cid = c["context_id"]
            if cid in old_contexts and cid in old_context_j and old_contexts[cid]["text"] == c["text"]:
                _legacy.validate_context_judgment(old_context_j[cid], c, p["full_source_text"])
                row["contexts"].append(copy.deepcopy(old_context_j[cid]))
        if has_file_judgment(row) or row["contexts"]:
            reusable[pid] = row
            accepted.append({"pair_id": pid, "origin": origin, "file_reused": has_file_judgment(row),
                             "query_id": p["query_id"], "query_sha256": text_sha(p["query_text"]),
                             "source_sha256": p["source_sha256"], "context_ids": [c["context_id"] for c in row["contexts"]],
                             "context_sha256": {c["context_id"]: text_sha(c["text"]) for c in p["contexts"] if c["context_id"] in {j['context_id'] for j in row['contexts']}}})
    return reusable, {"origin": origin, "reused_files": sum(has_file_judgment(j) for j in reusable.values()),
                      "reused_contexts": sum(len(j["contexts"]) for j in reusable.values()),
                      "accepted": accepted, "rejected": rejected}


def merge_judgments(pool, cached, submitted_rows):
    """Merge partial submissions; retain file judgments and expose all gaps."""
    merged = {pid: copy.deepcopy(j) for pid, j in cached.items()}
    for pid, row in merged.items():
        require(pid in pool, f"cached judgment outside current pool: {pid}")
        validate_partial_judgment(row, pool[pid])
    for new in submitted_rows:
        pid = new.get("pair_id")
        require(pid in pool, f"submitted judgment outside current pool: {pid}")
        p = pool[pid]
        validate_partial_judgment(new, p)
        if pid not in merged:
            merged[pid] = {**judgment_binding(p), "contexts": []}
        row = merged[pid]
        if has_file_judgment(new):
            if has_file_judgment(row):
                require(file_fields(new) == file_fields(row), f"cached file judgment may not be overwritten: {pid}")
            row.update(file_fields(new))
        actual = {c["context_id"]: c for c in row.get("contexts", [])}
        for c in new.get("contexts", []):
            cid = c["context_id"]
            require(cid not in actual or actual[cid] == c, f"cached context may not be overwritten: {pid}:{cid}")
            actual[cid] = copy.deepcopy(c)
        row["contexts"] = sorted(actual.values(), key=lambda c: c["context_id"])
    remaining, disagreements = [], []
    for pid, p in sorted(pool.items()):
        j = merged.get(pid)
        file_known = has_file_judgment(j)
        actual = {c["context_id"]: c for c in j.get("contexts", [])} if j else {}
        missing = [copy.deepcopy(c) for c in p["contexts"] if c["context_id"] not in actual]
        if not file_known or missing:
            remaining.append({**copy.deepcopy(p), "contexts": missing,
                              "needs_file_judgment": not file_known,
                              "file_judgment_from_cache": file_known})
        if j:
            j.update(judgment_binding(p))
            j["file_judgment_from_cache"] = has_file_judgment(cached.get(pid))
            validate_partial_judgment(j, p)
        if file_known and j["help_grade"] < 2:
            high = [copy.deepcopy(c) for c in actual.values() if c["help_grade"] >= 2]
            if high:
                disagreements.append({**judgment_binding(p), "file_help_grade": j["help_grade"],
                                      "file_reason": j["reason"], "file_source_quote": j.get("source_quote", ""),
                                      "high_context_judgments": high, "resolution": "kept_original_file_grade; review_disagreement_separately"})
    return merged, remaining, disagreements


def aggregate_metrics(rows, arm=None):
    n = len(rows)
    summary = {"queries": n, "top5_denominator": n * 5,
               "actual_top5_slots": sum(r["returned_files"] for r in rows),
               "absent_top5_slots": sum(r["absent_top5_slots"] for r in rows)}
    if arm is not None:
        summary["arm"] = arm
    for metric in METRIC_FIELDS + AUX_FIELDS:
        values = [r[metric] for r in rows if r.get(metric) is not None]
        summary[metric] = sum(values) / len(values) if values else None
        summary[metric + "_n"] = len(values)
    for kind in ("support", "boundary", "irrelevant"):
        summary["useful_" + kind + "_slots"] = sum(r["useful_" + kind + "_slots"] for r in rows)
    return summary


def compute_metrics(queries, results, pool, judgments):
    """Require every returned Top5 file/context judgment; missing hits use 5 slots."""
    validate_results(queries, results)
    require(set(judgments) == set(pool), "incomplete judgment coverage: missing file judgments")
    for pid, p in pool.items():
        require(has_file_judgment(judgments[pid]), f"incomplete file judgment: {pid}")
        validate_partial_judgment(judgments[pid], p)
        _legacy.validate_judgment(judgments[pid], p)
    per_query = []
    for r in sorted(results, key=lambda row: (row["arm"], row["query_id"])):
        qid, q = r["query_id"], queries[r["query_id"]]
        details = []
        for rank, h in enumerate(r["files"][:5], 1):
            pid = _legacy.pair_id(qid, h["file_id"])
            require(pid in pool, "result outside pool")
            p, j = pool[pid], judgments[pid]
            require(p["query_text"] == q["text"], "pool/query binding drift")
            c = checked_context(h, p["full_source_text"])
            cj = {v["context_id"]: v for v in j["contexts"]}[c["context_id"]]
            details.append({"rank": rank, "file_id": h["file_id"], "unit_id": h["unit_id"],
                            "pair_id": pid, "context_id": c["context_id"],
                            "help_grade": j["help_grade"], "help_type": j["help_type"],
                            "context_help_grade": cj["help_grade"], "misleading_risk": j["misleading_risk"],
                            "context_misleading_risk": cj["misleading_risk"], "source_quote": j.get("source_quote", ""),
                            "evidence_quote": cj.get("evidence_quote", ""), "reason": j["reason"],
                            "context_reason": cj["reason"], "limitations": copy.deepcopy(j["limitations"]),
                            "source_sha256": p["source_sha256"], "returned_hit": copy.deepcopy(h),
                            "source_spans": copy.deepcopy(h["source_spans"]), "source_segments": copy.deepcopy(h.get("source_segments", []))})
        n = len(details)
        row = {"arm": r["arm"], "query_id": qid, "query_text": q["text"], "group": q.get("group", "unspecified"),
               "returned_files": n, "absent_top5_slots": 5 - n, "top5_denominator": 5,
               "useful_at5": sum(d["help_grade"] >= 2 for d in details) / 5,
               "support_coverage_at5": int(any(d["help_grade"] >= 2 for d in details)),
               "mean_help_at5": sum(d["help_grade"] for d in details) / 5,
               "context_useful_at5": sum(d["context_help_grade"] >= 2 for d in details) / 5,
               "context_coverage_at5": int(any(d["context_help_grade"] >= 2 for d in details)),
               "mean_context_help_at5": sum(d["context_help_grade"] for d in details) / 5,
               "misleading_at5": sum(d["misleading_risk"] for d in details) / 5,
               "context_misleading_at5": sum(d["context_misleading_risk"] for d in details) / 5,
               "top5": details, "timing": copy.deepcopy(r.get("timing", {}))}
        for kind in ("support", "boundary", "irrelevant"):
            row["useful_" + kind + "_slots"] = sum(d["help_grade"] >= 2 and d["help_type"] == kind for d in details)
        positives = set(q.get("known_positive_file_ids", []))
        for k in (5, 10, 20):
            row[f"known_source_hit_at{k}"] = int(bool(positives.intersection(h["file_id"] for h in r["files"][:k]))) if positives else None
        row["known_source_count"] = len(positives)
        per_query.append(row)
    summaries = []
    for arm in sorted({r["arm"] for r in results}):
        rows = [r for r in per_query if r["arm"] == arm]
        a = aggregate_metrics(rows, arm)
        a["by_group"] = {group: aggregate_metrics([r for r in rows if r["group"] == group]) for group in sorted({r["group"] for r in rows})}
        summaries.append(a)
    return {"status": "complete", "evaluation": "model_review_only", "human_judgments": 0,
            "human_approved": False, "queries": len(queries), "unique_query_file_pairs": len(pool),
            "context_variants": sum(len(p["contexts"]) for p in pool.values()),
            "metrics": summaries, "metric_scope": "Top5 helpfulness; known-source hits are auxiliary only",
            "limitations": ["模型意见，未经人工验收", "开发集用于配置选择，确认集为独立来源的小样本模型构造输入", "已知来源不是完整相关集合，不声称真实召回率或全局金标", "有用阈值为>=2，固定每题5位置；缺席无支持，缺评分不计0"]}, per_query


def input_hashes(queries_path, result_paths, sources_path):
    return {str(Path(path).resolve()): file_sha(path) for path in [queries_path, *result_paths, sources_path, Path(__file__), LEGACY_PATH]}


def merge_cache(pool, target, rows):
    merged, _, _ = merge_judgments(pool, target, rows)
    return merged


def prepare(queries_path, results_paths, output_dir, reuse_pool=None, reuse_judgment_paths=None, *, sources_path=SOURCES):
    out = check_output_dir(output_dir)
    result_paths = paths(results_paths)
    old_pool_paths, old_judgment_paths = paths(reuse_pool), paths(reuse_judgment_paths)
    require(bool(old_pool_paths) == bool(old_judgment_paths), "reuse requires both pool and judgments")
    require(not old_pool_paths or len(old_pool_paths) in (1, len(old_judgment_paths)), "reuse inputs require paired pools/judgments or one common pool")
    check_input_output_isolation(out, [queries_path, *result_paths, sources_path, *old_pool_paths, *old_judgment_paths])
    bound_inputs = input_hashes(queries_path, result_paths, sources_path)
    previous_manifest = verify_prepared_manifest(out, bound_inputs)
    verify_resume_rows(out)
    reuse_inputs = {str(path.resolve()): file_sha(path) for path in [*old_pool_paths, *old_judgment_paths]}
    if previous_manifest:
        if reuse_inputs:
            require(reuse_inputs == previous_manifest.get("reuse_input_sha256", {}), "existing phase reuse input binding changed")
        else:
            reuse_inputs = previous_manifest.get("reuse_input_sha256", {})
    queries = load_queries(queries_path)
    results = [r for path in result_paths for r in read_rows(path)]
    pool, provenance = build_pool(queries, results, load_sources(sources_path))
    out.mkdir(parents=True, exist_ok=True)
    cached, reuse_log = {}, []
    if len(old_pool_paths) == 1:
        rows, log = reuse_judgments(pool, read_rows(old_pool_paths[0]), [r for path in old_judgment_paths for r in read_rows(path)], origin=str(old_pool_paths[0].resolve()))
        cached = merge_cache(pool, cached, list(rows.values()))
        reuse_log.append(log)
    else:
        for pool_path, judgment_path in zip(old_pool_paths, old_judgment_paths):
            rows, log = reuse_judgments(pool, read_rows(pool_path), read_rows(judgment_path), origin=str(pool_path.resolve()))
            cached = merge_cache(pool, cached, list(rows.values()))
            reuse_log.append(log)
    # Resume from this output's own source-bound rows, without relying on input-file equality.
    existing_pool = out / "blind_judgment_pool.jsonl"
    if existing_pool.exists():
        for name in ("cached_judgments.jsonl", "validated_judgments.jsonl"):
            candidate = out / name
            if candidate.exists():
                rows, log = reuse_judgments(pool, read_rows(existing_pool), read_rows(candidate), origin=str(candidate.resolve()))
                log["origin_sha256"] = file_sha(candidate)
                log["bound_pool_sha256"] = file_sha(existing_pool)
                cached = merge_cache(pool, cached, list(rows.values()))
                reuse_log.append(log)
    cached, remaining, disagreements = merge_judgments(pool, cached, [])
    for pid, p in pool.items():
        p["file_judgment_from_cache"] = has_file_judgment(cached.get(pid))
        p["needs_file_judgment"] = not p["file_judgment_from_cache"]
    write_rows(out / "blind_judgment_pool.jsonl", sorted(pool.values(), key=lambda p: p["pair_id"]))
    write_rows(out / "judgment_provenance.jsonl", provenance)
    write_rows(out / "cached_judgments.jsonl", sorted(cached.values(), key=lambda j: j["pair_id"]))
    write_rows(out / "validated_judgments.jsonl", sorted(cached.values(), key=lambda j: j["pair_id"]))
    write_rows(out / "remaining_pool.jsonl", remaining)
    write_rows(out / "file_context_disagreements.jsonl", disagreements)
    reuse = {"reuse_rule": "exact query id/text, source SHA/full text and independent exact context text", "sources": reuse_log,
             "input_sha256": reuse_inputs,
             "reused_files": sum(has_file_judgment(j) for j in cached.values()), "reused_contexts": sum(len(j["contexts"]) for j in cached.values())}
    reuse["validated_judgments_sha256"] = file_sha(out / "validated_judgments.jsonl")
    save_json(out / "reuse_provenance.json", reuse)
    manifest = {"status": "awaiting_judgments" if remaining else "ready_for_metrics", "evaluation": "model_review_only",
                "human_judgments": 0, "human_approved": False, "queries": len(queries), "arms": sorted({r['arm'] for r in results}),
                "unique_query_file_pairs": len(pool), "context_variants": sum(len(p["contexts"]) for p in pool.values()),
                "pending_pairs": len(remaining), "pending_files": sum(p["needs_file_judgment"] for p in remaining),
                "pending_contexts": sum(len(p["contexts"]) for p in remaining),
                "actual_top5_slots": len(provenance), "top5_denominator_per_arm": len(queries) * 5,
                "reused_files": reuse["reused_files"], "reused_contexts": reuse["reused_contexts"],
                "blind_to_algorithm_rank_known_positives": True, "sources_path": str(Path(sources_path).resolve()),
                "queries_path": str(Path(queries_path).resolve()), "results_paths": [str(p.resolve()) for p in result_paths],
                "input_sha256": bound_inputs,
                "reuse_input_sha256": reuse["input_sha256"],
                "artifact_sha256": {name: file_sha(out / name) for name in ("blind_judgment_pool.jsonl", "judgment_provenance.jsonl", "cached_judgments.jsonl")}}
    save_json(out / "judgment_pool_manifest.json", manifest)
    # Prepared pools never claim complete metrics before the explicit summary step.
    pending_metrics = {"status": "incomplete" if remaining else "ready_for_metrics", "evaluation": "model_review_only",
                       "human_judgments": 0, "human_approved": False, "queries": len(queries), "metrics": [],
                       "pending_pairs": len(remaining), "pending_files": manifest["pending_files"],
                       "pending_contexts": manifest["pending_contexts"], "judgments_sha256": reuse["validated_judgments_sha256"]}
    save_json(out / "metrics.json", pending_metrics)
    (out / "metrics.md").write_text(metrics_markdown(pending_metrics), encoding="utf-8")
    write_rows(out / "per_query_metrics.jsonl", [])
    return manifest


def metrics_markdown(summary):
    if summary["status"] != "complete":
        status = "评分已齐，等待统计" if summary["status"] == "ready_for_metrics" else "评分不完整，未生成完整指标"
        return f"# E04模型判断统计\n\n状态：{status}。\n\n待评全文：{summary['pending_files']}；待评片段：{summary['pending_contexts']}；待办见remaining_pool.jsonl。\n"
    lines = ["# E04模型判断统计", "", "状态：评分完整；以下均为模型意见，未经人工验收。固定每题5位置，有用阈值为2分。", "",
             "|配置|题数|片段有用率@5|片段覆盖率|全文有用率@5|片段误导率|全文误导率|片段均分|已知来源命中@5（有效题数）|",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for a in summary["metrics"]:
        known = f"{a['known_source_hit_at5']:.1%}" if a["known_source_hit_at5"] is not None else "不适用"
        lines.append(f"|{a['arm']}|{a['queries']}|{a['context_useful_at5']:.1%}|{a['context_coverage_at5']:.1%}|{a['useful_at5']:.1%}|{a['context_misleading_at5']:.1%}|{a['misleading_at5']:.1%}|{a['mean_context_help_at5']:.3f}|{known}（{a['known_source_hit_at5_n']}）|")
    lines += ["", "全文低分但片段高分的分歧单列于file_context_disagreements.jsonl，保留原全文评分。逐题、分组、原话、实际返回区间和ID见配套JSON产物。", "", "已知来源命中为辅助检查；无已知来源的题不计漏召回。本实验不声称真实召回率或全局金标。", ""]
    return "\n".join(lines)


def summarize(queries_path, results_paths, output_dir, judgment_paths=(), *, sources_path=SOURCES):
    result_paths, judgment_paths = paths(results_paths), paths(judgment_paths)
    out = check_output_dir(output_dir)
    check_input_output_isolation(out, [queries_path, *result_paths, sources_path, *judgment_paths])
    verify_resume_rows(out)
    if not (out / "judgment_pool_manifest.json").exists():
        prepare(queries_path, result_paths, out, sources_path=sources_path)
    manifest = verify_prepared_manifest(out, input_hashes(queries_path, result_paths, sources_path))
    for path, expected in manifest["input_sha256"].items():
        require(file_sha(path) == expected, f"input SHA drift: {path}")
    for path, expected in manifest.get("reuse_input_sha256", {}).items():
        require(file_sha(path) == expected, f"reuse input SHA drift: {path}")
    for name, expected in manifest["artifact_sha256"].items():
        require(file_sha(out / name) == expected, f"prepared artifact SHA drift: {name}")
    queries = load_queries(queries_path)
    results = [r for path in result_paths for r in read_rows(path)]
    fresh_pool, provenance = build_pool(queries, results, load_sources(sources_path))
    pool = validate_pool(read_rows(out / "blind_judgment_pool.jsonl"))
    require(set(pool) == set(fresh_pool), "pool pair coverage drift")
    for pid, p in pool.items():
        for key in ("query_id", "query_text", "file_id", "source_sha256", "full_source_text", "contexts"):
            require(p[key] == fresh_pool[pid][key], f"pool/source binding drift: {pid}:{key}")
    require(provenance == read_rows(out / "judgment_provenance.jsonl"), "retrieval provenance drift")
    cache = unique(read_rows(out / "cached_judgments.jsonl"), "pair_id", "cached pair")
    resume_path = out / "validated_judgments.jsonl"
    if resume_path.exists():
        cache = merge_cache(pool, cache, read_rows(resume_path))
    submitted = [r for path in judgment_paths for r in read_rows(path)]
    submitted_hashes = {str(path.resolve()): file_sha(path) for path in judgment_paths}
    merged, remaining, disagreements = merge_judgments(pool, cache, submitted)
    write_rows(out / "validated_judgments.jsonl", sorted(merged.values(), key=lambda j: j["pair_id"]))
    write_rows(out / "remaining_pool.jsonl", remaining)
    write_rows(out / "file_context_disagreements.jsonl", disagreements)
    if remaining:
        summary = {"status": "incomplete", "evaluation": "model_review_only", "human_judgments": 0, "human_approved": False,
                   "queries": len(queries), "metrics": [], "pending_pairs": len(remaining),
                   "pending_files": sum(p["needs_file_judgment"] for p in remaining),
                   "pending_contexts": sum(len(p["contexts"]) for p in remaining),
                   "reason": "All actual Top5 files and contexts require validated judgments; unknown is not zero."}
        per_query = []
    else:
        summary, per_query = compute_metrics(queries, results, pool, merged)
    summary["file_context_disagreements"] = len(disagreements)
    summary["input_sha256"] = {**manifest["input_sha256"], **manifest.get("reuse_input_sha256", {}), **submitted_hashes}
    summary["judgments_sha256"] = file_sha(out / "validated_judgments.jsonl")
    save_json(out / "metrics.json", summary)
    (out / "metrics.md").write_text(metrics_markdown(summary), encoding="utf-8")
    write_rows(out / "per_query_metrics.jsonl", per_query)
    reuse_path = out / "reuse_provenance.json"
    reuse = json.loads(reuse_path.read_text(encoding="utf-8"))
    reuse["judgment_inputs_sha256"] = submitted_hashes
    reuse["validated_judgments_sha256"] = summary["judgments_sha256"]
    reuse["remaining_pairs"] = len(remaining)
    save_json(reuse_path, reuse)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "summarize"):
        command = commands.add_parser(name)
        command.add_argument("--queries", required=True)
        command.add_argument("--results", nargs="+", required=True, metavar="PATH")
        command.add_argument("--output-dir", required=True)
        command.add_argument("--sources", default=str(SOURCES), help="Explicit permitted normalized source JSONL; production default is frozen9639")
        if name == "prepare":
            command.add_argument("--reuse-pool", nargs="+")
            command.add_argument("--reuse-judgments", nargs="+")
        else:
            command.add_argument("--judgments", nargs="*", default=[])
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.queries, args.results, args.output_dir, args.reuse_pool, args.reuse_judgments, sources_path=args.sources)
        else:
            result = summarize(args.queries, args.results, args.output_dir, args.judgments, sources_path=args.sources)
        visible = {key: result[key] for key in ("status", "queries", "unique_query_file_pairs", "context_variants", "pending_pairs", "pending_files", "pending_contexts", "reused_files", "reused_contexts") if key in result}
        print(json.dumps(visible, ensure_ascii=False, allow_nan=False))
        return 2 if result["status"] == "incomplete" else 0
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
