"""Compute combination metrics solely from exact same-round cached grades."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from combo_evaluate import E

summary = E.backend.summarize(E.OUT / "queries.jsonl", [E.OUT / "combo_results.jsonl"], E.OUT / "combo_evaluation", [], sources_path=E.backend.SOURCES)
print(json.dumps({k: summary[k] for k in ("status", "queries", "unique_query_file_pairs", "context_variants")}, ensure_ascii=False))
