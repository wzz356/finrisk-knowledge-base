"""1:1 offline retrieval, reviewed scoped returns and explicit session-judgment checks."""
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
OUT = ROOT / "outputs/FinRisk_离线演示V3_20261013"
PRIOR = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"
V2 = ROOT / "outputs/FinRisk_知识库V2_20261012"
GPU_PYTHON = ROOT / "work/finrisk_retrieval_20261012/.venv/Scripts/python.exe"
ADAPTER = ROOT / "work/finrisk_v2_20261012/run_v2.py"
DICTIONARY = ROOT / "finrisk-knowledge-base/dictionary/risk_type_dictionary.csv"
SOURCE_FILE = V2 / "normalized_final/data/documents.jsonl"


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_json(value):
    return sha_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False))


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_new(path, value, jsonl=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        if jsonl:
            for row in value:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
        else:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def source_map():
    documents = rows(SOURCE_FILE)
    result = {row["official_file_id"]: row["full_text"] for row in documents}
    if len(result) != 9639 or any(sha_text(row["full_text"]) != row["text_sha256"] for row in documents):
        raise ValueError("Source population/hash mismatch")
    return result


def load_scope(sources):
    runner = module(ROOT / "work/finrisk_e01_e04_5h_20261013/experiment.py", "v3_scope_runner")
    units = {row["unit_id"]: row for row in rows(V2 / "indexes/all9639_final/structured.jsonl")}
    approved = runner.validate_scope_units(rows(PRIOR / "scope_units.jsonl"), rows(PRIOR / "scope_review.jsonl"),
        read_json(ROOT / "outputs/FinRisk_E02小批量实验_20261013/cohort.json"), units, sources,
        sha_file(PRIOR / "scope_units.jsonl"))
    if len(approved) != 21:
        raise ValueError("Expected exactly 21 reviewed eligible units")
    return units, approved


def scoped_hit(hit, units, approved, sources):
    if hit["unit_id"] not in approved:
        return copy.deepcopy(hit)
    runner = module(ROOT / "work/finrisk_e01_e04_5h_20261013/experiment.py", "v3_scope_display")
    display = module(ROOT / "work/finrisk_e01_e04_5h_20261013/display_experiment.py", "v3_restore_model_fields")
    result = runner.decorate_hit(hit, units, approved, "S1", sources)
    return display.restore_model_fields(hit, result)


def make_packet(query, hits, sources):
    evidence = []
    for hit in hits:
        source = sources[hit["file_id"]]
        segments = hit.get("source_segments") or [
            {"text": source[span["start"]:span["end"]], "span": span} for span in hit["source_spans"]]
        for segment in segments:
            span = segment["span"]
            start, end = span["start"], span["end"]
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source) or source[start:end] != segment["text"]:
                raise ValueError("Evidence source span/text mismatch")
            if segment["text"] not in hit["text"]:
                raise ValueError("Evidence segment not actually displayed")
        row = copy.deepcopy(hit)
        row.update(source_segments=segments, source_text_sha256=sha_text(source),
                   displayed_text_sha256=sha_text(hit["text"]), source_document_reference=str(SOURCE_FILE))
        evidence.append(row)
    if len({(hit["file_id"], hit["unit_id"], hit["rank"]) for hit in evidence}) != len(evidence):
        raise ValueError("Duplicate evidence position")
    return {"version": "offline-demo-v3", "query_id": query["query_id"], "input_text": query["text"],
            "input_sha256": sha_text(query["text"]), "retrieval": {"weights": [1, 1], "rrf_k": 60, "rerank_top_k": 100},
            "human_approved": False, "evidence": evidence}


