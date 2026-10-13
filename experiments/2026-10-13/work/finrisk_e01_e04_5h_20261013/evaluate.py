"""Source-verified fresh five-arm evaluation; never assigns semantic grades."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"
E04 = ROOT / "work/finrisk_e04_pilot_20261012/evaluate.py"
ARMS = ("B0", "S1", "C2", "W4", "M3")
LABELS = {"文书主体", "片段主体", "责任角色", "行为背景", "适用条件", "材料用途", "产品背景"}
MATCH_HEAD = "【命中原话】\n"
SCOPE_HEAD = "\n\n【命中原话的对应原文（逐段独立，不合并主体）】\n"
PREFIX_HEAD = "【仅适用于下方命中片段的背景（原文摘录，候选）】\n"
if hashlib.sha256(E04.read_bytes()).hexdigest() != "4f76a7f0655c0db95f9033aa0b74c11ef467cddf707275a40059da4c525a3e0c":
    raise ValueError("Frozen E04 evaluator changed")
old_freeze = json.loads((ROOT / "outputs/FinRisk_E02小批量实验_20261013/execution_freeze.json").read_text(encoding="utf-8"))
legacy_path = ROOT / "work/finrisk_v2_20261012/eval_v2.py"
if hashlib.sha256(legacy_path.read_bytes()).hexdigest() != old_freeze["old_evaluation_helper_sha256"]:
    raise ValueError("Frozen original source validator changed")
spec = importlib.util.spec_from_file_location("fiveh_readonly_e04_eval", E04)
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
backend.ARMS = ARMS
backend.OUTPUT_ROOTS = (OUT,)
require = backend.require
text_sha = backend.text_sha
file_sha = backend.file_sha
read_rows = backend.read_rows
load_queries = backend.load_queries
load_sources = backend.load_sources
check_output_dir = backend.check_output_dir
unique = backend.unique
raw_context = backend._legacy.validate_context
raw_build = backend.build_pool
raw_compute = backend.compute_metrics
raw_hashes = backend.input_hashes
validate_context_judgment = backend._legacy.validate_context_judgment


def validate_context(hit, source):
    if not hit.get("scope_profile"):
        require(not hit.get("prefix_claims"), "extractive prefix without scoped display")
        return raw_context(hit, source)
    require(hit["scope_profile"] == "5h-scoped-v1", "Unknown scope profile")
    require(hit.get("scope_review_status") == "approved_model_review", "Scope review is pending or missing")
    original = hit.get("original_unit_text")
    matches = hit.get("original_unit_spans")
    require(isinstance(original, str) and original.strip(), "Missing original indexed quote")
    require(isinstance(matches, list) and matches, "Missing original occurrence spans")
    for span in matches:
        backend._legacy.valid_span(span, source, original)
    segments = hit.get("source_segments")
    require(isinstance(segments, list) and segments, "Missing scoped source segments")
    require(any(original in s.get("text", "") for s in segments), "Scoped segments belong to a different original quote")
    prefix = hit.get("prefix", "")
    require(isinstance(prefix, str), "Invalid prefix type")
    if prefix:
        require(hit.get("prefix_review_status") == "approved_model_review", "Missing prefix approval")
        claims = hit.get("prefix_claims")
        require(isinstance(claims, list) and 1 <= len(claims) <= 3 and len(prefix) <= 180, "Invalid background dose")
        for claim in claims:
            require(claim.get("label") in LABELS, "Invalid extractive label")
            require(isinstance(claim.get("link_reason"), str) and claim["link_reason"].strip(), "Missing semantic source association")
            backend._legacy.valid_span(claim.get("span"), source, claim.get("quote"))
        require(prefix == "\n".join(c["label"] + "：" + c["quote"] for c in claims), "Background contains unquoted assertions")
        if "unit_id" in hit:
            require(hit.get("prefix_source_unit_id") == hit["unit_id"], "Background belongs to another unit")
    else:
        require(not hit.get("prefix_claims"), "Claims not visible in display")
    gap_text = backend._legacy.GAP.join(s["text"] for s in segments)
    expected = MATCH_HEAD + original + SCOPE_HEAD + gap_text
    if prefix:
        expected = PREFIX_HEAD + prefix + "\n\n" + expected
    require(hit.get("text") == expected, "Display differs from verified source sections")
    plain = copy.deepcopy(hit)
    plain.update(text=gap_text, prefix="")
    checked = raw_context(plain, source)
    checked.update(context_id=backend._legacy.context_id(expected), text=expected, prefix=prefix,
                   scope_profile="5h-scoped-v1", scope_review_status=hit["scope_review_status"],
                   original_unit_text=original, original_unit_spans=copy.deepcopy(matches))
    for key in ("scope_status", "occurrence_ambiguity", "matched_occurrences"):
        if key in hit:
            checked[key] = copy.deepcopy(hit[key])
    if prefix:
        checked.update(prefix_claims=copy.deepcopy(claims), prefix_review_status=hit["prefix_review_status"])
    return checked


def clean_queries(queries):
    return {qid: {k: copy.deepcopy(q[k]) for k in ("query_id", "text", "group", "query_role") if k in q}
            for qid, q in queries.items()}


def require_five_arms(results):
    require({r["arm"] for r in results} == set(ARMS), "Five complete arms are required")


def build_pool(queries, results, sources):
    require_five_arms(results)
    pool, provenance = raw_build(clean_queries(queries), results, sources)
    for p in pool.values():
        p.pop("query_task", None)
        p["scoring_instructions"]["task"] += " 字段标题和范围提示是派生说明；逐段原文独立，不自动合并主体/事件，也不因边界条件相反认定输入违规。"
    return pool, provenance


def compute_metrics(queries, results, pool, judgments):
    require_five_arms(results)
    summary, perquery = raw_compute(clean_queries(queries), results, pool, judgments)
    strata = {}
    for label, is_new in (("diagnostic_replay", False), ("new_business", True)):
        ids = {qid for qid, q in queries.items() if (q.get("replay_origin") == "new_business_text_not_human_gold") == is_new}
        if ids:
            strata[label] = {"queries": len(ids), "metrics": [backend.aggregate_metrics([r for r in perquery if r["arm"] == a and r["query_id"] in ids], a) for a in ARMS]}
    summary["strata"] = strata
    summary["metric_scope"] = "Five-hour controlled helpfulness experiment; replay and new texts reported separately"
    summary["limitations"] = ["同轮统一模型意见，非人工金标", "22旧回放与20新业务文字分开，新文字不证明事件隔离或27类覆盖",
                              "仅24源单元局部表示与3–5候选机制卡，不外推全库收益", "配置/排名/作者预期隐藏，实际格式干预可见",
                              "固定每题5位置，有用>=2，缺评不记0，所有分数新评"]
    return summary, perquery


def input_hashes(queries_path, result_paths, sources_path):
    value = raw_hashes(queries_path, result_paths, sources_path)
    value[str(Path(__file__).resolve())] = file_sha(__file__)
    return value


backend._legacy.validate_context = validate_context
backend.build_pool = build_pool
backend.compute_metrics = compute_metrics
backend.input_hashes = input_hashes
validate_pool = backend.validate_pool
merge_judgments = backend.merge_judgments


def prepare(queries_path, results_paths, output_dir, reuse_pool=None, reuse_judgment_paths=None, *, sources_path=None):
    require(not reuse_pool and not reuse_judgment_paths, "Fresh semantic judgments required")
    return backend.prepare(queries_path, results_paths, output_dir, sources_path=sources_path or backend.SOURCES)


def summarize(queries_path, results_paths, output_dir, judgment_paths=(), *, sources_path=None):
    return backend.summarize(queries_path, results_paths, output_dir, judgment_paths, sources_path=sources_path or backend.SOURCES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "summarize"):
        p = sub.add_parser(name)
        p.add_argument("--queries", type=Path, required=True)
        p.add_argument("--results", type=Path, nargs="+", required=True)
        p.add_argument("--output-dir", type=Path, required=True)
        p.add_argument("--sources", type=Path, default=backend.SOURCES)
        if name == "summarize":
            p.add_argument("--judgments", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    result = (prepare(args.queries, args.results, args.output_dir, sources_path=args.sources) if args.command == "prepare"
              else summarize(args.queries, args.results, args.output_dir, args.judgments, sources_path=args.sources))
    print(json.dumps({k: result[k] for k in ("status", "queries", "unique_query_file_pairs", "context_variants", "pending_pairs") if k in result}, ensure_ascii=False))
    return 2 if args.command == "summarize" and result["status"] == "incomplete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
