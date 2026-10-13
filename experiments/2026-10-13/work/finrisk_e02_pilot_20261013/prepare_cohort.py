"""Prepare a deterministic diagnostic cohort; no semantic labels are generated."""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E02小批量实验_20261013"
E04 = ROOT / "outputs/FinRisk_E04小批量实验_20261012"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def save(name, value):
    p = OUT / name
    if p.exists():
        raise ValueError("refuse existing cohort output: " + name)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def lines(name, values):
    p = OUT / name
    if p.exists():
        raise ValueError("refuse existing cohort output: " + name)
    p.write_text("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in values), encoding="utf-8")


manifest = json.loads((E04 / "delivery_manifest.json").read_text(encoding="utf-8"))
for item in manifest["output_files"] + manifest["work_code_notes_and_logs"]:
    if sha(ROOT / item["path"]) != item["sha256"]:
        raise ValueError("E04 delivery drift: " + item["path"])
source_path = ROOT / "outputs/FinRisk_知识库V2_20261012/normalized_final/data/documents.jsonl"
unit_path = ROOT / "outputs/FinRisk_知识库V2_20261012/indexes/all9639_final/structured.jsonl"
sources = {v["official_file_id"]: v for v in read(source_path)}
units = read(unit_path)
unit_map = {v["unit_id"]: v for v in units}
if len(sources) != 9639 or len(units) != 65475 or len(unit_map) != 65475:
    raise ValueError("incomplete permitted population")
query_originals, perquery = [], []
for phase in ("dev", "confirmation"):
    query_originals += read(E04 / (phase + "_queries.jsonl"))
    perquery += read(E04 / (phase + "_evaluation") / "per_query_metrics.jsonl")
baseline = [v for v in perquery if v["arm"] == "A0"]
all_hits = [h for v in perquery for h in v["top5"]]
base_hits = [h for v in baseline for h in v["top5"]]
selected = {}
mandatory = ["F006493", "F003464", "F008940", "F008944", "F009488", "F009491", "F009587", "F000699"]
for fid in mandatory:
    if fid in ("F009587", "F000699"):
        anchor = next(a["quote"] for q in query_originals if q["query_id"] in ("Q009", "Q012") for a in q["anchor_evidence"] if a["file_id"] == fid)
        candidates = [u for u in units if u["file_id"] == fid and len(u["text"]) <= 220]
        if not candidates:
            raise ValueError("no short anchor unit: " + fid)
        # Diagnostic targeting is explicit; prefix authors will not receive query/anchor metadata.
        u = sorted(candidates, key=lambda v: (anchor not in v["text"], -len(set(anchor) & set(v["text"])), len(v["text"]), v["unit_id"]))[0]
    else:
        h = next(h for h in all_hits if h["file_id"] == fid)
        u = unit_map[h["unit_id"]]
    selected[fid] = {"unit": u, "selection_group": "known_context_or_failure_diagnostic"}
rng = random.Random(20261013)
for group, useful in (("short_weak_return", False), ("short_useful_control", True)):
    by_file = {}
    for h in base_hits:
        if h["file_id"] in selected or (h["context_help_grade"] >= 2) != useful:
            continue
        u = unit_map[h["unit_id"]]
        if len(u["text"]) <= 140:
            by_file.setdefault(h["file_id"], u)
    choices = sorted(by_file)
    if len(choices) < 8:
        raise ValueError("insufficient group: " + group)
    for fid in rng.sample(choices, 8):
        selected[fid] = {"unit": by_file[fid], "selection_group": group}
inputs, cohort = [], []
for fid, selected_row in selected.items():
    unit = selected_row["unit"]
    source = sources[fid]["full_text"]
    source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if unit["source_sha256"] != source_sha:
        raise ValueError("source SHA differs: " + fid)
    inputs.append({"file_id": fid, "source_sha256": source_sha, "full_source_text": source, "unit": unit})
    cohort.append({"file_id": fid, "unit_id": unit["unit_id"], "selection_group": selected_row["selection_group"],
                   "source_sha256": source_sha, "base_unit_text_sha256": hashlib.sha256(unit["text"].encode("utf-8")).hexdigest(),
                   "indexed_chars": len(unit["text"]), "returned_chars": len(unit["context_text"])})
queries = [{"query_id": q["query_id"], "text": q["text"], "group": q["group"],
            "query_role": q.get("query_role", "boundary" if q["group"] == "boundary_condition_change" else "risk"),
            "replay_origin": "E04_used_input_not_independent_holdout"} for q in query_originals]
lines("queries.jsonl", queries)
lines("prefix_inputs_p1.jsonl", inputs[:12])
lines("prefix_inputs_p2.jsonl", inputs[12:])
save("cohort.json", {"seed": 20261013, "documents": 24, "units": 24, "rows": cohort,
                     "selection_is_diagnostic": True, "authors_receive_queries_or_previous_grades": False,
                     "all_source_population": 9639, "all_searchable_units": 65475,
                     "scope": "one representative unit per document; other units unchanged"})
protected = json.loads((E04 / "input_freeze.json").read_text(encoding="utf-8"))["protected_input_sha256"]
protected.update({str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in (E04 / "delivery_manifest.json", ROOT / "work/finrisk_e04_pilot_20261012/experiment.py", ROOT / "work/finrisk_e04_pilot_20261012/evaluate.py")})
snapshot = json.loads((E04 / "execution_freeze.json").read_text(encoding="utf-8"))["old_cache_readonly_snapshot"]
save("input_freeze.json", {"protected_input_sha256": protected, "e04_delivery_manifest_sha256": sha(E04 / "delivery_manifest.json"),
                         "old_cache_readonly_snapshot": snapshot,
                         "experiment_inputs_sha256": {n: sha(OUT / n) for n in ("queries.jsonl", "prefix_inputs_p1.jsonl", "prefix_inputs_p2.jsonl", "cohort.json")},
                         "query_count": 22, "documents": 24, "units": 24, "evaluation": "model_review_only_diagnostic_replay"})
print(json.dumps({"documents": 24, "units": 24, "queries": len(queries), "source_chars": sum(len(v["full_source_text"]) for v in inputs),
                  "cohort": [{"file_id": v["file_id"], "group": v["selection_group"], "indexed_chars": v["indexed_chars"]} for v in cohort]}, ensure_ascii=False))
