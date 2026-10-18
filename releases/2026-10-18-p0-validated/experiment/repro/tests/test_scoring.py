"""Independent scorer contract, using only handwritten toy fixtures."""

import importlib.util
import json
from pathlib import Path
import unittest


SCORER = Path(__file__).resolve().parents[1] / "scoring.py"
if SCORER.exists():
    SPEC = importlib.util.spec_from_file_location("independent_scoring", SCORER)
    MODULE = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(MODULE)
else:
    MODULE = None


def reference(query_id, state="risk", mechanisms=None, predicates=None, uncertain=None):
    return {
        "query_id": query_id,
        "overall_state": state,
        "mechanism_ids": list(mechanisms if mechanisms is not None else ["m1"]),
        "uncertain_mechanism_ids": list(uncertain or []),
        "required_predicate_assessments": list(predicates or []),
        "adjudication_status": "model_silver_independently_reviewed",
    }


def dispatch(query_id, split="development", analysis_set="main"):
    return {
        "opaque_id": "opaque_" + query_id,
        "query_id": query_id,
        "split": split,
        "analysis_set": analysis_set,
        "group_id": "group_" + query_id,
    }


def assessment(predicate_id, status, mechanism_id="m1"):
    return {
        "mechanism_id": mechanism_id,
        "predicate_id": predicate_id,
        "status": status,
        "evidence": [{"quote": "toy", "start": 0, "end": 3}],
    }


def prediction(query_id, arm="old", state="risk", mechanisms=None, valid=True, **changes):
    result = {
        "query_id": query_id,
        "arm": arm,
        "valid": valid,
        "state": state,
        "mechanism_ids": list(mechanisms if mechanisms is not None else ["m1"]),
        "predicates": {},
        "case_unit_ids": [],
        "legal_article_ids": [],
        "current_text": "A toy sentence.",
        "displayed_case_ids": [],
        "displayed_article_ids": [],
        "validation_errors": [],
    }
    result.update(changes)
    return result


