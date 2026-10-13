"""Independent, source-only preparation and validation for E04 confirmation inputs.

Permitted reads are limited to normalized documents.full_text plus the prior
queries' anchor_evidence / known_positive_file_ids. No experiment output is read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS = ROOT / "outputs/FinRisk_知识库V2_20261012/normalized_final/data/documents.jsonl"
OLD_QUERIES = ROOT / "outputs/FinRisk_召回实验_20261012/queries.jsonl"
OUT = ROOT / "outputs/FinRisk_E04小批量实验_20261012"


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_allowed() -> tuple[list[dict], list[str], int]:
    excluded = set()
    old_count = 0
    with OLD_QUERIES.open(encoding="utf-8-sig") as stream:
        for line in stream:
            old_count += 1
            row = json.loads(line)
            # The old query wording and any other fields are never accessed.
            for anchor in row.get("anchor_evidence", []):
                if anchor.get("file_id"):
                    excluded.add(anchor["file_id"])
            for file_id in row.get("known_positive_file_ids", []):
                excluded.add(file_id)
    docs = []
    with DOCUMENTS.open(encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            full_text = row.get("full_text")
            if not isinstance(full_text, str) or not full_text:
                continue
            # Candidate tags and extraction judgments are never used.
            docs.append({
                "file_id": row["official_file_id"],
                "source_id": row["source_id"],
                "line_number": line_number,
                "full_text": full_text,
            })
    assert len(docs) == 9639, f"Unexpected permitted full_text count: {len(docs)}"
    assert old_count == 50, f"Unexpected prior query count: {old_count}"
    return docs, sorted(excluded), old_count


QUERY_PATH = OUT / "confirmation_queries.jsonl"
MANIFEST_PATH = OUT / "confirmation_source_manifest.json"
NOTES_PATH = OUT / "confirmation_design_notes.md"


def load_authored_queries() -> list[dict]:
    with QUERY_PATH.open(encoding="utf-8-sig") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def make_manifest(docs: list[dict], exclusions: list[str], old_count: int) -> dict:
    queries = load_authored_queries()
    by_id = {doc["file_id"]: doc for doc in docs}
    excluded = set(exclusions)
    old_hashes = {sha_text(by_id[file_id]["full_text"])
                  for file_id in exclusions if file_id in by_id}
    records = []
    source_ids = []
    selected_lines = []
    all_quotes = 0
    for query in queries:
        reference_ids = sorted({anchor["file_id"] for anchor in query["anchor_evidence"]})
        assert len(reference_ids) == 1, (query["query_id"], reference_ids)
        source = by_id[reference_ids[0]]
        assert source["file_id"] not in excluded
        assert sha_text(source["full_text"]) not in old_hashes
        source_ids.append(source["file_id"])
        selected_lines.append(source["line_number"])
        quotes = []
        for anchor in query["anchor_evidence"]:
            quote = anchor["quote"]
            assert quote and quote in source["full_text"], (query["query_id"], "non-exact quote")
            start = source["full_text"].index(quote)
            quotes.append({"quote_sha256_utf8": sha_text(quote),
                           "quote_character_span_zero_based_half_open": [start, start + len(quote)],
                           "quote_character_length": len(quote),
                           "exact_contiguous_match": True})
            all_quotes += 1
        records.append({
            "query_id": query["query_id"], "query_text_sha256_utf8": sha_text(query["text"]),
            "group": query["group"], "query_role": query["query_role"],
            "reference_source_file_ids": reference_ids,
            "reference_role": ("boundary_condition_reference_not_hard_positive"
                               if query["query_role"] == "boundary" else "helpful_risk_case_reference_not_exhaustive_gold"),
            "source_id": source["source_id"],
            "documents_jsonl_line_one_based": source["line_number"],
            "original_full_text_sha256_utf8": sha_text(source["full_text"]),
            "original_full_text_character_length": len(source["full_text"]),
            "full_text_read_before_synthesis": True,
            "selection_basis": query["mechanism_description"],
            "condition_comparison": query["distinguishing_conditions"],
            "quote_verification": quotes,
        })
    assert len(source_ids) == len(set(source_ids)) == 10
    return {
        "manifest_version": 1,
        "prepared_date": "2026-10-12",
        "purpose": "Independently check whether actual Top5 contexts from BM25+BGE -> RRF -> rerank help risk judgment; not source extraction accuracy.",
        "authorship": {"method": "language_model_synthetic_business_paraphrase",
                       "model_identity": "Current Codex session model; exact model identifier not recorded",
                       "human_user_inputs": False, "official_test_gold": False,
                       "model_generation_and_scoring_common_bias": True},
        "permitted_inputs": {
            "full_text_source": str(DOCUMENTS.relative_to(ROOT)).replace("\\", "/"),
            "allowed_full_text_count": len(docs),
            "documents_jsonl_file_sha256": hashlib.sha256(DOCUMENTS.read_bytes()).hexdigest(),
            "old_queries_file": str(OLD_QUERIES.relative_to(ROOT)).replace("\\", "/"),
            "old_query_count": old_count,
            "old_query_fields_accessed": ["anchor_evidence[].file_id", "known_positive_file_ids"],
        },
        "old_anchor_source_exclusion": {
            "excluded_source_count": len(exclusions), "excluded_file_ids": exclusions,
            "canonicalization": "Sorted unique file-ID list; UTF-8 JSON; ensure_ascii=false; separators=(comma,colon)",
            "excluded_source_set_sha256": sha_text(canonical(exclusions)),
            "selected_source_file_id_overlap_count": len(set(source_ids) & excluded),
            "selected_source_exact_full_text_hash_overlap_count": 0,
        },
        "source_interval": {
            "permitted_corpus_document_lines_one_based_inclusive": [1, len(docs)],
            "permitted_corpus_file_id_min_max": [min(by_id), max(by_id)],
            "selected_document_lines_one_based_min_max": [min(selected_lines), max(selected_lines)],
            "selected_file_id_min_max": [min(source_ids), max(source_ids)],
            "interpretation": "Min/max ranges describe provenance only; exact selected IDs and individual line numbers are below, with gaps allowed.",
        },
        "selection_method": {
            "basis": "Directed qualitative selection from full_text facts after excluding all prior anchor/known-positive sources; final source texts read in full.",
            "full_text_search_terms_used": ["保险合同.*以外|合同外", "利益", "说明|告知", "销售|投保", "虚构", "中介|手续费", "承诺", "收益", "免责", "说明", "虚假理赔|虚构.*事故", "农业", "虚假|不真实", "中介", "洗车券"],
            "sampling": "Non-random, mechanism-coverage-directed small sample",
            "candidate_tag_values_used": False,
            "experiment_selection_or_ranking_or_metrics_used": False,
            "reserved_360_sources_read": False,
            "original_teaching_material_or_competition_test_or_answers_read": False,
            "environment_secret_files_read": False,
            "gpu_called": False,
        },
        "query_counts": {"total": len(queries), "risk": 6, "boundary": 4,
                         "marketing_sales_risk": 4, "other_insurance_operations_risk": 2,
                         "unique_reference_sources": len(set(source_ids))},
        "reference_file_ids_in_query_order": source_ids,
        "reference_source_ids_in_query_order": [by_id[file_id]["source_id"] for file_id in source_ids],
        "query_records": records,
        "verification": {"all_quotes_exact_contiguous_original_full_text": True,
                         "quote_count": all_quotes, "query_ids": [query["query_id"] for query in queries],
                         "all_boundary_known_positive_file_ids_empty": True,
                         "no_query_title_case_number_party_product_proper_name_clues": "Manual wording review completed",
                         "no_paid_or_secret_material_in_final_outputs": "Necessary public case excerpts only; no full-text attachments or identity/address/payment-account fields"},
        "artifacts": {"confirmation_queries_jsonl_sha256": hashlib.sha256(QUERY_PATH.read_bytes()).hexdigest(),
                      "confirmation_design_notes_md_sha256": hashlib.sha256(NOTES_PATH.read_bytes()).hexdigest()},
        "limitations": [
            "10 synthetic inputs are a small directed sample, not human-user or official test gold.",
            "Source file disjointness does not guarantee semantic mechanism independence.",
            "Risk references are non-exhaustive; a source hit alone does not prove helpful actual Top5 context.",
            "Boundary references support condition comparisons only, never whole-input automatic compliance or violation.",
            "Shared model generation and later model scoring can introduce correlated bias; no statistical significance or generalization claim is supported.",
        ],
    }


def validate(docs: list[dict], exclusions: list[str], old_count: int) -> None:
    queries = load_authored_queries()
    expected_ids = [f"C{n:03d}" for n in range(1, 11)]
    assert [query["query_id"] for query in queries] == expected_ids
    fields = {"query_id", "text", "group", "query_role", "mechanism_description",
              "relevant_conditions", "distinguishing_conditions", "known_positive_file_ids",
              "anchor_evidence", "query_type", "expected_help"}
    role_counts = {}
    groups = {}
    for query in queries:
        assert set(query) == fields, (query["query_id"], "fields")
        assert query["query_type"] == "new_source_synthetic_business_paraphrase"
        assert 1 <= len(re.findall(r"[。！？]", query["text"])) <= 2
        assert not re.search(r"F\d{6}|〔|〕|罚决|保监罚", query["text"])
        assert all(query[field] for field in ["text", "mechanism_description", "relevant_conditions",
                                              "distinguishing_conditions", "anchor_evidence", "expected_help"])
        role_counts[query["query_role"]] = role_counts.get(query["query_role"], 0) + 1
        groups[query["group"]] = groups.get(query["group"], 0) + 1
        if query["query_role"] == "boundary":
            assert query["known_positive_file_ids"] == []
        else:
            assert query["known_positive_file_ids"] == [query["anchor_evidence"][0]["file_id"]]
    assert role_counts == {"risk": 6, "boundary": 4}
    assert groups == {"marketing_sales": 4, "other_insurance_operations": 2, "boundary_condition_change": 4}
    computed = make_manifest(docs, exclusions, old_count)
    saved = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    assert computed == saved, "Saved manifest differs from freshly computed provenance"
    print(canonical({"validation": "passed", "queries": len(queries), "roles": role_counts,
                     "groups": groups, "unique_sources": 10,
                     "old_source_overlap": 0, "old_exact_full_text_hash_overlap": 0,
                     "exact_quote_matches": computed["verification"]["quote_count"],
                     "artifact_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                         for path in [QUERY_PATH, MANIFEST_PATH, NOTES_PATH]}}))


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["inventory", "search", "read", "manifest", "validate"])
    parser.add_argument("terms", nargs="*")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()
    docs, exclusions, old_count = load_allowed()
    excluded = set(exclusions)
    by_id = {doc["file_id"]: doc for doc in docs}
    if args.mode == "inventory":
        print(canonical({"allowed_full_text_count": len(docs), "old_query_count": old_count,
                         "excluded_source_count": len(exclusions),
                         "excluded_source_set_sha256": sha_text(canonical(exclusions)),
                         "first_id": docs[0]["file_id"], "last_id": docs[-1]["file_id"]}))
    elif args.mode == "search":
        patterns = [re.compile(term) for term in args.terms]
        matches = [doc for doc in docs if doc["file_id"] not in excluded
                   and all(pattern.search(doc["full_text"]) for pattern in patterns)]
        print(canonical({"matching_count": len(matches), "offset": args.offset}))
        for doc in matches[args.offset:args.offset+args.limit]:
            text = doc["full_text"]
            snippets = []
            for pattern in patterns:
                match = pattern.search(text)
                snippets.append(text[max(0, match.start()-50): min(len(text), match.end()+160)])
            print(canonical({"file_id": doc["file_id"], "line": doc["line_number"],
                             "length": len(text), "snippets": snippets}))
    elif args.mode == "read":
        for file_id in args.terms:
            assert file_id not in excluded, f"Prior source forbidden: {file_id}"
            doc = by_id[file_id]
            print(canonical({"file_id": file_id, "line": doc["line_number"],
                             "length": len(doc["full_text"]),
                             "full_text": doc["full_text"]}))
    elif args.mode == "manifest":
        # Prints only: artifact writes are performed explicitly by the caller.
        print(json.dumps(make_manifest(docs, exclusions, old_count), ensure_ascii=False, indent=2))
    else:
        validate(docs, exclusions, old_count)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run()
