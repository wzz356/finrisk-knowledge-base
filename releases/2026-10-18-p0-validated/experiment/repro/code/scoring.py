"""Independent, standard-library-only scorer for normalized FinRisk records.

This module performs no file I/O, model calls, or inference from reference text.
"""

from collections import Counter
from math import comb, sqrt
from statistics import NormalDist


STATES = ("risk", "no_clear_risk", "insufficient_info")
ARMS = ("old", "new")
SPLITS = ("development", "holdout")
ANALYSIS_SETS = ("main", "boundary")
PREDICATE_STATES = ("met", "not_met", "unknown")
REFERENCE_STATUSES = ("boundary_reference_pending", "model_silver_independently_reviewed")


def wilson_interval(correct, total, confidence=0.95):
    """Wilson binomial interval; an empty denominator yields null endpoints."""
    if (type(correct) is not int or type(total) is not int
            or not 0 <= correct <= total or not 0 < confidence < 1):
        raise ValueError("Wilson requires integer 0 <= correct <= total and 0 < confidence < 1")
    if not total:
        return {"lower": None, "upper": None, "confidence": confidence}
    z = -NormalDist().inv_cdf((1 - confidence) / 2)
    proportion = correct / total
    divisor = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / divisor
    half_width = z * sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / divisor
    return {"lower": max(0.0, center - half_width), "upper": min(1.0, center + half_width),
            "confidence": confidence}


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def _rate(correct, total):
    return {"correct": correct, "total": total, "rate": _ratio(correct, total),
            "wilson95": wilson_interval(correct, total)}


def _micro(true_positive, false_positive, false_negative):
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": _ratio(true_positive, true_positive + false_positive),
        "recall": _ratio(true_positive, true_positive + false_negative),
        "f1": _ratio(2 * true_positive, 2 * true_positive + false_positive + false_negative),
    }


def _text(value):
    return isinstance(value, str) and bool(value)


def _id_list(value):
    return isinstance(value, list) and all(_text(item) for item in value)


def _valid_prediction(pred):
    """Reject malformed records as whole-query failures, without repairing them."""
    if not isinstance(pred, dict) or pred.get("valid") is not True:
        return False
    if pred.get("state") not in STATES or pred.get("validation_errors") != []:
        return False
    if not isinstance(pred.get("current_text"), str):
        return False
    for key in ("mechanism_ids", "case_unit_ids", "legal_article_ids", "displayed_case_ids", "displayed_article_ids"):
        if not _id_list(pred.get(key)):
            return False
    predicates = pred.get("predicates")
    if not isinstance(predicates, dict):
        return False
    return all(
        _text(key) and isinstance(item, dict) and item.get("status") in PREDICATE_STATES
        and isinstance(item.get("quote"), str)
        for key, item in predicates.items()
    )


def _validate_reference(ref):
    if not isinstance(ref, dict) or not _text(ref.get("query_id")):
        raise ValueError("Reference requires a nonempty query_id")
    if ref.get("overall_state") not in STATES or ref.get("adjudication_status") not in REFERENCE_STATUSES:
        raise ValueError("Reference has an unsupported state or adjudication_status")
    if not _id_list(ref.get("mechanism_ids")) or not _id_list(ref.get("uncertain_mechanism_ids")):
        raise ValueError("Reference mechanism IDs must be lists of nonempty strings")
    assessments = ref.get("required_predicate_assessments")
    if not isinstance(assessments, list):
        raise ValueError("Reference required_predicate_assessments must be a list")
    seen = set()
    for item in assessments:
        if (not isinstance(item, dict) or not _text(item.get("mechanism_id"))
                or not _text(item.get("predicate_id")) or item.get("status") not in PREDICATE_STATES
                or not isinstance(item.get("evidence"), list)):
            raise ValueError("Malformed required predicate assessment")
        if item["predicate_id"] in seen:
            raise ValueError("Reference predicate_id must be unique within a query")
        seen.add(item["predicate_id"])


