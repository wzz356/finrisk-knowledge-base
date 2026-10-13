"""Source-only synthetic fixtures for E04 evaluation; no semantic grading."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_ROOT = HERE.parents[1] / "outputs/FinRisk_E04小批量实验_20261012"
sys.path.insert(0, str(HERE))
try:
    import evaluate as E
except ModuleNotFoundError:
    E = None

BODY = "甲机构隐瞒重要条件。乙机构如实说明条件。丙机构另有事项。"


def query(qid="Q1", text="需要核对产品条件", positives=None):
    return {"query_id": qid, "text": text, "group": "boundary",
            "known_positive_file_ids": positives or [],
            "anchor_evidence": [{"file_id": "F1", "quote": "秘密锚点"}],
            "mechanism_description": "核对说明义务", "method": "secret_method"}


def hit(text="甲机构隐瞒重要条件。", fid="F1", rank=1):
    start = BODY.index(text)
    span = {"start": start, "end": start + len(text)}
    return {"file_id": fid, "unit_id": "structured:" + fid + ":U1",
            "rank": rank, "text": text, "prefix": "", "source_text": text,
            "source_spans": [span], "source_segments": [{"span": span, "text": text}],
            "score": 0.75, "method": "secret_method"}


def result(q=None, hits=None, arm="A0"):
    q = q or query()
    return {"query_id": q["query_id"], "text": q["text"], "arm": arm,
            "corpus": "structured", "files": [hit()] if hits is None else hits,
            "timing": {"rerank_seconds": 0.25}, "method": "secret_method"}


def source():
    return {"F1": {"full_text": BODY, "text_sha256": E.text_sha(BODY)}}


def file_judgment(p, grade=2):
    return {"pair_id": p["pair_id"], "help_grade": grade, "help_type": "boundary",
            "mechanism_match": "partial", "conditions_match": "partial",
            "source_quote": "隐瞒重要条件" if grade >= 2 else "",
            "reason": "仅为测试评分数据", "limitations": ["测试夹具"],
            "misleading_risk": False, "contexts": []}


def context_judgment(c, grade=2):
    return {"context_id": c["context_id"], "help_grade": grade,
            "evidence_quote": c["text"] if grade >= 2 else "",
            "reason": "仅为测试片段数据", "misleading_risk": False}


def complete_judgment(p, file_grade=2, context_grade=2):
    j = file_judgment(p, file_grade)
    j["contexts"] = [context_judgment(c, context_grade) for c in p["contexts"]]
    return j


def write_rows(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(E, "evaluation module is not implemented")

    def pool(self, q=None, hits=None):
        q = q or query()
        return E.build_pool({q["query_id"]: q}, [result(q, hits)], source())[0]

    def fixture(self, root):
        qpath, rpath, spath = root / "queries.jsonl", root / "results.jsonl", root / "sources.jsonl"
        write_rows(qpath, [query()])
        write_rows(rpath, [result()])
        write_rows(spath, [{"official_file_id": "F1", "full_text": BODY, "text_sha256": E.text_sha(BODY), "source_sha256": E.text_sha(BODY)}])
        return qpath, rpath, spath

    def test_blind_pool_strips_method_rank_and_known_positives(self):
        q = query(positives=["F1"])
        pool, provenance = E.build_pool({"Q1": q}, [result(q)], source())
        p = next(iter(pool.values()))
        encoded = json.dumps(p, ensure_ascii=False)
        for secret in ("known_positive", "anchor_evidence", "秘密锚点", "secret_method", '"rank"', '"arm"', '"score"', '"unit_id"'):
            self.assertNotIn(secret, encoded)
        self.assertEqual(p["full_source_text"], BODY)
        self.assertEqual(p["contexts"][0]["source_segments"], hit()["source_segments"])
        self.assertEqual(provenance[0]["unit_id"], hit()["unit_id"])
        self.assertEqual(provenance[0]["source_spans"], hit()["source_spans"])

    def test_new_context_cannot_inherit_old_context(self):
        old = self.pool()
        previous = next(iter(old.values()))
        new = self.pool(hits=[hit("乙机构如实说明条件。")])
        cached, log = E.reuse_judgments(new, list(old.values()), [complete_judgment(previous)], origin="old")
        reused = cached[previous["pair_id"]]
        self.assertEqual(reused["help_grade"], 2)
        self.assertEqual(reused["contexts"], [])
        self.assertEqual(log["reused_files"], 1)
        self.assertEqual(log["reused_contexts"], 0)

    def test_different_query_id_cannot_reuse(self):
        old = self.pool()
        p = next(iter(old.values()))
        new = self.pool(query("Q2"))
        cached, _ = E.reuse_judgments(new, list(old.values()), [complete_judgment(p)])
        self.assertEqual(cached, {})

    def test_different_query_text_cannot_reuse(self):
        old = self.pool()
        p = next(iter(old.values()))
        new = self.pool(query(text="另一个判断任务"))
        cached, log = E.reuse_judgments(new, list(old.values()), [complete_judgment(p)])
        self.assertEqual(cached, {})
        self.assertTrue(log["rejected"])

    def test_source_drift_cannot_reuse(self):
        old = self.pool()
        p = next(iter(old.values()))
        changed_source = BODY + "追加原文。"
        new, _ = E.build_pool({"Q1": query()}, [result()], {"F1": {"full_text": changed_source, "text_sha256": E.text_sha(changed_source)}})
        cached, log = E.reuse_judgments(new, list(old.values()), [complete_judgment(p)])
        self.assertEqual(cached, {})
        self.assertTrue(log["rejected"])

    def test_invalid_source_sha_rejected(self):
        bad = source()
        bad["F1"]["text_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA"):
            E.build_pool({"Q1": query()}, [result()], bad)

    def test_actual_source_interval_rejected(self):
        h = hit()
        h["source_spans"][0]["start"] += 1
        with self.assertRaisesRegex(ValueError, "source|span"):
            self.pool(hits=[h])

    def test_source_segments_must_match_full_context(self):
        h = hit()
        h["text"] += "伪造内容"
        with self.assertRaisesRegex(ValueError, "context|text"):
            self.pool(hits=[h])

    def test_forged_file_quote_rejected(self):
        pool = self.pool()
        p = next(iter(pool.values()))
        j = complete_judgment(p)
        j["source_quote"] = "原文没有这句话"
        with self.assertRaisesRegex(ValueError, "quote"):
            E.merge_judgments(pool, {}, [j])

    def test_forged_context_quote_rejected(self):
        pool = self.pool()
        p = next(iter(pool.values()))
        j = complete_judgment(p)
        j["contexts"][0]["evidence_quote"] = "乙机构如实说明条件。"
        with self.assertRaisesRegex(ValueError, "quote"):
            E.merge_judgments(pool, {}, [j])

    def test_positive_grade_requires_exact_quote(self):
        pool = self.pool()
        p = next(iter(pool.values()))
        j = complete_judgment(p)
        j["contexts"][0]["evidence_quote"] = ""
        with self.assertRaisesRegex(ValueError, "quote"):
            E.merge_judgments(pool, {}, [j])

    def test_fixed_five_denominator_and_absent_slots(self):
        q = query(positives=["F1"])
        results = [result(q)]
        pool, _ = E.build_pool({"Q1": q}, results, source())
        p = next(iter(pool.values()))
        validated, remaining, _ = E.merge_judgments(pool, {}, [complete_judgment(p, 3, 2)])
        summary, per_query = E.compute_metrics({"Q1": q}, results, pool, validated)
        a = summary["metrics"][0]
        self.assertEqual(a["top5_denominator"], 5)
        self.assertEqual(a["context_useful_at5"], 0.2)
        self.assertEqual(a["useful_at5"], 0.2)
        self.assertEqual(a["mean_help_at5"], 0.6)
        self.assertEqual(a["context_coverage_at5"], 1)
        self.assertEqual(per_query[0]["absent_top5_slots"], 4)
        self.assertEqual(a["known_source_hit_at5"], 1)
        self.assertEqual(remaining, [])

    def test_no_known_source_is_not_a_miss(self):
        q = query()
        results = [result(q, [])]
        pool, _ = E.build_pool({"Q1": q}, results, source())
        summary, _ = E.compute_metrics({"Q1": q}, results, pool, {})
        self.assertIsNone(summary["metrics"][0]["known_source_hit_at5"])
        self.assertEqual(summary["metrics"][0]["known_source_hit_at5_n"], 0)
        self.assertEqual(summary["metrics"][0]["context_useful_at5"], 0)

    def test_missing_judgment_refuses_complete_metrics(self):
        pool = self.pool()
        with self.assertRaisesRegex(ValueError, "incomplete|missing|coverage"):
            E.compute_metrics({"Q1": query()}, [result()], pool, {})

    def test_missing_context_is_remaining_work(self):
        pool = self.pool()
        p = next(iter(pool.values()))
        validated, remaining, _ = E.merge_judgments(pool, {}, [file_judgment(p)])
        self.assertEqual(len(remaining), 1)
        self.assertTrue(remaining[0]["file_judgment_from_cache"])
        self.assertFalse(remaining[0]["needs_file_judgment"])
        self.assertEqual(remaining[0]["contexts"], p["contexts"])
        with self.assertRaisesRegex(ValueError, "incomplete|coverage"):
            E.compute_metrics({"Q1": query()}, [result()], pool, validated)

    def test_cached_file_context_only_supplement_preserves_old_grade(self):
        pool = self.pool(hits=[hit("乙机构如实说明条件。")])
        p = next(iter(pool.values()))
        old_file = file_judgment(p, 1)
        submission = {"pair_id": p["pair_id"], "contexts": [context_judgment(p["contexts"][0], 3)]}
        merged, remaining, disagreements = E.merge_judgments(pool, {p["pair_id"]: old_file}, [submission])
        self.assertEqual(merged[p["pair_id"]]["help_grade"], 1)
        self.assertEqual(merged[p["pair_id"]]["contexts"][0]["help_grade"], 3)
        self.assertEqual(len(disagreements), 1)
        self.assertEqual(remaining, [])

    def test_cached_file_cannot_be_overwritten(self):
        pool = self.pool()
        p = next(iter(pool.values()))
        with self.assertRaisesRegex(ValueError, "overwrite|cached"):
            E.merge_judgments(pool, {p["pair_id"]: file_judgment(p, 1)}, [complete_judgment(p, 3)])

    def test_multiple_judgment_inputs_merge_disjoint_contexts(self):
        old = self.pool()
        oldp = next(iter(old.values()))
        q = query()
        results = [result(q), result(q, [hit("乙机构如实说明条件。")], "A1")]
        pool, _ = E.build_pool({"Q1": q}, results, source())
        p = next(iter(pool.values()))
        rows = [file_judgment(p)] + [{"pair_id": p["pair_id"], "contexts": [context_judgment(c)]} for c in p["contexts"]]
        merged, remaining, _ = E.merge_judgments(pool, {}, rows)
        self.assertEqual(len(merged[p["pair_id"]]["contexts"]), 2)
        self.assertEqual(remaining, [])

    def test_every_present_arm_must_cover_all_queries(self):
        q2 = query("Q2")
        with self.assertRaisesRegex(ValueError, "cover|query"):
            E.build_pool({"Q1": query(), "Q2": q2}, [result(), result(q2), result(arm="A1")], source())

    def test_output_guard_rejects_original_frozen_directories(self):
        guard = getattr(E, "check_output_dir", None)
        self.assertIsNotNone(guard, "output guard is not implemented")
        with self.assertRaisesRegex(ValueError, "output|实验"):
            guard(E.ROOT / "outputs/FinRisk_知识库V2_20261012/metrics")

    def test_prepare_changed_phase_refuses_overwrite_complete_metrics(self):
        with tempfile.TemporaryDirectory(prefix="e04_eval_test_", dir=TEST_ROOT) as td:
            root = Path(td)
            self.assertTrue(root.resolve().is_relative_to(TEST_ROOT.resolve()))
            qpath, rpath, spath = self.fixture(root)
            out = root / "out"
            E.prepare(qpath, [rpath], out, sources_path=spath)
            p = E.read_rows(out / "blind_judgment_pool.jsonl")[0]
            jpath = root / "judgments.jsonl"
            write_rows(jpath, [complete_judgment(p)])
            E.summarize(qpath, [rpath], out, [jpath], sources_path=spath)
            previous_metrics = (out / "metrics.json").read_bytes()
            previous_judgments = (out / "validated_judgments.jsonl").read_bytes()
            write_rows(rpath, [result(hits=[hit("乙机构如实说明条件。")])])
            with self.assertRaisesRegex(ValueError, "binding|input|SHA"):
                E.prepare(qpath, [rpath], out, sources_path=spath)
            self.assertEqual(previous_metrics, (out / "metrics.json").read_bytes())
            self.assertEqual(previous_judgments, (out / "validated_judgments.jsonl").read_bytes())

    def test_reused_input_drift_rejected_at_summary(self):
        with tempfile.TemporaryDirectory(prefix="e04_eval_test_", dir=TEST_ROOT) as td:
            root = Path(td)
            self.assertTrue(root.resolve().is_relative_to(TEST_ROOT.resolve()))
            qpath, rpath, spath = self.fixture(root)
            old_pool, _ = E.build_pool({"Q1": query()}, [result()], source())
            p = next(iter(old_pool.values()))
            ppath, jpath = root / "old_pool.jsonl", root / "old_judgments.jsonl"
            write_rows(ppath, list(old_pool.values()))
            write_rows(jpath, [complete_judgment(p)])
            out = root / "out"
            E.prepare(qpath, [rpath], out, [ppath], [jpath], sources_path=spath)
            write_rows(jpath, [complete_judgment(p, 3, 3)])
            with self.assertRaisesRegex(ValueError, "reuse|cache|SHA"):
                E.summarize(qpath, [rpath], out, [], sources_path=spath)

    def test_modified_validated_resume_rows_rejected(self):
        with tempfile.TemporaryDirectory(prefix="e04_eval_test_", dir=TEST_ROOT) as td:
            root = Path(td)
            self.assertTrue(root.resolve().is_relative_to(TEST_ROOT.resolve()))
            qpath, rpath, spath = self.fixture(root)
            out = root / "out"
            E.prepare(qpath, [rpath], out, sources_path=spath)
            p = E.read_rows(out / "blind_judgment_pool.jsonl")[0]
            jpath = root / "judgments.jsonl"
            write_rows(jpath, [complete_judgment(p)])
            E.summarize(qpath, [rpath], out, [jpath], sources_path=spath)
            rows = E.read_rows(out / "validated_judgments.jsonl")
            rows[0]["help_grade"] = 3
            write_rows(out / "validated_judgments.jsonl", rows)
            with self.assertRaisesRegex(ValueError, "validated|SHA"):
                E.summarize(qpath, [rpath], out, [], sources_path=spath)

    def test_prepare_and_summarize_cli_resume_idempotently(self):
        with tempfile.TemporaryDirectory(prefix="e04_eval_test_", dir=TEST_ROOT) as td:
            root = Path(td)
            self.assertTrue(root.resolve().is_relative_to(TEST_ROOT.resolve()))
            qpath, rpath, spath = root / "queries.jsonl", root / "results.jsonl", root / "sources.jsonl"
            out = root / "out"
            write_rows(qpath, [query()])
            write_rows(rpath, [result()])
            write_rows(spath, [{"official_file_id": "F1", "full_text": BODY, "text_sha256": E.text_sha(BODY), "source_sha256": E.text_sha(BODY)}])
            manifest = E.prepare(qpath, [rpath], out, sources_path=spath)
            self.assertEqual(manifest["status"], "awaiting_judgments")
            before = (out / "blind_judgment_pool.jsonl").read_bytes()
            E.prepare(qpath, [rpath], out, sources_path=spath)
            self.assertEqual(before, (out / "blind_judgment_pool.jsonl").read_bytes())
            incomplete = E.summarize(qpath, [rpath], out, [], sources_path=spath)
            self.assertEqual(incomplete["status"], "incomplete")
            self.assertEqual(incomplete["metrics"], [])
            p = E.read_rows(out / "blind_judgment_pool.jsonl")[0]
            judgments = root / "judgments.jsonl"
            write_rows(judgments, [complete_judgment(p)])
            finished = E.summarize(qpath, [rpath], out, [judgments], sources_path=spath)
            self.assertEqual(finished["status"], "complete")
            E.prepare(qpath, [rpath], out, sources_path=spath)
            self.assertEqual(E.read_rows(out / "remaining_pool.jsonl"), [])
            for name in ("metrics.json", "metrics.md", "per_query_metrics.jsonl", "validated_judgments.jsonl", "reuse_provenance.json", "remaining_pool.jsonl"):
                self.assertTrue((out / name).exists(), name)
            cli = subprocess.run([sys.executable, "-X", "utf8", "-B", str(HERE / "evaluate.py"), "summarize", "--queries", str(qpath), "--results", str(rpath), "--output-dir", str(out), "--sources", str(spath), "--judgments", str(judgments)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(cli.returncode, 0, cli.stderr)

    def test_output_alias_to_queries_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory(prefix="e04_eval_test_", dir=TEST_ROOT) as td:
            root = Path(td)
            self.assertTrue(root.resolve().is_relative_to(TEST_ROOT.resolve()))
            _, rpath, spath = self.fixture(root)
            out = root / "out"
            out.mkdir()
            qpath = out / "per_query_metrics.jsonl"
            write_rows(qpath, [query()])
            before = qpath.read_bytes()
            with self.assertRaisesRegex(ValueError, "input|alias|output"):
                E.prepare(qpath, [rpath], out, sources_path=spath)
            self.assertEqual(before, qpath.read_bytes())

    def test_unknown_same_named_artifact_rejected(self):
        with tempfile.TemporaryDirectory(prefix="e04_eval_test_", dir=TEST_ROOT) as td:
            root = Path(td)
            self.assertTrue(root.resolve().is_relative_to(TEST_ROOT.resolve()))
            qpath, rpath, spath = self.fixture(root)
            out = root / "out"
            out.mkdir()
            artifact = out / "metrics.json"
            artifact.write_text('{"owner":"other"}', encoding="utf-8")
            before = artifact.read_bytes()
            with self.assertRaisesRegex(ValueError, "artifact|output|manifest"):
                E.prepare(qpath, [rpath], out, sources_path=spath)
            self.assertEqual(before, artifact.read_bytes())

    def test_new_phase_cached_file_only_requests_new_context(self):
        with tempfile.TemporaryDirectory(prefix="e04_eval_test_", dir=TEST_ROOT) as td:
            root = Path(td)
            self.assertTrue(root.resolve().is_relative_to(TEST_ROOT.resolve()))
            qpath, rpath, spath = self.fixture(root)
            old_pool = self.pool()
            p = next(iter(old_pool.values()))
            ppath, jpath = root / "old_pool.jsonl", root / "old_judgments.jsonl"
            write_rows(ppath, list(old_pool.values()))
            write_rows(jpath, [complete_judgment(p)])
            write_rows(rpath, [result(hits=[hit("乙机构如实说明条件。")])])
            out = root / "new_phase"
            m = E.prepare(qpath, [rpath], out, [ppath], [jpath], sources_path=spath)
            self.assertEqual(m["pending_files"], 0)
            self.assertEqual(m["pending_contexts"], 1)
            remaining = E.read_rows(out / "remaining_pool.jsonl")[0]
            self.assertFalse(remaining["needs_file_judgment"])
            self.assertNotIn("cached_file_judgment", remaining)
            self.assertNotIn("help_grade", remaining)
            supplement = root / "supplement.jsonl"
            write_rows(supplement, [{"pair_id": remaining["pair_id"], "contexts": [context_judgment(c) for c in remaining["contexts"]]}])
            m = E.summarize(qpath, [rpath], out, [supplement], sources_path=spath)
            self.assertEqual(m["status"], "complete")

    def test_hardlinked_output_alias_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory(prefix="e04_eval_test_", dir=TEST_ROOT) as td:
            root = Path(td)
            self.assertTrue(root.resolve().is_relative_to(TEST_ROOT.resolve()))
            qpath, rpath, spath = self.fixture(root)
            out = root / "out"
            out.mkdir()
            alias = out / "per_query_metrics.jsonl"
            try:
                alias.hardlink_to(qpath)
            except OSError as exc:
                self.skipTest(f"hardlinks unavailable: {exc}")
            before = qpath.read_bytes()
            with self.assertRaisesRegex(ValueError, "input|alias|output"):
                E.prepare(qpath, [rpath], out, sources_path=spath)
            self.assertEqual(before, qpath.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
