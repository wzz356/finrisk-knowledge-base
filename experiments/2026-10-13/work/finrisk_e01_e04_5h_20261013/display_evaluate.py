"""Fixed-ranking display diagnostics; exact same-round grade reuse only."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("display_frozen_eval", HERE / "evaluate.py")
E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
E.ARMS = ("B0", "D1", "D2")
E.backend.ARMS = E.ARMS
old_hashes = E.backend.input_hashes
old_compute = E.backend.compute_metrics


def hashes(queries_path, results_paths, sources_path):
    result = old_hashes(queries_path, results_paths, sources_path)
    result[str(Path(__file__).resolve())] = E.file_sha(__file__)
    return result


def compute(queries, results, pool, judgments):
    summary, perquery = old_compute(queries, results, pool, judgments)
    summary["metric_scope"] = "Same-round frozen B0 ranking, source-scoped return and scoped background diagnostic"
    summary["limitations"].append("返回对照在主检索曝光分析后、完整语义指标/采用决策前追加；无新GPU推理，不是独立确认")
    return summary, perquery


E.backend.input_hashes = hashes
E.backend.compute_metrics = compute


def prepare(queries, results, output, *, sources_path=None):
    # Only a complete, source-bound judgment artifact from this same round.
    phase = E.OUT / "evaluation"
    metrics = json.loads((phase / "metrics.json").read_text(encoding="utf-8"))
    if metrics["status"] != "complete" or metrics["judgments_sha256"] != E.file_sha(phase / "validated_judgments.jsonl"):
        raise ValueError("Main round grades must be complete and bound before reuse")
    return E.backend.prepare(queries, results, output, phase / "blind_judgment_pool.jsonl",
                             [phase / "validated_judgments.jsonl"], sources_path=sources_path or E.backend.SOURCES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "summarize"):
        p = sub.add_parser(name)
        p.add_argument("--queries", required=True, type=Path)
        p.add_argument("--results", required=True, type=Path, nargs="+")
        p.add_argument("--output-dir", required=True, type=Path)
        if name == "summarize":
            p.add_argument("--judgments", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    result = (prepare(args.queries, args.results, args.output_dir) if args.command == "prepare" else
              E.backend.summarize(args.queries, args.results, args.output_dir, args.judgments, sources_path=E.backend.SOURCES))
    print(json.dumps({k: result[k] for k in ("status", "queries", "unique_query_file_pairs", "context_variants", "pending_pairs", "pending_contexts", "reused_files", "reused_contexts") if k in result}, ensure_ascii=False))
    return 2 if args.command == "summarize" and result["status"] == "incomplete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