def _validate_mapping(rows, refs):
    seen_queries, seen_opaque = set(), set()
    for row in rows:
        if (not isinstance(row, dict) or not _text(row.get("query_id"))
                or not _text(row.get("opaque_id")) or not _text(row.get("group_id"))
                or row.get("split") not in SPLITS or row.get("analysis_set") not in ANALYSIS_SETS):
            raise ValueError("Malformed mapping row")
        if row["query_id"] not in refs:
            raise ValueError("Mapping query_id has no reference")
        if row["query_id"] in seen_queries or row["opaque_id"] in seen_opaque:
            raise ValueError("Mapping query_id and opaque_id must be unique")
        seen_queries.add(row["query_id"])
        seen_opaque.add(row["opaque_id"])


def _paired(entries_old, entries_new):
    counts = {"both_correct": 0, "old_only_correct": 0, "new_only_correct": 0, "both_wrong": 0}
    for (ref, old), (_, new) in zip(entries_old, entries_new):
        old_correct = _valid_prediction(old) and old["state"] == ref["overall_state"]
        new_correct = _valid_prediction(new) and new["state"] == ref["overall_state"]
        key = ("both_correct" if old_correct and new_correct else "old_only_correct" if old_correct
               else "new_only_correct" if new_correct else "both_wrong")
        counts[key] += 1
    b, c = counts["old_only_correct"], counts["new_only_correct"]
    discordant = b + c
    n = len(entries_old)
    p_value = min(1.0, 2 * sum(comb(discordant, i) for i in range(min(b, c) + 1)) / (1 << discordant))
    return {**counts, "total": n, "discordant": discordant,
            "accuracy_delta_new_minus_old": _ratio(c - b, n),
            "exact_mcnemar_two_sided_p": p_value if n else None}


def _mechanical_citations(entries):
    quote_total = quote_correct = predicate_total = query_pass = 0
    id_counts = {"case": [0, 0], "article": [0, 0]}
    for _, pred in entries:
        if not _valid_prediction(pred):
            continue
        quotes = [item["quote"] for item in pred["predicates"].values() if item["quote"]]
        predicate_total += len(pred["predicates"])
        quote_total += len(quotes)
        matching_quotes = sum(quote in pred["current_text"] for quote in quotes)
        quote_correct += matching_quotes
        passed = matching_quotes == len(quotes)
        for kind, returned_key, displayed_key in (
            ("case", "case_unit_ids", "displayed_case_ids"),
            ("article", "legal_article_ids", "displayed_article_ids"),
        ):
            returned = pred[returned_key]
            matching = sum(item in pred[displayed_key] for item in returned)
            id_counts[kind][0] += matching
            id_counts[kind][1] += len(returned)
            passed = passed and matching == len(returned)
        query_pass += int(passed)
    return {
        "quote_literal_validity": _rate(quote_correct, quote_total),
        "quote_coverage": _rate(quote_total, predicate_total),
        "case_id_validity": _rate(*id_counts["case"]),
        "article_id_validity": _rate(*id_counts["article"]),
        "query_checks_pass": _rate(query_pass, len(entries)),
        "measures_semantic_sufficiency": False,
    }


