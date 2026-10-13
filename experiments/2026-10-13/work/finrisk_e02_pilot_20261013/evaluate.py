"""E02 fresh model-review pools; extend frozen E04 validation without editing it."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E02小批量实验_20261013"
E04_PATH = ROOT / "work/finrisk_e04_pilot_20261012/evaluate.py"
E04_SHA = "4f76a7f0655c0db95f9033aa0b74c11ef467cddf707275a40059da4c525a3e0c"
LABELS = {"文书主体", "片段主体", "责任角色", "行为背景", "适用条件", "材料用途", "产品背景"}
HEAD = "【背景说明（原文摘录，候选）】\n"
SEPARATOR = "\n\n【原文片段】\n"
if hashlib.sha256(E04_PATH.read_bytes()).hexdigest() != E04_SHA:
    raise ValueError("frozen E04 evaluator has changed")
_spec = importlib.util.spec_from_file_location("e02_readonly_e04_eval", E04_PATH)
_backend = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_backend)
_backend.ARMS = ("P0", "P1", "P2")
_backend.OUTPUT_ROOTS = (OUT,)
_raw_context = _backend._legacy.validate_context
_raw_build_pool = _backend.build_pool
_raw_compute = _backend.compute_metrics
_raw_input_hashes = _backend.input_hashes
require = _backend.require
text_sha = _backend.text_sha
file_sha = _backend.file_sha
read_rows = _backend.read_rows
load_queries = _backend.load_queries
load_sources = _backend.load_sources
check_output_dir = _backend.check_output_dir
validate_context_judgment = _backend._legacy.validate_context_judgment


def validate_context(hit, source):
    prefix = hit.get("prefix", "")
    require(isinstance(prefix, str), "prefix must be string")
    if not prefix:
        require(not hit.get("prefix_claims"), "claims without a visible background")
        return _raw_context(hit, source)
    require(hit.get("prefix_profile") == "E02-extractive-v1", "unknown prefix profile")
    require(hit.get("prefix_review_status") == "approved_model_review", "prefix review is absent or pending")
    require(len(prefix) <= 180, "prefix exceeds frozen 180-character limit")
    claims = hit.get("prefix_claims")
    require(isinstance(claims, list) and 1 <= len(claims) <= 3, "invalid extractive claims")
    for claim in claims:
        require(isinstance(claim, dict) and claim.get("label") in LABELS, "invalid prefix label")
        require(isinstance(claim.get("quote"), str) and claim["quote"].strip(), "empty prefix quote")
        require(isinstance(claim.get("link_reason"), str) and claim["link_reason"].strip(), "missing semantic-link audit reason")
        _backend._legacy.valid_span(claim.get("span"), source, claim["quote"])
    expected_prefix = "\n".join(c["label"] + "：" + c["quote"] for c in claims)
    require(prefix == expected_prefix, "background differs from extractive claims")
    if "unit_id" in hit:
        require(hit.get("prefix_source_unit_id") == hit["unit_id"], "background belongs to another winning unit")
    body = hit.get("base_context_text")
    require(isinstance(body, str) and body.strip(), "missing original context text")
    require(hit.get("text") == HEAD + prefix + SEPARATOR + body, "derived/background/body rendering mismatch")
    plain = copy.deepcopy(hit)
    plain["text"], plain["prefix"] = body, ""
    raw = _raw_context(plain, source)
    raw.update(context_id=_backend._legacy.context_id(hit["text"]), text=hit["text"], prefix=prefix,
               prefix_claims=copy.deepcopy(claims), prefix_profile="E02-extractive-v1",
               prefix_review_status="approved_model_review", base_context_text=body)
    return raw


def clean_queries(queries):
    return {qid: {k: copy.deepcopy(q[k]) for k in ("query_id", "text", "group", "query_role") if k in q}
            for qid, q in queries.items()}


def build_pool(queries, results, sources):
    pool, provenance = _raw_build_pool(clean_queries(queries), results, sources)
    for p in pool.values():
        p.pop("query_task", None)
        p["scoring_instructions"]["task"] += " 背景字段标签是派生说明，标签后的摘录可逐字回源；仍须依据当前输入核查主体/同案条件，不能把文书身份视为片段行为实施者。"
    return pool, provenance


def compute_metrics(queries, results, pool, judgments):
    summary, perquery = _raw_compute(clean_queries(queries), results, pool, judgments)
    summary["metric_scope"] = "Fixed 22-query diagnostic replay; actual Top5 helpfulness"
    summary["limitations"] = ["当前会话模型辅助评分，非人工金标", "22条输入已用于E04，本轮为诊断回放，非独立确认集",
                              "只改变24个代表单元，不代表全量知识库背景收益", "配置名称、排名与作者预期说明隐藏；片段是否有背景可见",
                              "固定每题5位置，有用>=2；缺评分不能默认为0或报告完整"]
    return summary, perquery


def input_hashes(queries_path, result_paths, sources_path):
    value = _raw_input_hashes(queries_path, result_paths, sources_path)
    value[str(Path(__file__).resolve())] = file_sha(__file__)
    return value


_backend._legacy.validate_context = validate_context
_backend.build_pool = build_pool
_backend.compute_metrics = compute_metrics
_backend.input_hashes = input_hashes
validate_pool = _backend.validate_pool
merge_judgments = _backend.merge_judgments
unique = _backend.unique


def prepare(queries_path, results_paths, output_dir, reuse_pool=None, reuse_judgment_paths=None, *, sources_path=None):
    require(not reuse_pool and not reuse_judgment_paths, "E02 requires fresh semantic judgments, no previous grade reuse")
    return _backend.prepare(queries_path, results_paths, output_dir, sources_path=sources_path or _backend.SOURCES)


def summarize(queries_path, results_paths, output_dir, judgment_paths=(), *, sources_path=None):
    result = _backend.summarize(queries_path, results_paths, output_dir, judgment_paths, sources_path=sources_path or _backend.SOURCES)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "summarize"):
        p = sub.add_parser(name)
        p.add_argument("--queries", required=True, type=Path)
        p.add_argument("--results", nargs="+", required=True, type=Path)
        p.add_argument("--output-dir", required=True, type=Path)
        p.add_argument("--sources", type=Path, default=_backend.SOURCES)
        if name == "summarize":
            p.add_argument("--judgments", nargs="*", default=[], type=Path)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        result = prepare(args.queries, args.results, args.output_dir, sources_path=args.sources)
    else:
        result = summarize(args.queries, args.results, args.output_dir, args.judgments, sources_path=args.sources)
    print(json.dumps({k: result[k] for k in ("status", "queries", "unique_query_file_pairs", "context_variants", "pending_pairs", "pending_files", "pending_contexts") if k in result}, ensure_ascii=False))
    return 2 if result["status"] == "incomplete" and args.command == "summarize" else 0


if __name__ == "__main__":
    raise SystemExit(main())
