import copy
import unittest

try:
    import demo
except ModuleNotFoundError:
    demo = None


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(demo, "Demo implementation not available yet")
        source = "甲公司承诺合同外现金返还。乙公司仅说明合同。"
        self.sources = {"F1": source}
        self.unit = {"unit_id": "u1", "file_id": "F1", "text": "合同外现金返还"}
        self.scope = {"u1": {"segments": [{"text": source[:13], "span": {"start": 0, "end": 13}}],
                             "indexed_text": source[:13], "prefix_text": "", "source_sha256": demo.sha_text(source),
                             "scope_status": "scoped", "scope_reason": "独立主体行"}}
        self.hit = {"unit_id": "u1", "file_id": "F1", "indexed_text": self.unit["text"],
                    "text": self.unit["text"], "source_spans": [{"start": 5, "end": 12}],
                    "source_segments": [{"text": self.unit["text"], "span": {"start": 5, "end": 12}}],
                    "rank": 1, "score": 3.5, "semantic_status": "candidate", "human_review_status": "pending"}
        self.query = {"query_id": "D1", "text": "销售员承诺合同外现金。"}

    def packet_and_judgment(self):
        packet = demo.make_packet(self.query, [self.hit], self.sources)
        judgment = {"query_id": "D1", "input_sha256": packet["input_sha256"],
                    "packet_sha256": demo.sha_json(packet), "origin": "current_session_model",
                    "human_approved": False, "decision": "risk_detected",
                    "risk_labels": [{"risk_tag": "合同外利益", "certainty": "likely", "input_quote": "合同外现金",
                                     "evidence_file_ids": ["F1"], "limitations": "金额待核"}],
                    "reason": "输入与案例机制相近", "missing_information": ["现金金额"], "boundary_notes": [],
                    "evidence_assessments": [{"file_id": "F1", "unit_id": "u1", "rank": 1,
                                              "relation": "direct", "helpful": True,
                                              "quote": "合同外现金返还", "reason": "有合同外现金机制", "warnings": []}]}
        return packet, judgment

    def test_scope_preserves_model_rank_fields(self):
        new = demo.scoped_hit(self.hit, {"u1": self.unit}, self.scope, self.sources)
        for key in ["unit_id", "file_id", "rank", "score", "indexed_text"]:
            self.assertEqual(self.hit[key], new[key])
        self.assertIn("命中原话", new["text"])
        self.assertTrue(new["display_only"])

    def test_unreviewed_hit_unchanged(self):
        self.assertEqual(demo.scoped_hit(self.hit, {"u1": self.unit}, {}, self.sources), self.hit)

    def test_bad_source_span_rejected(self):
        bad = copy.deepcopy(self.hit)
        bad["source_segments"][0]["span"]["start"] = 0
        with self.assertRaises(ValueError):
            demo.make_packet(self.query, [bad], self.sources)

    def test_valid_judgment_passes(self):
        packet, judgment = self.packet_and_judgment()
        self.assertEqual(demo.validate_judgments([packet], [judgment], {"合同外利益"})["judgments"], 1)

    def test_missing_judgment_rejected(self):
        packet, _ = self.packet_and_judgment()
        with self.assertRaises(ValueError):
            demo.validate_judgments([packet], [], {"合同外利益"})

    def test_unknown_label_rejected(self):
        packet, judgment = self.packet_and_judgment()
        judgment["risk_labels"][0]["risk_tag"] = "自创标签"
        with self.assertRaises(ValueError):
            demo.validate_judgments([packet], [judgment], {"合同外利益"})

    def test_unshown_quote_rejected(self):
        packet, judgment = self.packet_and_judgment()
        judgment["evidence_assessments"][0]["quote"] = "乙公司仅说明合同"
        with self.assertRaises(ValueError):
            demo.validate_judgments([packet], [judgment], {"合同外利益"})

    def test_fake_human_approval_rejected(self):
        packet, judgment = self.packet_and_judgment()
        judgment["human_approved"] = True
        with self.assertRaises(ValueError):
            demo.validate_judgments([packet], [judgment], {"合同外利益"})

    def test_duplicate_evidence_rejected(self):
        packet, judgment = self.packet_and_judgment()
        judgment["evidence_assessments"].append(copy.deepcopy(judgment["evidence_assessments"][0]))
        with self.assertRaises(ValueError):
            demo.validate_judgments([packet], [judgment], {"合同外利益"})


if __name__ == "__main__":
    unittest.main()