def _score_arm(entries):
    confusion = {state: {label: 0 for label in (*STATES, "invalid")} for state in STATES}
    output_status = {"valid": 0, "missing": 0, "invalid": 0}
    state_correct = mechanism_exact = reference_conditions_exact = predicate_id_set_exact = 0
    mechanism_tp = mechanism_fp = mechanism_fn = 0
    predicate_correct = predicate_total = missing_predicates = 0
    extra_predicates = extra_predicate_queries = 0
    unknown_predicate_correct = unknown_predicate_total = 0
    unknown_query_correct = unknown_query_total = unknown_query_failures = 0
    false_alarms = {
        name: {"risk_predictions": 0, "denominator": 0, "failed_output_count": 0}
        for name in ("normal", "nonrisk")
    }
    for ref, pred in entries:
        valid = _valid_prediction(pred)
        status = "missing" if pred is None else "valid" if valid else "invalid"
        output_status[status] += 1
        predicted_state = pred["state"] if valid else "invalid"
        confusion[ref["overall_state"]][predicted_state] += 1
        state_correct += int(valid and predicted_state == ref["overall_state"])

        expected_mechanisms = set(ref["mechanism_ids"])
        predicted_mechanisms = set(pred["mechanism_ids"]) if valid else set()
        mechanism_exact += int(valid and expected_mechanisms == predicted_mechanisms)
        mechanism_tp += len(expected_mechanisms & predicted_mechanisms)
        mechanism_fp += len(predicted_mechanisms - expected_mechanisms)
        mechanism_fn += len(expected_mechanisms - predicted_mechanisms)

        expected_predicates = {
            item["predicate_id"]: item["status"] for item in ref["required_predicate_assessments"]
        }
        predicted_predicates = {
            key: value["status"] for key, value in pred["predicates"].items()
        } if valid else {}
        reference_conditions_exact += int(valid and all(
            predicted_predicates.get(key) == value for key, value in expected_predicates.items()
        ))
        predicate_id_set_exact += int(valid and expected_predicates.keys() == predicted_predicates.keys())
        predicate_total += len(expected_predicates)
        missing_predicates += len(expected_predicates.keys() - predicted_predicates.keys())
        extras = len(predicted_predicates.keys() - expected_predicates.keys())
        extra_predicates += extras
        extra_predicate_queries += int(bool(extras))
        for predicate_id, expected_status in expected_predicates.items():
            correct = valid and predicted_predicates.get(predicate_id) == expected_status
            predicate_correct += int(correct)
            if expected_status == "unknown":
                unknown_predicate_total += 1
                unknown_predicate_correct += int(correct)

        if (ref["overall_state"] == "insufficient_info" or ref["uncertain_mechanism_ids"]
                or "unknown" in expected_predicates.values()):
            unknown_query_total += 1
            unknown_query_correct += int(valid and predicted_state == ref["overall_state"])
            unknown_query_failures += int(not valid)

        for name, included in (
            ("normal", ref["overall_state"] == "no_clear_risk"),
            ("nonrisk", ref["overall_state"] != "risk"),
        ):
            if included:
                false_alarms[name]["denominator"] += 1
                false_alarms[name]["risk_predictions"] += int(valid and predicted_state == "risk")
                false_alarms[name]["failed_output_count"] += int(not valid)

    n = len(entries)
    per_class = {}
    for state in STATES:
        tp = confusion[state][state]
        fp = sum(confusion[actual][state] for actual in STATES if actual != state)
        fn = sum(value for label, value in confusion[state].items() if label != state)
        per_class[state] = _micro(tp, fp, fn)
        per_class[state]["support"] = sum(confusion[state].values())
    for values in false_alarms.values():
        values["rate"] = _ratio(values["risk_predictions"], values["denominator"])

    return {
        "output_status": output_status,
        "output_coverage": _rate(output_status["valid"], n),
        "output_failure_rate": _ratio(n - output_status["valid"], n),
        "classification": {
            "accuracy": _rate(state_correct, n),
            "macro_f1": sum(per_class[state]["f1"] or 0.0 for state in STATES) / 3 if n else None,
            "per_class": per_class,
            "confusion": confusion,
        },
        "mechanisms": {
            "exact_match": _rate(mechanism_exact, n),
            "micro": _micro(mechanism_tp, mechanism_fp, mechanism_fn),
        },
        "predicates": {
            "reference_condition_states_exact": _rate(reference_conditions_exact, n),
            "full_predicate_id_set_exact": _rate(predicate_id_set_exact, n),
            "status_accuracy": _rate(predicate_correct, predicate_total),
            "unknown_status_accuracy": _rate(unknown_predicate_correct, unknown_predicate_total),
            "missing_required_count": missing_predicates,
            "extra_unscored_condition_count": extra_predicates,
            "extra_unscored_condition_query_count": extra_predicate_queries,
        },
        "unknown_subset": {
            "accuracy": _rate(unknown_query_correct, unknown_query_total),
            "failed_output_count": unknown_query_failures,
        },
        "false_alarms": false_alarms,
        "mechanical_citations": _mechanical_citations(entries),
    }