def validate_judgments(packets, judgments, labels):
    pool = {packet["query_id"]: packet for packet in packets}
    assigned = {judgment["query_id"]: judgment for judgment in judgments}
    if len(pool) != len(packets) or len(assigned) != len(judgments) or set(pool) != set(assigned):
        raise ValueError("Missing/duplicate/extra query judgment")
    useful = 0
    for qid, packet in pool.items():
        judgment = assigned[qid]
        if judgment.get("input_sha256") != packet["input_sha256"] or judgment.get("packet_sha256") != sha_json(packet):
            raise ValueError("Judgment input/packet binding mismatch")
        if judgment.get("origin") != "current_session_model" or judgment.get("human_approved") is not False:
            raise ValueError("Judgment origin/approval mismatch")
        if judgment.get("decision") not in {"risk_detected", "no_obvious_risk", "insufficient_information"}:
            raise ValueError("Invalid decision status")
        if not isinstance(judgment.get("reason"), str) or not judgment["reason"].strip():
            raise ValueError("Missing judgment reason")
        if any(not isinstance(judgment.get(key), list) for key in ["risk_labels", "missing_information", "boundary_notes", "evidence_assessments"]):
            raise ValueError("Invalid judgment list fields")
        if judgment["decision"] == "no_obvious_risk" and judgment["risk_labels"]:
            raise ValueError("No-risk decision cannot carry positive risk candidates")
        hits = {(hit["file_id"], hit["unit_id"], hit["rank"]): hit for hit in packet["evidence"]}
        assessments = {(item["file_id"], item["unit_id"], item["rank"]): item for item in judgment["evidence_assessments"]}
        if len(assessments) != len(judgment["evidence_assessments"]) or set(hits) != set(assessments):
            raise ValueError("Evidence positions must be assessed exactly once")
        helpful_files = set()
        for key, assessment in assessments.items():
            hit = hits[key]
            if assessment.get("relation") not in {"direct", "partial", "boundary", "irrelevant"} or type(assessment.get("helpful")) is not bool:
                raise ValueError("Invalid evidence relation/helpfulness")
            quote = assessment.get("quote")
            if not isinstance(quote, str) or not isinstance(assessment.get("reason"), str) or not assessment["reason"].strip() or not isinstance(assessment.get("warnings"), list):
                raise ValueError("Missing evidence explanation")
            if assessment["helpful"] and (not quote or quote not in hit["text"] or not any(quote in s["text"] for s in hit["source_segments"])):
                raise ValueError("Positive evidence requires an exact displayed source quote")
            if quote and (quote not in hit["text"] or not any(quote in s["text"] for s in hit["source_segments"])):
                raise ValueError("Evidence quote not in actual returned source segment")
            if assessment["helpful"]:
                useful += 1
                helpful_files.add(hit["file_id"])
        risk_tags = []
        for risk in judgment["risk_labels"]:
            if risk.get("risk_tag") not in labels or risk.get("certainty") not in {"likely", "possible"}:
                raise ValueError("Unofficial risk label or invalid certainty")
            if not risk.get("input_quote") or risk["input_quote"] not in packet["input_text"]:
                raise ValueError("Risk candidate lacks exact input quote")
            if not isinstance(risk.get("evidence_file_ids"), list) or not set(risk["evidence_file_ids"]).issubset(helpful_files):
                raise ValueError("Label cites unhelpful/unreturned evidence")
            if not isinstance(risk.get("limitations"), str) or not risk["limitations"].strip():
                raise ValueError("Risk label scope limitation required")
            risk_tags.append(risk["risk_tag"])
        if len(risk_tags) != len(set(risk_tags)):
            raise ValueError("Duplicate risk candidate")
    return {"judgments": len(judgments), "evidence_positions": sum(len(p["evidence"]) for p in packets),
            "model_useful_positions": useful, "human_approved": False, "semantic_gold": False}


def assert_freeze(path):
    frozen = read_json(path)
    for name, digest in frozen["files_sha256"].items():
        if sha_file(Path(name)) != digest:
            raise ValueError("Frozen dependency drift: " + name)
    return frozen


def retrieve(args):
    assert_freeze(OUT / "input_freeze.json")
    for suffix in ["", ".run.json", ".token_audit.jsonl", ".partial"]:
        if Path(str(args.output) + suffix).exists():
            raise FileExistsError("Refusing to overwrite output/sidecar")
    cache = args.cache.resolve()
    if not cache.is_relative_to(WORK.resolve()) or cache == WORK.resolve() or cache.exists():
        raise ValueError("Use a new cache child under this work directory")
    cache.mkdir(parents=True)
    for meta in (ROOT / "work/finrisk_retrieval_20261012/vector_cache").glob("*.json"):
        data = read_json(meta)
        if data.get("binding", {}).get("kind") == "document" and data.get("shape", [0])[0] == 65475:
            vector = meta.with_suffix(".npy")
            if sha_file(vector) != data["npy_sha256"]:
                raise ValueError("Old document cache binding mismatch")
            shutil.copy2(meta, cache / meta.name)
            shutil.copy2(vector, cache / vector.name)
    command = [str(GPU_PYTHON), "-X", "utf8", "-B", str(ADAPTER), "--run", "--prepared", str(V2 / "indexes/all9639_final"),
               "--scope", "all", "--expected-files", "9639", "--queries", str(args.queries), "--output", str(args.output),
               "--cache", str(cache), "--device", "cuda", "--precision", "float16", "--batch-size", "16", "--max-length", "512", "--arms", "rrf_rerank"]
    subprocess.run(command, check=True)
    assert_freeze(OUT / "input_freeze.json")


