"""Merge unchanged same-round semantic grades, evaluate selected combination."""
import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("combo_source_eval", HERE / "evaluate.py")
E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
E.ARMS = ("B0", "W4", "WD"); E.backend.ARMS = E.ARMS
old_hashes, old_compute = E.backend.input_hashes, E.backend.compute_metrics


def hashes(queries, results, sources):
    value = old_hashes(queries, results, sources)
    value[str(Path(__file__).resolve())] = E.file_sha(__file__)
    return value


def compute(queries, results, pool, judgments):
    summary, perquery = old_compute(queries, results, pool, judgments)
    summary["metric_scope"] = "Post-selection same-input combination diagnostic; not independent confirmation"
    summary["limitations"].append("组合在W4/D1结果之后选择，42输入均已用；0新GPU调用，不算新确认")
    return summary, perquery


E.backend.input_hashes, E.backend.compute_metrics = hashes, compute


def merge_same_round():
    pools, grades = {}, {}
    for phase in ("evaluation", "display_evaluation"):
        folder = E.OUT / phase
        metrics = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
        if metrics["status"] != "complete" or metrics["judgments_sha256"] != E.file_sha(folder / "validated_judgments.jsonl"):
            raise ValueError("Source phase incomplete or grade binding changed")
        current_pool = E.validate_pool(E.read_rows(folder / "blind_judgment_pool.jsonl"))
        current_grades = E.unique(E.read_rows(folder / "validated_judgments.jsonl"), "pair_id", "grades")
        for pid, p in current_pool.items():
            if pid not in pools:
                pools[pid], grades[pid] = copy.deepcopy(p), copy.deepcopy(current_grades[pid])
                continue
            prior, grade = pools[pid], grades[pid]
            for key in ("query_id", "query_text", "file_id", "source_sha256", "full_source_text"):
                if prior[key] != p[key]:
                    raise ValueError("Same-round pool source/input conflict")
            for key in E.backend.FILE_FIELDS:
                if grade[key] != current_grades[pid][key]:
                    raise ValueError("Same-round whole-source grade conflict")
            pc = {c["context_id"]: c for c in prior["contexts"]}
            gc = {c["context_id"]: c for c in grade["contexts"]}
            for c in p["contexts"]:
                if c["context_id"] in pc and pc[c["context_id"]]["text"] != c["text"]:
                    raise ValueError("Context hash collision")
                pc.setdefault(c["context_id"], copy.deepcopy(c))
            for c in current_grades[pid]["contexts"]:
                if c["context_id"] in gc and gc[c["context_id"]] != c:
                    raise ValueError("Same-round context grade conflict")
                gc.setdefault(c["context_id"], copy.deepcopy(c))
            prior["contexts"], grade["contexts"] = list(pc.values()), list(gc.values())
    E.validate_pool(list(pools.values()))
    for pid, p in pools.items():
        E.backend._legacy.validate_judgment(grades[pid], p)
    pp, jp = E.OUT / "same_round_pool.jsonl", E.OUT / "same_round_judgments.jsonl"
    for path in (pp, jp):
        if path.exists():
            raise FileExistsError(path)
    E.backend.write_rows(pp, sorted(pools.values(), key=lambda p: p["pair_id"]))
    E.backend.write_rows(jp, sorted(grades.values(), key=lambda p: p["pair_id"]))
    return pp, jp


def main():
    pp, jp = merge_same_round()
    phase = E.OUT / "combo_evaluation"
    result = E.backend.prepare(E.OUT / "queries.jsonl", [E.OUT / "combo_results.jsonl"], phase, pp, [jp], sources_path=E.backend.SOURCES)
    print(json.dumps({k: result[k] for k in ("status", "pending_pairs", "pending_contexts", "reused_files", "reused_contexts")}))


if __name__ == "__main__":
    main()
