"""Regressions for scoped display, fresh grading and complete five-arm comparison."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    import evaluate as E
except ModuleNotFoundError:
    E = None

SOURCE = "甲机构。其人员承诺合同以外赠品。乙机构存在独立事项。"
RAW = "其人员承诺合同以外赠品。"
ARMS = ("B0", "S1", "C2", "W4", "M3")


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def span(text):
    start = SOURCE.index(text)
    return {"start": start, "end": start + len(text)}


def hit(scoped=False, prefixed=False):
    h = {"file_id": "F1", "unit_id": "U1", "rank": 1, "score": 1., "prefix": "",
         "text": RAW, "source_text": RAW, "source_spans": [span(RAW)],
         "source_segments": [{"text": RAW, "span": span(RAW)}]}
    if scoped:
        body = "甲机构。" + RAW
        h.update(scope_profile="5h-scoped-v1", scope_review_status="approved_model_review",
                 original_unit_text=RAW, original_unit_spans=[span(RAW)], scope_status="scoped",
                 occurrence_ambiguity=False, matched_occurrences=[span(RAW)],
                 source_text=body, source_spans=[span(body)], source_segments=[{"text": body, "span": span(body)}])
        h["text"] = "【命中原话】\n" + RAW + "\n\n【命中原话的对应原文（逐段独立，不合并主体）】\n" + body
        if prefixed:
            claim = {"label": "文书主体", "quote": "甲机构", "span": span("甲机构"), "link_reason": "同段机构身份"}
            h.update(prefix="文书主体：甲机构", prefix_claims=[claim], prefix_review_status="approved_model_review",
                     prefix_source_unit_id="U1")
            h["text"] = "【仅适用于下方命中片段的背景（原文摘录，候选）】\n" + h["prefix"] + "\n\n" + h["text"]
    return h


def query():
    return {"query_id": "N1", "text": "购买合同外赠品的保险需核查什么？", "group": "new_business_risk",
            "query_role": "risk", "replay_origin": "new_business_text_not_human_gold", "expected_help": "SECRET_HINT"}


def results():
    return [{"arm": a, "query_id": "N1", "text": query()["text"], "files": [hit(a in {"S1", "C2"}, a == "C2")], "timing": {}} for a in ARMS]


def judgments(pool):
    return {pid: {"pair_id": pid, "help_grade": 2, "help_type": "support", "mechanism_match": "same",
                  "conditions_match": "compatible", "source_quote": RAW, "reason": "测试机制", "limitations": ["夹具"],
                  "misleading_risk": False, "contexts": [{"context_id": c["context_id"], "help_grade": 2,
                  "evidence_quote": RAW, "reason": "测试原话", "misleading_risk": False} for c in p["contexts"]]}
            for pid, p in pool.items()}


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(E, "five-hour evaluator not implemented")

    def test_old_plain_context_still_valid(self):
        self.assertEqual(E.validate_context(hit(), SOURCE)["text"], RAW)

    def test_scoped_and_prefixed_roundtrip_keep_source(self):
        for prefix in (False, True):
            h = hit(True, prefix)
            c = E.validate_context(h, SOURCE)
            self.assertEqual(c["source_segments"], h["source_segments"])
            self.assertEqual(E.validate_context(c, SOURCE)["text"], h["text"])
            self.assertNotIn("unit_id", c)

    def test_other_subject_segment_does_not_contain_original(self):
        h = hit(True); other = "乙机构存在独立事项。"
        h.update(source_text=other, source_segments=[{"text": other, "span": span(other)}], source_spans=[span(other)])
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)

    def test_fabricated_span_or_display_rejected(self):
        h = hit(True); h["source_segments"][0]["span"]["end"] -= 1
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)
        h = hit(True); h["text"] += "本公司合法"
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)

    def test_missing_scope_approval_rejected(self):
        h = hit(True); h["scope_review_status"] = "pending"
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)

    def test_prefix_quote_and_unit_binding_rejected(self):
        h = hit(True, True); h["prefix_claims"][0]["span"]["start"] += 1
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)
        h = hit(True, True); h["prefix_source_unit_id"] = "OTHER"
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)

    def test_visible_field_label_cannot_be_regulatory_quote(self):
        c = E.validate_context(hit(True, True), SOURCE)
        j = {"context_id": c["context_id"], "help_grade": 2, "evidence_quote": "文书主体：甲机构", "reason": "标签", "misleading_risk": False}
        with self.assertRaises(ValueError): E.validate_context_judgment(j, c, SOURCE)

    def test_blind_pool_removes_author_and_methods(self):
        p, provenance = E.build_pool({"N1": query()}, results(), {"F1": {"full_text": SOURCE, "text_sha256": digest(SOURCE)}})
        encoded = json.dumps(list(p.values()), ensure_ascii=False)
        for marker in ("SECRET_HINT", "query_task", '"arm"', '"rank"', '"unit_id"', '"score"', "prefix_source_unit_id"):
            self.assertNotIn(marker, encoded)
        self.assertEqual(len(provenance), 5)

    def test_missing_arm_is_rejected(self):
        with self.assertRaises(ValueError):
            E.build_pool({"N1": query()}, results()[:-1], {"F1": {"full_text": SOURCE, "text_sha256": digest(SOURCE)}})

    def test_fixed_denominator_and_fresh_strata(self):
        q = {"N1": query()}; rr = results()
        p, _ = E.build_pool(q, rr, {"F1": {"full_text": SOURCE, "text_sha256": digest(SOURCE)}})
        j = judgments(p); summary, _ = E.compute_metrics(q, rr, p, j)
        self.assertTrue(all(a["context_useful_at5"] == .2 for a in summary["metrics"]))
        self.assertEqual(summary["strata"]["new_business"]["queries"], 1)
        broken = copy.deepcopy(j); next(iter(broken.values()))["contexts"].pop()
        with self.assertRaises(ValueError): E.compute_metrics(q, rr, p, broken)

    def test_prepare_missing_then_summarize_complete(self):
        with tempfile.TemporaryDirectory(dir=E.OUT) as directory:
            base = Path(directory)
            def save(name, values):
                p = base / name; p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in values), encoding="utf-8"); return p
            qp = save("q.jsonl", [query()]); rp = save("r.jsonl", results())
            sp = save("s.jsonl", [{"official_file_id": "F1", "full_text": SOURCE, "text_sha256": digest(SOURCE), "source_sha256": digest(SOURCE)}])
            phase = base / "phase"
            prepared = E.prepare(qp, [rp], phase, sources_path=sp)
            self.assertEqual(prepared["reused_files"], 0)
            self.assertEqual(E.summarize(qp, [rp], phase, [], sources_path=sp)["status"], "incomplete")
            p = E.validate_pool(E.read_rows(phase / "blind_judgment_pool.jsonl"))
            jp = save("j.jsonl", judgments(p).values())
            self.assertEqual(E.summarize(qp, [rp], phase, [jp], sources_path=sp)["status"], "complete")


if __name__ == "__main__":
    unittest.main()