def prepare(args):
    assert_freeze(OUT / "input_freeze.json")
    queries = {row["query_id"]: row for row in rows(args.queries)}
    actual = rows(args.results)
    if len(queries) != len(rows(args.queries)) or len(actual) != len(queries) or {row["query_id"] for row in actual} != set(queries):
        raise ValueError("Incomplete/duplicate result population")
    run = read_json(Path(str(args.results) + ".run.json"))
    if run["status"] != "complete" or run["queries_sha256"] != sha_file(args.queries) or not run["rrf"]["equal_weights"]:
        raise ValueError("Parent retrieval is not a complete bound 1:1 run")
    sources = source_map()
    units, approved = load_scope(sources)
    display, packets = [], []
    for record in actual:
        if record["arm"] != "rrf_rerank" or record["text"] != queries[record["query_id"]]["text"]:
            raise ValueError("Wrong retrieval arm/query")
        new = copy.deepcopy(record)
        for kind in ["files", "cases"]:
            new[kind] = [scoped_hit(hit, units, approved, sources) for hit in record[kind]]
        if len(new["files"]) < 5 or new["stages"] != record["stages"]:
            raise ValueError("Missing Top5 or mutated retrieval stages")
        packets.append(make_packet(queries[record["query_id"]], new["files"][:5], sources))
        display.append(new)
    args.packet_dir.mkdir(parents=True, exist_ok=True)
    write_new(args.packet_dir / "display_results.jsonl", display, True)
    write_new(args.packet_dir / "evidence_packets.jsonl", packets, True)
    write_new(args.packet_dir / "packet_manifest.json", {"status": "complete", "queries": len(packets),
        "source_documents": 9639, "indexed_units": len(units), "weights": [1, 1], "eligible_scoped_units": len(approved),
        "scoped_top5_positions": sum(bool(hit.get("display_only")) for p in packets for hit in p["evidence"]),
        "packet_sha256": sha_file(args.packet_dir / "evidence_packets.jsonl"), "parent_results_sha256": sha_file(args.results),
        "queries_sha256": sha_file(args.queries), "scope_sha256": sha_file(PRIOR / "scope_units.jsonl"), "human_approved": False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    retrieval = commands.add_parser("retrieve")
    retrieval.add_argument("--queries", type=Path, default=OUT / "queries.jsonl")
    retrieval.add_argument("--output", type=Path, default=OUT / "retrieval_results.jsonl")
    retrieval.add_argument("--cache", type=Path, default=WORK / "vector_cache")
    preparation = commands.add_parser("prepare")
    preparation.add_argument("--queries", type=Path, default=OUT / "queries.jsonl")
    preparation.add_argument("--results", type=Path, default=OUT / "retrieval_results.jsonl")
    preparation.add_argument("--packet-dir", type=Path, default=OUT)
    verification = commands.add_parser("verify-judgments")
    verification.add_argument("--packets", type=Path, default=OUT / "evidence_packets.jsonl")
    verification.add_argument("--judgments", type=Path, default=OUT / "model_judgments.jsonl")
    verification.add_argument("--output", type=Path, default=OUT / "judgment_verification.json")
    args = parser.parse_args()
    if args.command == "retrieve":
        retrieve(args)
    elif args.command == "prepare":
        prepare(args)
    else:
        assert_freeze(OUT / "input_freeze.json")
        with DICTIONARY.open(encoding="utf-8-sig", newline="") as stream:
            labels = {row["risk_tag"] for row in csv.DictReader(stream)}
        if len(labels) != 27:
            raise ValueError("Official dictionary is not exactly 27 labels")
        result = validate_judgments(rows(args.packets), rows(args.judgments), labels)
        write_new(args.output, result)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