class ScoringTests(unittest.TestCase):
    def score(self, refs, rows, predictions):
        self.assertTrue(
            MODULE is not None and callable(getattr(MODULE, "score_evaluation", None)),
            "Missing independent score_evaluation implementation",
        )
        result = MODULE.score_evaluation(refs, rows, predictions)
        json.dumps(result, allow_nan=False)
        return result

    def main(self, result, arm="old", split="development"):
        return result["strata"][split]["main"]["arms"][arm]

    def test_missing_and_invalid_stay_in_all_query_denominators(self):
        refs = [
            reference("a"),
            reference("b", "no_clear_risk", []),
            reference("c", "insufficient_info", ["m2"]),
        ]
        result = self.score(refs, [dispatch(r["query_id"]) for r in refs], [
            prediction("a"),
            prediction("c", state="insufficient_info", mechanisms=["m2"], valid=False),
        ])
        old = self.main(result)
        self.assertEqual(old["output_status"], {"valid": 1, "missing": 1, "invalid": 1})
        self.assertEqual(old["classification"]["accuracy"]["correct"], 1)
        self.assertEqual(old["classification"]["accuracy"]["total"], 3)
        self.assertAlmostEqual(old["classification"]["accuracy"]["rate"], 1 / 3)
        confusion = old["classification"]["confusion"]
        self.assertEqual(confusion["no_clear_risk"]["invalid"], 1)
        self.assertEqual(confusion["insufficient_info"]["invalid"], 1)
        self.assertAlmostEqual(old["classification"]["macro_f1"], 1 / 3)
        self.assertEqual(old["mechanisms"]["exact_match"]["correct"], 1)
        self.assertEqual(old["mechanisms"]["exact_match"]["total"], 3)
        self.assertEqual(old["mechanisms"]["micro"]["true_positive"], 1)
        self.assertEqual(old["mechanisms"]["micro"]["false_positive"], 0)
        self.assertEqual(old["mechanisms"]["micro"]["false_negative"], 1)
        self.assertAlmostEqual(old["mechanisms"]["micro"]["f1"], 2 / 3)
        self.assertTrue("reference_condition_states_exact" in old["predicates"], "Missing reference-condition exact metric")
        self.assertEqual(old["predicates"]["reference_condition_states_exact"]["correct"], 1)
        self.assertEqual(old["predicates"]["reference_condition_states_exact"]["total"], 3)

    def test_wrong_mechanism_ids_are_not_filled_from_reference(self):
        result = self.score([reference("a")], [dispatch("a")], [
            prediction("a", mechanisms=["m2"]),
        ])
        old = self.main(result)
        self.assertEqual(old["classification"]["accuracy"]["correct"], 1)
        self.assertEqual(old["mechanisms"]["exact_match"]["correct"], 0)
        self.assertEqual(old["mechanisms"]["micro"]["true_positive"], 0)
        self.assertEqual(old["mechanisms"]["micro"]["false_positive"], 1)
        self.assertEqual(old["mechanisms"]["micro"]["false_negative"], 1)

    def test_empty_reference_invalid_gets_no_exact_match_credit_or_fake_micro_fp(self):
        result = self.score([reference("a", "no_clear_risk", [])], [dispatch("a")], [])
        old = self.main(result)
        self.assertEqual(old["mechanisms"]["exact_match"]["correct"], 0)
        self.assertTrue("reference_condition_states_exact" in old["predicates"], "Missing reference-condition exact metric")
        self.assertEqual(old["predicates"]["reference_condition_states_exact"]["correct"], 0)
        self.assertEqual(old["mechanisms"]["micro"]["false_positive"], 0)
        self.assertIsNone(old["mechanisms"]["micro"]["precision"])
        self.assertIsNone(old["mechanisms"]["micro"]["recall"])
        self.assertIsNone(old["mechanisms"]["micro"]["f1"])

    def test_main_boundary_and_splits_have_separate_denominators(self):
        refs = [reference(q) for q in ["a", "b", "c", "d"]]
        refs[1]["adjudication_status"] = "boundary_reference_pending"
        rows = [dispatch("a"), dispatch("b", analysis_set="boundary"),
                dispatch("c", "holdout"), dispatch("d", "holdout", "boundary")]
        result = self.score(refs, rows, [prediction("a"), prediction("b", state="no_clear_risk")])
        self.assertEqual(self.main(result)["classification"]["accuracy"]["total"], 1)
        self.assertEqual(self.main(result)["classification"]["accuracy"]["correct"], 1)
        boundary = result["strata"]["development"]["boundary"]
        self.assertEqual(boundary["n"], 1)
        self.assertEqual(boundary["arms"]["old"]["classification"]["accuracy"]["correct"], 0)
        self.assertEqual(boundary["reference_status_counts"], {"boundary_reference_pending": 1})
        self.assertEqual(self.main(result, split="holdout")["classification"]["accuracy"]["total"], 1)
        self.assertNotIn("overall", result)

    def test_labels_are_exact_categories_not_risk_substring_matches(self):
        result = self.score([reference("a", "no_clear_risk", [])], [dispatch("a")], [
            prediction("a", state="no_clear_risk", mechanisms=[]),
        ])
        old = self.main(result)
        self.assertEqual(old["classification"]["accuracy"]["correct"], 1)
        self.assertEqual(old["classification"]["confusion"]["no_clear_risk"]["no_clear_risk"], 1)
        self.assertEqual(old["false_alarms"]["normal"]["risk_predictions"], 0)
        self.assertEqual(old["false_alarms"]["normal"]["denominator"], 1)

    def test_missing_and_extra_predicates_and_wrong_unknown_status(self):
        ref = reference("a", predicates=[assessment("p1", "met"), assessment("p2", "unknown"),
                                          assessment("p3", "not_met")])
        pred = prediction("a", predicates={
            "p1": {"status": "met", "quote": "toy"},
            "p2": {"status": "not_met", "quote": "toy"},
            "p4": {"status": "unknown", "quote": ""},
        })
        old = self.main(self.score([ref], [dispatch("a")], [pred]))
        predicates = old["predicates"]
        self.assertTrue("reference_condition_states_exact" in predicates, "Missing reference-condition exact metric")
        self.assertEqual(predicates["reference_condition_states_exact"]["correct"], 0)
        self.assertIn("status_accuracy", predicates)
        self.assertEqual(predicates["status_accuracy"]["correct"], 1)
        self.assertEqual(predicates["status_accuracy"]["total"], 3)
        self.assertEqual(predicates["missing_required_count"], 1)
        self.assertEqual(predicates["extra_unscored_condition_count"], 1)
        self.assertEqual(predicates["extra_unscored_condition_query_count"], 1)
        self.assertEqual(predicates["unknown_status_accuracy"]["correct"], 0)
        self.assertEqual(predicates["unknown_status_accuracy"]["total"], 1)

    def test_invalid_predicates_fail_each_required_status(self):
        ref = reference("a", predicates=[assessment("p1", "met"), assessment("p2", "unknown")])
        pred = prediction("a", valid=False, predicates={
            "p1": {"status": "met", "quote": "toy"},
            "p2": {"status": "unknown", "quote": "toy"},
        })
        old = self.main(self.score([ref], [dispatch("a")], [pred]))
        self.assertIn("status_accuracy", old["predicates"])
        self.assertEqual(old["predicates"]["status_accuracy"]["correct"], 0)
        self.assertEqual(old["predicates"]["status_accuracy"]["total"], 2)
        self.assertEqual(old["predicates"]["missing_required_count"], 2)
        self.assertEqual(old["predicates"]["unknown_status_accuracy"]["total"], 1)

    def test_unknown_subset_and_two_false_alarm_denominators_are_distinct(self):
        refs = [reference("a", "no_clear_risk", []),
                reference("b", "insufficient_info", [], [assessment("p", "unknown")]),
                reference("c", "risk", ["m1"], [assessment("p", "unknown")])]
        result = self.score(refs, [dispatch(ref["query_id"]) for ref in refs], [
            prediction("a"), prediction("b"),
            prediction("c", predicates={"p": {"status": "unknown", "quote": ""}}),
        ])
        old = self.main(result)
        self.assertIn("unknown_subset", old)
        self.assertEqual(old["unknown_subset"]["accuracy"]["correct"], 1)
        self.assertEqual(old["unknown_subset"]["accuracy"]["total"], 2)
        self.assertEqual(old["false_alarms"]["normal"]["risk_predictions"], 1)
        self.assertEqual(old["false_alarms"]["normal"]["denominator"], 1)
        self.assertEqual(old["false_alarms"]["nonrisk"]["risk_predictions"], 2)
        self.assertEqual(old["false_alarms"]["nonrisk"]["denominator"], 2)

    def test_quotes_and_ids_are_mechanical_checks_only(self):
        ref = reference("a", predicates=[assessment("p1", "met")])
        pred = prediction("a", current_text="存在安排，但未落实。", predicates={
            "p1": {"status": "not_met", "quote": "存在安排"},
            "p2": {"status": "unknown", "quote": "从未出现"},
        }, case_unit_ids=["c1", "other"], displayed_case_ids=["c1"],
            legal_article_ids=["l1"], displayed_article_ids=["l1"])
        old = self.main(self.score([ref], [dispatch("a")], [pred]))
        self.assertIn("status_accuracy", old["predicates"])
        self.assertEqual(old["predicates"]["status_accuracy"]["correct"], 0)
        citations = old["mechanical_citations"]
        self.assertEqual(citations["quote_literal_validity"]["correct"], 1)
        self.assertEqual(citations["quote_literal_validity"]["total"], 2)
        self.assertEqual(citations["case_id_validity"]["correct"], 1)
        self.assertEqual(citations["case_id_validity"]["total"], 2)
        self.assertEqual(citations["article_id_validity"]["rate"], 1)
        self.assertEqual(citations["query_checks_pass"]["correct"], 0)
        self.assertEqual(citations["query_checks_pass"]["total"], 1)
        self.assertFalse(citations["measures_semantic_sufficiency"])

    def test_identical_quote_does_not_make_different_status_correct(self):
        ref = reference("a", predicates=[assessment("p", "not_met")])
        pred = prediction("a", current_text="同一句话", predicates={
            "p": {"status": "met", "quote": "同一句话"},
        })
        old = self.main(self.score([ref], [dispatch("a")], [pred]))
        self.assertIn("status_accuracy", old["predicates"])
        self.assertEqual(old["predicates"]["status_accuracy"]["correct"], 0)
        self.assertEqual(old["mechanical_citations"]["quote_literal_validity"]["correct"], 1)

    def test_extra_candidate_predicates_do_not_penalize_reference_condition_accuracy(self):
        ref = reference("a", predicates=[assessment("p1", "met"), assessment("p2", "not_met")])
        pred = prediction("a", predicates={
            "p1": {"status": "met", "quote": ""},
            "p2": {"status": "not_met", "quote": ""},
            "p_extra": {"status": "unknown", "quote": ""},
        })
        old = self.main(self.score([ref], [dispatch("a")], [pred]))
        predicates = old["predicates"]
        self.assertTrue("reference_condition_states_exact" in predicates, "Missing reference-condition exact metric")
        self.assertEqual(predicates["reference_condition_states_exact"]["correct"], 1)
        self.assertEqual(predicates["reference_condition_states_exact"]["total"], 1)
        self.assertEqual(predicates["status_accuracy"]["correct"], 2)
        self.assertEqual(predicates["status_accuracy"]["total"], 2)
        self.assertEqual(predicates["full_predicate_id_set_exact"]["correct"], 0)
        self.assertEqual(predicates["extra_unscored_condition_count"], 1)

    def test_paired_counts_include_missing_invalid_and_exact_mcnemar(self):
        refs = [reference(q) for q in "abcdef"]
        preds = [prediction("a"), prediction("a", "new"), prediction("b"),
                 prediction("b", "new", state="no_clear_risk"), prediction("c", "new"),
                 prediction("d", valid=False), prediction("d", "new"),
                 prediction("e", state="no_clear_risk"), prediction("e", "new"),
                 prediction("f", state="no_clear_risk")]
        cell = self.score(refs, [dispatch(q) for q in "abcdef"], preds)["strata"]["development"]["main"]
        self.assertTrue("paired" in cell, "Missing paired statistics")
        paired = cell["paired"]
        self.assertEqual(paired["both_correct"], 1)
        self.assertEqual(paired["old_only_correct"], 1)
        self.assertEqual(paired["new_only_correct"], 3)
        self.assertEqual(paired["both_wrong"], 1)
        self.assertEqual(paired["total"], 6)
        self.assertEqual(paired["discordant"], 4)
        self.assertAlmostEqual(paired["accuracy_delta_new_minus_old"], 1 / 3)
        self.assertAlmostEqual(paired["exact_mcnemar_two_sided_p"], 0.625)

    def test_wilson_intervals_and_zero_denominators(self):
        self.assertTrue(MODULE is not None and callable(getattr(MODULE, "wilson_interval", None)))
        one = MODULE.wilson_interval(1, 1)
        self.assertAlmostEqual(one["lower"], 0.20654931437723745)
        self.assertAlmostEqual(one["upper"], 1.0)
        zero = MODULE.wilson_interval(0, 1)
        self.assertAlmostEqual(zero["lower"], 0.0)
        self.assertAlmostEqual(zero["upper"], 1 - one["lower"])
        self.assertIsNone(MODULE.wilson_interval(0, 0)["lower"])
        self.assertIsNone(MODULE.wilson_interval(0, 0)["upper"])
        for correct, total in [(-1, 1), (2, 1), (0, -1), (0.5, 1)]:
            with self.subTest(correct=correct, total=total):
                with self.assertRaises(ValueError):
                    MODULE.wilson_interval(correct, total)
        with self.assertRaises(ValueError):
            MODULE.wilson_interval(1, 1, confidence=1)

    def test_wilson_confidence_near_one_keeps_quantile_inside_domain(self):
        default = MODULE.wilson_interval(1, 2)
        self.assertAlmostEqual(default["lower"], 0.09453120573423074, places=15)
        self.assertAlmostEqual(default["upper"], 0.9054687942657693, places=15)
        confidence = 0.9999999999999999
        try:
            interval = MODULE.wilson_interval(1, 2, confidence=confidence)
        except Exception as error:
            self.fail(f"Valid near-one confidence raised {type(error).__name__}: {error}")
        self.assertEqual(interval["confidence"], confidence)
        self.assertTrue(0 < interval["lower"] < default["lower"])
        self.assertTrue(default["upper"] < interval["upper"] < 1)

    def test_no_discordant_pairs_and_empty_cells(self):
        result = self.score([reference("a")], [dispatch("a")], [prediction("a"), prediction("a", "new")])
        cell = result["strata"]["development"]["main"]
        self.assertTrue("paired" in cell, "Missing paired statistics")
        self.assertEqual(cell["paired"]["exact_mcnemar_two_sided_p"], 1.0)
        empty = result["strata"]["holdout"]["boundary"]
        self.assertIsNone(empty["paired"]["exact_mcnemar_two_sided_p"])
        self.assertIsNone(empty["arms"]["old"]["classification"]["accuracy"]["rate"])
        self.assertIsNone(empty["arms"]["old"]["classification"]["accuracy"]["wilson95"]["lower"])

    def test_duplicate_predictions_invalidate_pair_instead_of_last_row_winning(self):
        result = self.score([reference("a")], [dispatch("a")], [
            prediction("a", state="no_clear_risk"), prediction("a"),
        ])
        old = self.main(result)
        self.assertEqual(old["output_status"]["invalid"], 1)
        self.assertEqual(old["classification"]["accuracy"]["correct"], 0)
        self.assertEqual(result["input_audit"]["duplicate_prediction_pairs"], 1)

    def test_structural_prediction_errors_invalidate_whole_query(self):
        cases = [prediction("a", mechanisms="m1"),
                 prediction("a", validation_errors=["toy upstream error"]),
                 prediction("a", predicates={"p": {"status": "maybe", "quote": "toy"}})]
        cases[0]["mechanism_ids"] = "m1"
        for pred in cases:
            with self.subTest(pred=pred):
                old = self.main(self.score([reference("a")], [dispatch("a")], [pred]))
                self.assertEqual(old["output_status"]["invalid"], 1)
                self.assertEqual(old["classification"]["accuracy"]["correct"], 0)
                self.assertEqual(old["mechanisms"]["exact_match"]["correct"], 0)

    def test_duplicate_reference_or_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            self.score([reference("a"), reference("a")], [dispatch("a")], [])
        with self.assertRaises(ValueError):
            self.score([reference("a")], [dispatch("a"), dispatch("a")], [])

    def test_ambiguous_reference_predicate_ids_are_rejected(self):
        ref = reference("a", predicates=[assessment("p", "met", "m1"), assessment("p", "unknown", "m2")])
        with self.assertRaises(ValueError):
            self.score([ref], [dispatch("a")], [])

    def test_missing_reference_and_invalid_dispatch_are_rejected(self):
        try:
            self.score([], [dispatch("a")], [])
        except Exception as error:
            self.assertIsInstance(error, ValueError)
        else:
            self.fail("Missing reference must raise ValueError")
        with self.assertRaises(ValueError):
            self.score([reference("a")], [dispatch("a", split="unknown")], [])

    def test_unmapped_rows_are_audited_and_do_not_inflate_denominators(self):
        result = self.score([reference("a"), reference("unused")], [dispatch("a")], [
            prediction("a"), prediction("unused"),
        ])
        self.assertTrue("input_audit" in result, "Missing input audit")
        self.assertEqual(result["input_audit"]["unmapped_reference_count"], 1)
        self.assertEqual(result["input_audit"]["unmatched_prediction_count"], 1)
        self.assertEqual(self.main(result)["classification"]["accuracy"]["total"], 1)
        self.assertEqual(self.main(result)["output_failure_rate"], 0)
        self.assertIn("interpretation_notes", result)

    def test_all_three_exact_classes_give_macro_f1_one(self):
        states = ["risk", "no_clear_risk", "insufficient_info"]
        refs = [reference(str(i), state, []) for i, state in enumerate(states)]
        rows = [dispatch(str(i)) for i in range(3)]
        preds = [prediction(str(i), state=state, mechanisms=[]) for i, state in enumerate(states)]
        old = self.main(self.score(refs, rows, preds))
        self.assertEqual(old["classification"]["macro_f1"], 1)
        self.assertEqual(old["classification"]["accuracy"]["rate"], 1)

    def test_uncertain_mechanism_defines_unknown_subset_without_adding_gold_positive(self):
        ref = reference("a", uncertain=["m2"])
        old = self.main(self.score([ref], [dispatch("a")], [prediction("a")]))
        self.assertEqual(old["unknown_subset"]["accuracy"]["total"], 1)
        self.assertEqual(old["unknown_subset"]["accuracy"]["correct"], 1)
        self.assertEqual(old["mechanisms"]["micro"]["true_positive"], 1)
        self.assertEqual(old["mechanisms"]["micro"]["false_negative"], 0)
        self.assertEqual(old["mechanisms"]["exact_match"]["correct"], 1)

    def test_missing_invalid_and_empty_citations_do_not_claim_semantic_sufficiency(self):
        refs = [reference(q, "no_clear_risk", []) for q in "abc"]
        old = self.main(self.score(refs, [dispatch(q) for q in "abc"], [
            prediction("a", state="no_clear_risk", mechanisms=[]),
            prediction("b", state="no_clear_risk", mechanisms=[], valid=False),
        ]))
        citations = old["mechanical_citations"]
        self.assertIsNone(citations["quote_literal_validity"]["rate"])
        self.assertIsNone(citations["case_id_validity"]["rate"])
        self.assertEqual(citations["query_checks_pass"]["correct"], 1)
        self.assertEqual(citations["query_checks_pass"]["total"], 3)
        self.assertFalse(citations["measures_semantic_sufficiency"])
        self.assertEqual(old["false_alarms"]["normal"]["denominator"], 3)
        self.assertEqual(old["false_alarms"]["normal"]["failed_output_count"], 2)
        self.assertEqual(old["false_alarms"]["normal"]["risk_predictions"], 0)

    def test_mcnemar_known_one_sided_discordance_case_and_swap_symmetry(self):
        refs = [reference(str(i)) for i in range(6)]
        rows = [dispatch(str(i)) for i in range(6)]
        preds = [prediction(str(i), "new") for i in range(6)]
        forward = self.score(refs, rows, preds)["strata"]["development"]["main"]["paired"]
        self.assertEqual(forward["old_only_correct"], 0)
        self.assertEqual(forward["new_only_correct"], 6)
        self.assertEqual(forward["exact_mcnemar_two_sided_p"], 1 / 32)
        for pred in preds:
            pred["arm"] = "old"
        reverse = self.score(refs, rows, preds)["strata"]["development"]["main"]["paired"]
        self.assertEqual(reverse["old_only_correct"], 6)
        self.assertEqual(reverse["new_only_correct"], 0)
        self.assertEqual(reverse["exact_mcnemar_two_sided_p"], forward["exact_mcnemar_two_sided_p"])


if __name__ == "__main__":
    unittest.main()