def score_evaluation(references, mapping, predictions):
    """Score old/new predictions with denominators defined exclusively by mapping.

    ``references``, ``mapping`` and ``predictions`` are iterable dictionaries in
    the normalized schemas described in scoring_notes.md. Returns a JSON-safe
    dictionary, separately reporting every split × analysis_set cell.
    """
    refs = {}
    for ref in references:
        _validate_reference(ref)
        if ref["query_id"] in refs:
            raise ValueError("Duplicate reference query_id")
        refs[ref["query_id"]] = ref
    rows = list(mapping)
    _validate_mapping(rows, refs)
    scheduled = {row["query_id"] for row in rows}
    indexed_predictions, duplicate_pairs = {}, set()
    raw_predictions = list(predictions)
    unmatched_count = 0
    for pred in raw_predictions:
        if (not isinstance(pred, dict) or not _text(pred.get("query_id"))
                or pred.get("query_id") not in scheduled or pred.get("arm") not in ARMS):
            unmatched_count += 1
            continue
        key = (pred["query_id"], pred["arm"])
        if key in indexed_predictions:
            duplicate_pairs.add(key)
            indexed_predictions[key] = {"valid": False}
        else:
            indexed_predictions[key] = pred
    strata = {}
    for split in SPLITS:
        strata[split] = {}
        for analysis_set in ANALYSIS_SETS:
            selected = [row for row in rows if row["split"] == split and row["analysis_set"] == analysis_set]
            stratum = {
                "n": len(selected),
                "group_count": len({row["group_id"] for row in selected}),
                "reference_status_counts": dict(Counter(
                    refs[row["query_id"]]["adjudication_status"] for row in selected
                )),
                "arms": {},
            }
            arm_entries = {}
            for arm in ARMS:
                entries = [
                    (refs[row["query_id"]], indexed_predictions.get((row["query_id"], arm)))
                    for row in selected
                ]
                arm_entries[arm] = entries
                stratum["arms"][arm] = _score_arm(entries)
            stratum["paired"] = _paired(arm_entries["old"], arm_entries["new"])
            strata[split][analysis_set] = stratum
    return {
        "schema_version": "1.0",
        "strata": strata,
        "input_audit": {
            "mapped_query_count": len(rows),
            "reference_count": len(refs),
            "prediction_count": len(raw_predictions),
            "unmapped_reference_count": len(refs.keys() - scheduled),
            "unmatched_prediction_count": unmatched_count,
            "duplicate_prediction_pairs": len(duplicate_pairs),
        },
        "interpretation_notes": [
            "小样本银标对照；boundary_reference_pending 的边界参考尚未裁决，结果仅作暂定诊断。",
            "development/holdout 与 main/boundary 分别报告；不存在混合主指标。",
            "缺失或无效输出在所有整题指标中固定失败；机制 micro 视其预测为空集，不合成 FP。",
            "阴性机制参考下 micro 无法表达输出失败代价，须同时读取整题精确率、有效覆盖率与失败率。",
            "macro F1 固定平均三个类别，未出现且无预测的类别按零 F1 参与平均；空单元为 null。",
            "条件主指标只评参考登记的 pid 子集；额外候选条件单列为未评分项，不视为状态错误。",
            "引用字面与展示 ID 校验仅是机械指标，不代表证据相关性、支持关系或语义充分率。",
            "McNemar 为以题目为配对单位的双侧精确二项检验，未校正组内相关或多重比较。",
        ],
    }
