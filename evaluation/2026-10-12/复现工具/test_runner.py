import json
import math
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import runner


class RetrievalRulesTest(unittest.TestCase):
    def test_rrf_equal_weight_starts_at_one_and_missing_is_zero(self):
        result = runner.rrf([
            [{"unit_id": "a", "score": 999}, {"unit_id": "b", "score": 1}],
            [{"unit_id": "b", "score": -20}, {"unit_id": "c", "score": 10}],
        ])
        scores = {row["unit_id"]: row["score"] for row in result}
        self.assertAlmostEqual(scores["a"], 1 / 61)
        self.assertAlmostEqual(scores["b"], 1 / 62 + 1 / 61)
        self.assertAlmostEqual(scores["c"], 1 / 62)
        self.assertEqual(result[0]["unit_id"], "b")

    def test_rrf_deduplicates_unit_in_each_route(self):
        result = runner.rrf([[{"unit_id": "a"}, {"unit_id": "a"}, {"unit_id": "b"}]])
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0]["score"], 1 / 61)
        self.assertAlmostEqual(result[1]["score"], 1 / 62)

    def test_latest_fix_is_numeric_and_shared_originals_excluded(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            root = Path(folder)
            for name in ["F000001_r0.json", "F000001_r0_fix02.json", "F000001_r0_fix10.json", "other.json"]:
                (root / name).write_text("{}", encoding="utf-8")
            selected = runner.latest_candidates(root)
            self.assertEqual(list(selected), ["F000001"])
            self.assertEqual(selected["F000001"].name, "F000001_r0_fix10.json")

    def test_chunks_exact_span_overlap_and_parent(self):
        source = "首段。\n" + "甲" * 730 + "。\n否认其直接责任。"
        chunks = runner.chunk_spans(source, 300, 40)
        self.assertEqual(chunks[0][0], 0)
        self.assertEqual(chunks[-1][1], len(source))
        for start, end in chunks:
            self.assertLessEqual(end - start, 300)
            self.assertTrue(source[start:end])
        covered = set()
        for start, end in chunks:
            covered.update(range(start, end))
        self.assertEqual(covered, set(range(len(source))))
        self.assertTrue(any(chunks[i][0] < chunks[i - 1][1] for i in range(1, len(chunks))))

    def _fixture(self):
        source = "张某。原文未明确责任层次。\n机构未按规定回访，但已经补充回访。\n若客户同意才可办理。"
        candidate = {
            "file_id": "F000001",
            "cases": [{"local_key": "c1", "party_name": "张某", "party_quote": "张某。", "party_type": "person"}],
            "behaviors": [{"local_key": "b1", "case_key": "c1", "actor_role": "unknown",
                           "finding_quote": "机构未按规定回访，但已经补充回访。", "summary": "虚构推测事实",
                           "risk_tags": [{"tag": "绝对收益", "quotes": ["这是不存在的引文"]}],
                           "conditions": [{"value": "推测性条件", "quote": "若客户同意才可办理。"}],
                           "negations": [{"value": "未直接责任", "quote": "原文未明确责任层次。"}],
                           "exceptions": [], "uncertainties": ["未知"]}],
        }
        return source, candidate

    def test_structured_quotes_are_exact_and_unknown_is_not_direct_responsibility(self):
        source, candidate = self._fixture()
        units, audit = runner.project_document("F000001", source, candidate, "candidate-sha")
        structured = [u for u in units if u["corpus"] == "structured" and u["behavior_id"]]
        self.assertTrue(structured)
        self.assertTrue(any(u["evidence_kind"] == "negation" for u in structured))
        self.assertTrue(any(u["evidence_kind"] == "condition" for u in structured))
        for unit in structured:
            span = unit["source_spans"][0]
            self.assertEqual(unit["source_text"], source[span["start"]:span["end"]])
            self.assertEqual(unit["case_id"], "F000001:c1")
            self.assertNotIn("直接责任", unit["prefix"])
            self.assertIn("责任层次未知", unit["prefix"])
            self.assertNotIn("虚构推测事实", unit["text"])
            self.assertNotIn("绝对收益", unit["text"])
            self.assertNotIn("推测性条件", unit["text"])
            self.assertIn("parent_source_text", unit)
            self.assertIn("parent_source_spans", unit)

    def test_unmatched_quotes_are_audited_and_source_has_no_fake_case(self):
        source, candidate = self._fixture()
        candidate["behaviors"][0]["finding_quote"] = "不存在"
        units, audit = runner.project_document("F000001", source, candidate, "sha")
        self.assertTrue(any(row["quote"] == "不存在" for row in audit))
        fallback = [u for u in units if u["case_id"] == "F000001:SOURCE"]
        self.assertTrue(fallback)
        self.assertTrue(all(u["behavior_id"] is None for u in fallback))

    def test_case_then_file_max_preserves_distinct_parties_and_best_evidence(self):
        units = {}
        for uid, fid, cid in [("a", "F1", "F1:person1"), ("b", "F1", "F1:person2"),
                              ("c", "F1", "F1:person1"), ("d", "F2", "F2:c1"), ("e", "F3", "F3:SOURCE")]:
            units[uid] = dict(unit_id=uid, file_id=fid, case_id=cid, behavior_id="b1", text=uid,
                              prefix="", source_text=uid, source_spans=[dict(start=0, end=1)])
        ranked = [dict(unit_id="a", score=9), dict(unit_id="b", score=8), dict(unit_id="c", score=7),
                  dict(unit_id="d", score=6), dict(unit_id="e", score=5)]
        cases, files = runner.aggregate(ranked, units)
        self.assertEqual([c["case_id"] for c in cases], ["F1:person1", "F1:person2", "F2:c1"])
        self.assertEqual(files[0]["unit_id"], "a")
        self.assertEqual(files[0]["case_ids"], ["F1:person1", "F1:person2"])
        self.assertEqual([f["file_id"] for f in files], ["F1", "F2", "F3"])

    def test_cache_signature_changes_for_order_text_config(self):
        units = [dict(unit_id="a", text="甲"), dict(unit_id="b", text="乙")]
        first = runner.ordered_text_sha(units)
        self.assertNotEqual(first, runner.ordered_text_sha(list(reversed(units))))
        self.assertNotEqual(first, runner.ordered_text_sha([dict(unit_id="a", text="丙"), units[1]]))
        self.assertNotEqual(runner.cache_key(first, {"max_length": 512}), runner.cache_key(first, {"max_length": 256}))

    def test_duplicate_quote_channels_do_not_create_duplicate_units(self):
        source, candidate = self._fixture()
        quote = candidate["behaviors"][0]["finding_quote"]
        candidate["behaviors"][0]["risk_mechanism_quotes"] = [quote]
        candidate["behaviors"][0]["material_function_quotes"] = [quote]
        candidate["coverage"] = [{"behavior_keys": ["b1"], "quote": quote}]
        units, _ = runner.project_document("F000001", source, candidate, "sha")
        matches = [u for u in units if u["behavior_id"] and u["parent_source_text"] == quote]
        self.assertEqual(len(matches), 1)

    def test_early_cli_failure_writes_failed_log_and_never_completed_result(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            root = Path(folder)
            output = root / "results.jsonl"
            with patch("sys.argv", ["runner.py", "--run", "--prepared", str(root / "missing"), "--output", str(output)]):
                with self.assertRaises(FileNotFoundError):
                    runner.main()
            self.assertFalse(output.exists())
            self.assertEqual(runner.read_json(str(output) + ".run.json")["status"], "failed")

    def test_duplicate_original_quote_keeps_all_positions_and_marks_ambiguous(self):
        quote = "未按规定回访。"
        source = "甲机构。" + quote + "\n乙机构。" + quote
        candidate = {"file_id": "F000001", "cases": [
            {"local_key": "c1", "party_quote": "甲机构。"}, {"local_key": "c2", "party_quote": "乙机构。"}],
            "behaviors": [{"local_key": f"b{i}", "case_key": f"c{i}", "actor_role": "institution_violation", "finding_quote": quote} for i in (1, 2)]}
        units, _ = runner.project_document("F000001", source, candidate, "sha")
        matches = [u for u in units if u["behavior_id"]]
        self.assertEqual({u["case_id"] for u in matches}, {"F000001:c1", "F000001:c2"})
        for unit in matches:
            self.assertEqual(len(unit["source_spans"]), 2)
            self.assertTrue(unit["evidence_ambiguous"])
            self.assertIn("subject attribution", unit["ambiguity_reason"])
            for span in unit["source_spans"]:
                self.assertEqual(source[span["start"]:span["end"]], unit["source_text"])

    def test_token_cache_audit_replays_actual_lengths_for_each_unit(self):
        import io
        rows = [dict(stage="embedding", corpus="structured", kind="document", id="u1",
                     input_tokens=700, used_tokens=512, truncated=True, max_length=512)]
        handle = io.StringIO()
        runner.write_token_audit(handle, rows, corpus="raw", cache_hit=True, cache_key="key123")
        replayed = json.loads(handle.getvalue())
        self.assertEqual(replayed["input_tokens"], 700)
        self.assertEqual(replayed["used_tokens"], 512)
        self.assertTrue(replayed["truncated"])
        self.assertTrue(replayed["cache_hit"])
        self.assertEqual(replayed["cache_key"], "key123")
        self.assertEqual(replayed["corpus"], "raw")

    def test_cached_token_audit_rejects_wrong_unit_order(self):
        rows = [dict(id="u2", input_tokens=700, used_tokens=512, truncated=True),
                dict(id="u1", input_tokens=10, used_tokens=10, truncated=False)]
        with self.assertRaises(ValueError):
            runner.validate_token_audit(rows, ["u1", "u2"], 512)

    def test_existing_result_is_rejected_before_model_and_audit_open(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            output = Path(folder) / "results.jsonl"
            output.write_text("existing result", encoding="utf-8")
            audit = Path(str(output) + ".token_audit.jsonl")
            audit.write_text("existing audit", encoding="utf-8")
            with patch.object(runner, "LocalModels") as models:
                with self.assertRaises(FileExistsError):
                    runner.run(SimpleNamespace(output=output))
                models.assert_not_called()
            self.assertEqual(audit.read_text(encoding="utf-8"), "existing audit")

    def test_runner_hash_change_fails_instead_of_claiming_new_version(self):
        with patch.object(runner, "sha_file", return_value="modified"):
            with self.assertRaises(RuntimeError):
                runner.check_runner_hash("started-version")


if __name__ == "__main__":
    unittest.main()
