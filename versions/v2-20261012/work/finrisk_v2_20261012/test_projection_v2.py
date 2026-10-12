"""Local regression tests; the optional baseline imports the unchanged V1 runner."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
MODULE = (HERE.parent / "finrisk_retrieval_20261012" / "runner.py"
          if os.environ.get("FINRISK_PROJECTION_BASELINE") == "1"
          else HERE / "projection_v2.py")
SPEC = importlib.util.spec_from_file_location("projection_under_test", MODULE)
projection = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(projection)


def draft_for(source_quote, *, count=1, party="甲机构。", role="unknown"):
    return {
        "file_id": "F000001", "semantic_status": "candidate", "human_review_status": "pending",
        "cases": [{"local_key": f"c{i}", "party_quote": party} for i in range(count)],
        "behaviors": [{"local_key": f"b{i}", "case_key": f"c{i}", "actor_role": role,
                       "finding_quote": source_quote} for i in range(count)], "coverage": [],
    }


def project(source, draft, size=300, overlap=40):
    return projection.project_document("F000001", source, draft, "candidate-sha", size, overlap)


def evidence(units):
    return [u for u in units if u["corpus"] == "structured" and u.get("behavior_id")]


def public_pair(file_id):
    """Read only explicitly allowed public regression files via their index locators."""
    root = WORKSPACE / "finrisk-knowledge-base"
    with (root / "data/file_index.jsonl").open(encoding="utf-8") as handle:
        index = next(json.loads(line) for line in handle if json.loads(line)["file_id"] == file_id)
    result = []
    for field in ("source", "candidate"):
        locator = index[field]
        with (root / locator["path"]).open(encoding="utf-8") as handle:
            row = next(json.loads(line) for number, line in enumerate(handle, 1)
                       if number == locator["line"])
        if row["file_id"] != file_id:
            raise AssertionError("Public shard locator does not identify requested file")
        result.append(row)
    return result[0]["full_text"], result[1]["draft"], index["original_candidate_sha256"]


class ProjectionV2Test(unittest.TestCase):
    def nullable_project(self, source, draft):
        try:
            return project(source, draft)
        except TypeError as error:
            self.fail(f"Legacy explicit null quote metadata must not crash traversal: {error}")

    def assert_roundtrip(self, source, unit):
        for span in unit["source_spans"]:
            self.assertEqual(source[span["start"]:span["end"]], unit["source_text"])
        self.assertEqual("".join(source[s["start"]:s["end"]] for s in unit["context_spans"]),
                         unit["context_source_text"])
        self.assertIn("context_segments", unit)
        self.assertEqual([segment["span"] for segment in unit["context_segments"]], unit["context_spans"])
        for segment in unit["context_segments"]:
            span = segment["span"]
            self.assertEqual(segment["text"], source[span["start"]:span["end"]])
        if len(unit["context_spans"]) == 1:
            self.assertEqual(unit["context_text"], unit["context_source_text"])

    def test_unrelated_finding_never_prefixes_punishment(self):
        finding = "费用用于银行渠道开拓和关系维护。"
        penalty = "对未取得展业证开展业务的行为罚款。"
        source = "甲机构。\n" + finding + "\n" + penalty
        draft = draft_for(finding)
        draft["behaviors"][0]["factor_values"] = [{"quote": penalty, "value": "推测标签"}]
        units, _ = project(source, draft)
        rows = [u for u in evidence(units) if penalty in u["source_text"]]
        self.assertTrue(rows)
        self.assertTrue(all(finding not in u["text"] for u in rows))
        self.assertTrue(all(not u["prefix"] for u in rows))

    def test_same_body_indexes_once_across_twenty_five_behaviors(self):
        quote = "未按规定进行客户回访。"
        source = "甲机构。\n" + quote
        units, _ = project(source, draft_for(quote, count=25))
        rows = [u for u in evidence(units) if u["source_text"] == quote]
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]["case_ids"]), 25)
        self.assertEqual(len(rows[0]["behavior_ids"]), 25)
        self.assertEqual(len(rows[0]["associations"]), 25)

    def test_repeated_quote_merges_all_positions_without_proving_actor(self):
        quote = "未按规定进行客户回访。"
        source = "甲机构。\n" + quote + "\n乙机构。\n" + quote
        draft = draft_for(quote, count=2)
        draft["cases"][1]["party_quote"] = "乙机构。"
        units, audit = project(source, draft)
        rows = [u for u in evidence(units) if u["source_text"] == quote]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(len(row["source_spans"]), 2)
        self.assertEqual(set(row["case_ids"]), {"F000001:c0", "F000001:c1"})
        self.assertTrue(row["evidence_ambiguous"])
        self.assertIn("subject attribution", row["ambiguity_reason"])
        self.assertTrue(any(a["reason"] == "multiple_exact_occurrences" for a in audit))
        self.assert_roundtrip(source, row)

    def test_claim_keeps_full_adjacent_regulatory_response(self):
        claim = "甲机构申辩：金额无法准确计量，已经整改，请求减免处罚。"
        response = "对上述陈述申辩意见，我会认为：费用能够可靠计量。整改不足以减轻处罚，申辩不予采纳。"
        source = "甲机构。\n" + claim + "\n" + response + "\n综上，决定罚款。"
        units, _ = project(source, draft_for("金额无法准确计量"))
        rows = [u for u in evidence(units) if "金额无法准确计量" in u["source_text"]]
        self.assertTrue(rows)
        for row in rows:
            self.assertIn(claim, row.get("context_text", ""))
            self.assertIn(response, row.get("context_text", ""))
            self.assert_roundtrip(source, row)

    def test_soft_wrapped_condition_and_table_keep_original_parent(self):
        parent = "办理条件\n项目\t适用限制\n销售\t仅当客户\n同意且资料齐全时才可办理，否则不得办理。"
        source = "甲机构。\n\n" + parent + "\n\n另一事项。"
        units, _ = project(source, draft_for("仅当客户\n同意"))
        rows = [u for u in evidence(units) if "仅当客户" in u["source_text"]]
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row.get("context_text"), parent)
            self.assertIn("否则不得办理", row["context_text"])
            self.assert_roundtrip(source, row)

    def test_long_parent_never_enters_short_model_text(self):
        parent = "若满足条件，" + "需核实资料，" * 110 + "才可办理，否则不得办理。"
        source = "甲机构。\n" + parent
        units, _ = project(source, draft_for(parent), 120, 20)
        rows = evidence(units)
        self.assertGreater(len(rows), 1)
        for row in rows:
            self.assertLessEqual(len(row["text"]), 120)
            self.assertEqual(row.get("context_text"), parent)
            self.assertTrue(row["evidence_ambiguous"])
            self.assertIn("long_parent", row["ambiguity_reason"])
            self.assert_roundtrip(source, row)

    def test_punctuated_table_rows_remain_one_parent(self):
        parent = "条件表\n条件\t办理限制。\n同意\t才可办理。\n不同意\t不得办理。"
        source = "甲机构。\n\n" + parent + "\n\n另一事项。"
        units, _ = project(source, draft_for("同意\t才可办理。"))
        rows = [u for u in evidence(units) if "同意\t才可办理。" in u["source_text"]]
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row["context_text"], parent)
            self.assert_roundtrip(source, row)

    def test_disjoint_repeated_contexts_keep_separate_source_blocks(self):
        quote = "不得隐瞒风险。"
        source = "甲机构。\n" + quote + "\n其他机构的无关事项。\n乙机构。\n" + quote
        units, _ = project(source, draft_for(quote, count=2))
        rows = [u for u in evidence(units) if u["source_text"] == quote]
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]["context_spans"]), 2)
        self.assertTrue(rows[0]["context_ambiguous"])
        self.assertNotIn("无关事项", rows[0]["context_text"])
        self.assertIn("\n\n[原文间隔，分段摘录]\n\n", rows[0]["context_text"])
        self.assertEqual(rows[0]["context_source_text"], quote + quote)
        self.assertNotEqual(rows[0]["context_text"], quote + quote)
        self.assert_roundtrip(source, rows[0])

    def test_unknown_role_and_labels_stay_out_of_text(self):
        quote = "原文未明确张某责任层次。"
        source = "甲机构。\n" + quote
        draft = draft_for(quote)
        draft["behaviors"][0].update(summary="虚构直接实施", risk_tags=[{"tag": "绝对收益"}],
                                    conditions=[{"quote": quote, "value": "虚构条件值"}])
        units, _ = project(source, draft)
        for row in evidence(units):
            self.assertNotIn("直接实施", row["text"])
            self.assertNotIn("绝对收益", row["text"])
            self.assertNotIn("虚构条件值", row["text"])
            self.assertIn("associations", row)
            self.assertTrue(all(a["actor_role"] == "unknown" for a in row["associations"]))

    def test_unmatched_quotes_audited_raw_fallback_has_no_case(self):
        draft = draft_for("不存在的原文")
        original = copy.deepcopy(draft)
        units, audit = project("甲机构。\n机构未按规定回访。", draft)
        self.assertEqual(draft, original)
        self.assertTrue(any(a["reason"] == "not_exact_source_substring" for a in audit))
        raw = [u for u in units if u["corpus"] == "raw"]
        self.assertTrue(raw)
        self.assertTrue(all(u.get("case_ids") == [] and u.get("behavior_ids") == [] for u in raw))
        self.assertTrue(all(u["case_id"] == "F000001:SOURCE" and u["behavior_id"] is None for u in raw))

    def test_protocol_dedup_roundtrip_and_candidate_status_preserved(self):
        source = "甲机构。\n若客户同意才可办理。\n原文未明确责任层次。"
        draft = draft_for("若客户同意才可办理。")
        draft["behaviors"][0]["negations"] = [{"quote": "原文未明确责任层次。"}]
        units, _ = project(source, draft)
        required = {"unit_id", "corpus", "file_id", "case_id", "behavior_id", "evidence_kind", "text",
                    "prefix", "source_text", "source_spans", "parent_span", "evidence_ambiguous",
                    "ambiguity_reason", "prefix_evidence_ambiguous", "candidate_sha256", "case_ids",
                    "behavior_ids", "associations", "context_text", "context_source_text", "context_spans"}
        self.assertEqual(len({u["unit_id"] for u in units}), len(units))
        self.assertEqual(len({(u["corpus"], u["source_text"]) for u in units}), len(units))
        for unit in units:
            self.assertFalse(required - unit.keys())
            self.assertEqual(unit["semantic_status"], "candidate")
            self.assertEqual(unit["human_review_status"], "pending")
            self.assertEqual(unit["candidate_sha256"], "candidate-sha")
            self.assert_roundtrip(source, unit)

    def test_invalid_references_and_chunk_parameters_rejected(self):
        draft = draft_for("甲机构。")
        with self.assertRaises(ValueError):
            project("甲机构。", draft, 40, 40)
        draft["behaviors"][0]["case_key"] = "missing"
        with self.assertRaises(ValueError):
            project("甲机构。", draft)

    def test_response_plain_authority_continuation_keeps_rejection(self):
        related = "甲机构申辩：已经整改。\n对上述申辩意见，本局认为仍构成违法。\n本局不予采纳其减免请求。"
        source = "甲机构。\n" + related + "\n综上，决定罚款。\n另一个案件的事实。"
        units, _ = project(source, draft_for("已经整改", party="甲机构"))
        rows = [u for u in evidence(units) if u["source_text"] == "已经整改"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["context_text"], related)
        self.assertNotIn("决定罚款", rows[0]["context_text"])
        self.assert_roundtrip(source, rows[0])

    def test_claim_complete_sentence_continuation_keeps_response(self):
        related = "甲机构申辩：已经整改。\n其请求减免处罚。\n对上述申辩意见，本局不予采纳。"
        source = "甲机构。\n" + related + "\n综上，决定罚款。"
        units, _ = project(source, draft_for("已经整改", party="甲机构"))
        rows = [u for u in evidence(units) if u["source_text"] == "已经整改"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["context_text"], related)
        self.assert_roundtrip(source, rows[0])

    def test_enumerated_table_keeps_negation_and_stops_at_external_section(self):
        table = "条件\t办理限制。\n一、客户同意\t才可办理。\n二、资料缺失\t不得办理。"
        source = "甲机构。\n\n" + table + "\n三、其他事项\n其他事项允许办理。"
        units, _ = project(source, draft_for("才可办理", party="甲机构"))
        rows = [u for u in evidence(units) if u["source_text"] == "才可办理"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["context_text"], table)
        self.assertNotIn("其他事项", rows[0]["context_text"])
        self.assert_roundtrip(source, rows[0])

    def test_many_short_context_blocks_mark_total_display_length(self):
        quote = "不得隐瞒风险。"
        source = "甲机构。\n" + "\n无关段落。\n".join([quote] * 50)
        units, _ = project(source, draft_for(quote, party="甲机构"))
        row = next(u for u in evidence(units) if u["source_text"] == quote)
        self.assertEqual(len(row["context_segments"]), 50)
        self.assertGreater(len(row["context_source_text"]), 300)
        self.assertTrue(row["context_long"])
        self.assertIn("long_parent", row["ambiguity_reason"])
        self.assert_roundtrip(source, row)

    def test_repeated_party_positions_mark_attribution_ambiguity(self):
        quote = "未按规定回访。"
        source = "甲机构。\n" + quote + "\n乙机构与甲机构另有合作。"
        units, _ = project(source, draft_for(quote, party="甲机构"))
        row = next(u for u in evidence(units) if u["source_text"] == quote)
        association = row["associations"][0]
        self.assertEqual(len(association["party_source_spans"]), 2)
        self.assertTrue(association["source_position_ambiguous"])
        self.assertTrue(association.get("party_position_ambiguous"))
        self.assertFalse(association.get("quote_position_ambiguous"))
        self.assertTrue(row["evidence_ambiguous"])
        self.assertIn("party", row["ambiguity_reason"])
        self.assertEqual(association["actor_role"], "unknown")
        self.assert_roundtrip(source, row)

    def test_finding_returns_separate_same_behavior_qualifiers(self):
        finding = "可以办理业务。"
        condition = "仅当客户同意且资料齐全时才可办理。"
        negation = "资料缺失时不得办理。"
        exception = "紧急情形另有规定的除外。"
        source = "甲机构。\n" + finding + "\n无关事项。\n" + condition + "\n说明事项。\n" + negation + "\n其他事项。\n" + exception
        draft = draft_for(finding, party="甲机构")
        draft["behaviors"][0].update(conditions=[{"quote": condition, "value": "不能输出的值"}],
                                    negations=[{"quote": negation}], exceptions=[{"quote": exception}])
        units, _ = project(source, draft)
        row = next(u for u in evidence(units) if u["source_text"] == finding)
        self.assertEqual(row["text"], finding)
        for qualifier in (condition, negation, exception):
            self.assertIn(qualifier, row["context_text"])
        self.assertNotIn("无关事项", row["context_text"])
        self.assertNotIn("不能输出的值", row["context_text"])
        self.assertIn("[原文间隔，分段摘录]", row["context_text"])
        self.assertEqual(len(row["context_segments"]), 4)
        self.assertEqual(row["qualifier_quotes"], {"conditions": [condition], "negations": [negation], "exceptions": [exception]})
        self.assert_roundtrip(source, row)

    def test_shared_finding_keeps_each_bound_qualifier_without_other_behavior(self):
        finding = "可以办理业务。"
        condition_a, condition_b, unrelated = "仅限客户同意时办理。", "资料缺失不得办理。", "其他行为的条件。"
        source = "甲机构。\n" + finding + "\n隔断事实。\n" + condition_a + "\n隔断事实。\n" + condition_b + "\n另一行为。\n" + unrelated
        draft = draft_for(finding, count=2, party="甲机构")
        draft["behaviors"][0]["conditions"] = [{"quote": condition_a}]
        draft["behaviors"][1]["negations"] = [{"quote": condition_b}]
        draft["behaviors"].append({"local_key": "b_other", "case_key": "c0", "actor_role": "unknown",
                                   "finding_quote": "另一行为。", "conditions": [{"quote": unrelated}]})
        units, _ = project(source, draft)
        row = next(u for u in evidence(units) if u["source_text"] == finding)
        self.assertIn(condition_a, row["context_text"])
        self.assertIn(condition_b, row["context_text"])
        self.assertNotIn(unrelated, row["context_text"])
        self.assertTrue(row["evidence_ambiguous"])
        self.assertEqual(set(row["behavior_ids"]), {"F000001:b0", "F000001:b1"})
        self.assertIn("qualifier_source_links", row)
        self.assertEqual({(link["behavior_id"], link["field"], link["quote"])
                          for link in row["qualifier_source_links"]},
                         {("F000001:b0", "conditions", condition_a), ("F000001:b1", "negations", condition_b)})
        for link in row["qualifier_source_links"]:
            self.assertEqual(link["linkage_status"], "candidate_behavior_link_not_verified")
            for span in link["source_spans"]:
                self.assertEqual(source[span["start"]:span["end"]], link["quote"])
        self.assert_roundtrip(source, row)

    def test_explicit_null_collections_preserve_unknown_not_empty_certainty(self):
        quote = "未按规定回访。"
        source = "甲机构。\n" + quote
        draft = draft_for(quote)
        fields = ("risk_mechanism_quotes", "material_function_quotes", "conditions", "negations",
                  "exceptions", "uncertainties", "materials", "factor_values")
        draft["behaviors"][0].update({field: None for field in fields})
        draft["coverage"] = None
        original = copy.deepcopy(draft)
        units, audit = self.nullable_project(source, draft)
        self.assertEqual(draft, original)
        row = next(u for u in evidence(units) if u["source_text"] == quote)
        association = row["associations"][0]
        self.assertTrue(association.get("metadata_unknown"))
        self.assertEqual(set(association.get("legacy_null_metadata_fields", [])), set(fields) | {"coverage"})
        self.assertTrue(row["evidence_ambiguous"])
        self.assertIn("legacy_null_metadata_unknown", row["ambiguity_reason"])
        self.assertEqual({a["field"] for a in audit if a["reason"] == "legacy_explicit_null_metadata_unknown"},
                         set(fields) | {"coverage"})
        self.assertEqual(row["text"], quote)
        self.assert_roundtrip(source, row)

    def test_null_entry_quotes_keep_existing_quote_and_unknown_audit(self):
        quote, condition = "可以办理业务。", "客户同意时才可办理。"
        source = "甲机构。\n" + quote + "\n另一个事项。\n" + condition
        draft = draft_for(quote)
        draft["behaviors"][0]["conditions"] = [{"quote": condition, "quotes": None}]
        original = copy.deepcopy(draft)
        units, audit = self.nullable_project(source, draft)
        row = next(u for u in evidence(units) if u["source_text"] == quote)
        self.assertEqual(draft, original)
        self.assertIn(condition, row["context_text"])
        self.assertIn("conditions[0].quotes", row["associations"][0].get("legacy_null_metadata_fields", []))
        self.assertTrue(any(a.get("field") == "conditions[0].quotes" for a in audit))
        self.assert_roundtrip(source, row)

    def test_null_coverage_membership_does_not_invent_behavior_link(self):
        quote, unbound = "可以办理业务。", "未绑定覆盖引文。"
        source = "甲机构。\n" + quote + "\n" + unbound
        draft = draft_for(quote)
        draft["coverage"] = [{"quote": unbound, "behavior_keys": None}]
        units, audit = self.nullable_project(source, draft)
        self.assertFalse(any(a["quote"] == unbound for u in units for a in u["associations"]))
        row = next(u for u in evidence(units) if u["source_text"] == quote)
        self.assertIn("coverage[0].behavior_keys", row["associations"][0].get("legacy_null_metadata_fields", []))
        self.assertTrue(any(a.get("field") == "coverage[0].behavior_keys" for a in audit))
        self.assert_roundtrip(source, row)


class PublicRegressionTest(unittest.TestCase):
    def test_f005270_legacy_null_uncertainties_are_unknown_and_unchanged(self):
        source, draft, sha = public_pair("F005270")
        original = copy.deepcopy(draft)
        try:
            units, audit = projection.project_document("F005270", source, draft, sha)
        except TypeError as error:
            self.fail(f"F005270 legacy null uncertainties must not crash traversal: {error}")
        self.assertEqual(draft, original)
        affected = {"she_responsibility", "yang_responsibility"}
        rows = [a for u in evidence(units) for a in u["associations"] if a["behavior_key"] in affected]
        self.assertTrue(rows)
        self.assertEqual({a["behavior_key"] for a in rows}, affected)
        self.assertTrue(all(a.get("metadata_unknown") and "uncertainties" in a.get("legacy_null_metadata_fields", [])
                            for a in rows))
        self.assertEqual({a["behavior_key"] for a in audit if a.get("field") == "uncertainties"
                          and a["reason"] == "legacy_explicit_null_metadata_unknown"}, affected)
        for unit in units:
            for span in unit["source_spans"]:
                self.assertEqual(source[span["start"]:span["end"]], unit["source_text"])
            for segment in unit["context_segments"]:
                span = segment["span"]
                self.assertEqual(source[span["start"]:span["end"]], segment["text"])
            self.assertEqual(unit["semantic_status"], "candidate")
            self.assertEqual(unit["human_review_status"], "pending")

    def test_f002401_no_channel_development_prefix_on_certificate_penalty(self):
        source, draft, sha = public_pair("F002401")
        units, _ = projection.project_document("F002401", source, draft, sha)
        penalty_units = [u for u in evidence(units) if "展业证" in u["source_text"]
                         and "费用用于银行渠道开拓和关系维护" not in u["source_text"]]
        self.assertTrue(penalty_units)
        self.assertTrue(all("费用用于银行渠道开拓和关系维护" not in u["text"] for u in penalty_units))
        self.assertTrue(all(not u["prefix"] for u in evidence(units)))

    def test_f001369_claim_context_keeps_reliable_measurement_and_rejection(self):
        source, draft, sha = public_pair("F001369")
        units, _ = projection.project_document("F001369", source, draft, sha)
        claims = [u for u in units if u["corpus"] == "structured"
                  and ("无法准确计量" in u["source_text"] or "已经采取纠正措施" in u["source_text"])]
        self.assertTrue(claims)
        for unit in claims:
            self.assertIn("能够可靠计量", unit.get("context_text", ""))
            self.assertIn("不予采纳", unit.get("context_text", ""))
            self.assertIn("我会现场检查以后才采取纠正措施", unit.get("context_text", ""))
            self.assertEqual("".join(source[s["start"]:s["end"]] for s in unit["context_spans"]),
                             unit["context_source_text"])


if __name__ == "__main__":
    unittest.main()
