"""离线源文件统一池及二值直接支撑评分；无网络、密钥、标注生成或文件写入。"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
import random

KS = (1, 5, 10, 20)
TOP_K = 20


def _ids(values, name):
    values = list(values)
    if any(not isinstance(v, str) or not v for v in values):
        raise ValueError(f"{name}含非法ID")
    if len(values) != len(set(values)):
        raise ValueError(f"{name}含重复ID")
    return values


def _queries(queries):
    qids = _ids((q["query_id"] for q in queries), "查询")
    if not qids:
        raise ValueError("查询不能为空")
    return sorted(qids)


def _rankings(qids, rankings_by_method, all_file_ids=None):
    if not rankings_by_method:
        raise ValueError("检索路线不能为空")
    methods = {}
    common = {qid: set() for qid in qids}
    for method in sorted(rankings_by_method):
        if not isinstance(method, str) or not method:
            raise ValueError("非法路线名称")
        rows = rankings_by_method[method]
        actual = _ids((r["query_id"] for r in rows), f"{method}排名查询")
        if set(actual) != set(qids):
            raise ValueError(f"{method}排名未完整唯一覆盖查询")
        methods[method] = {}
        for row in rows:
            ids = _ids(row["file_ids"], f"{method}/{row['query_id']}排名")
            if len(ids) < TOP_K:
                raise ValueError(f"{method}/{row['query_id']}排名不足Top20")
            if all_file_ids is not None and not set(ids) <= all_file_ids:
                raise ValueError(f"{method}/{row['query_id']}排名含库外文件")
            methods[method][row["query_id"]] = ids[:TOP_K]
            common[row["query_id"]].update(ids[:TOP_K])
    return methods, common


def _qrels(rows):
    result = {}
    for row in rows:
        key = (row["query_id"], row["file_id"])
        if any(not isinstance(value, str) or not value for value in key):
            raise ValueError("相关性配对含非法ID")
        if key in result:
            raise ValueError(f"重复相关性配对: {key}")
        result[key] = row
    return result


def build_pool(queries, rankings_by_method, all_file_ids, existing_qrels,
               seed=2026101713, extra_per_query=10):
    """先无标签选取Top20并集和池外样本，再原样关联冻结已有银标。

    rankings_by_method: {method: [{query_id, file_ids: [源文件ID, ...]}]}。
    每个路线须唯一覆盖全部查询，至少返回20个不同源文件。
    pairs中的existing_qrel是整对象副本；本函数从不读取grade。
    """
    if type(seed) is not int or type(extra_per_query) is not int or extra_per_query < 0:
        raise ValueError("seed须为整数，extra_per_query须为非负整数")
    qids = _queries(queries)
    corpus = set(_ids(all_file_ids, "全库文件"))
    methods, common = _rankings(qids, rankings_by_method, corpus)

    # Selection is complete before any qrel is inspected or attached.
    selected = []
    for qid in qids:
        outside = sorted(corpus - common[qid])
        if len(outside) < extra_per_query:
            raise ValueError(f"{qid}池外文件不足{extra_per_query}份")
        material = json.dumps([seed, qid], ensure_ascii=False, separators=(",", ":"))
        query_seed = int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest(), "big")
        sampled = set(random.Random(query_seed).sample(outside, extra_per_query))
        for fid in sorted(common[qid] | sampled):
            selected.append({"query_id": qid, "file_id": fid,
                             "selection": "pooled" if fid in common[qid] else "outside_random"})

    existing = _qrels(existing_qrels)
    pairs = []
    unknown = []
    stats_per_query = []
    for row in selected:
        row = dict(row)
        key = (row["query_id"], row["file_id"])
        if key in existing:
            row["existing_qrel"] = deepcopy(existing[key])
        else:
            unknown.append(dict(row))
        pairs.append(row)
    for qid in qids:
        chosen = [p for p in pairs if p["query_id"] == qid]
        stats_per_query.append({"query_id": qid, "pooled_pairs": len(common[qid]),
                                "outside_random_pairs": extra_per_query,
                                "reused_existing_qrels": sum("existing_qrel" in p for p in chosen),
                                "unknown_pairs": sum("existing_qrel" not in p for p in chosen)})
    return {"pairs": pairs, "unknown_pairs": unknown,
            "common_top20_pool": [{"query_id": qid, "file_ids": sorted(common[qid])} for qid in qids],
            "stats": {"queries": len(qids), "corpus_files": len(corpus),
                      "methods": sorted(methods), "top_k": TOP_K, "seed": seed,
                      "extra_per_query": extra_per_query,
                      "sampling_algorithm": "sha256([seed,query_id])+Random.sample(sorted(outside))",
                      "pooled_pairs": sum(len(v) for v in common.values()),
                      "outside_random_pairs": extra_per_query * len(qids),
                      "reused_existing_qrels": len(pairs) - len(unknown),
                      "unknown_pairs": len(unknown), "per_query": stats_per_query}}


def _fraction(value):
    return {"value": float(value), "fraction": str(value)}


def _score(ids, positive):
    first = next((rank for rank, fid in enumerate(ids, 1) if fid in positive), None)
    row = {"top1_hit": ids[0] in positive,
           "reciprocal_rank": _fraction(Fraction(1, first) if first else Fraction()),
           "first_relevant_rank_within_cutoff": first, "mrr_cutoff": TOP_K,
           "positive_reference_count": len(positive)}
    for k in KS:
        hits = sum(fid in positive for fid in ids[:k])
        dcg = sum(1 / math.log2(i + 1) for i, fid in enumerate(ids[:k], 1) if fid in positive)
        ideal = sum(1 / math.log2(i + 1) for i in range(1, min(k, len(positive)) + 1))
        row[f"precision{k}"] = hits / k
        row[f"success{k}"] = hits > 0
        row[f"ndcg{k}"] = dcg / ideal if ideal else None
    return row


def _aggregate(per_query):
    n = len(per_query)
    hit_count = sum(r["top1_hit"] for r in per_query)
    mrr = sum((Fraction(r["reciprocal_rank"]["fraction"]) for r in per_query), Fraction()) / n
    summary = {"queries": n, "top1_hit_count": hit_count,
               "top1_hit_rate": _fraction(Fraction(hit_count, n)), "mrr20": _fraction(mrr)}
    for k in KS:
        ndcg = [r[f"ndcg{k}"] for r in per_query if r[f"ndcg{k}"] is not None]
        summary[f"precision{k}"] = sum(r[f"precision{k}"] for r in per_query) / n
        summary[f"success{k}"] = sum(r[f"success{k}"] for r in per_query) / n
        summary[f"ndcg{k}"] = sum(ndcg) / len(ndcg) if ndcg else None
        summary[f"ndcg_valid_queries{k}"] = len(ndcg)
    return summary


def evaluate_pool(queries, rankings_by_method, pool, judged_qrels, risk_ids=None):
    """对所有路线使用同一已完整标注Top20并集；未知标签绝不补0。

    judged_qrels可只含新增标注，也可含完整参考；已冻结existing_qrel禁止覆盖。
    仅grade==3为直接支撑。池外随机样本可暂缺标，单列诊断且不进入NDCG。
    risk_ids默认全部查询；给定时只影响汇总，完整性仍校验全部查询和路线。
    """
    qids = _queries(queries)
    methods, common = _rankings(qids, rankings_by_method)
    entries = pool["common_top20_pool"]
    actual_qids = _ids((r["query_id"] for r in entries), "参考池查询")
    declared = {r["query_id"]: set(_ids(r["file_ids"], "参考池文件")) for r in entries}
    if set(actual_qids) != set(qids) or declared != common:
        raise ValueError("排名Top20并集与冻结参考池不一致，须重新建池并补齐标注")

    chosen_ids = set(qids) if risk_ids is None else set(risk_ids)
    if not chosen_ids or not chosen_ids <= set(qids):
        raise ValueError("汇总查询须为非空查询子集")
    labels = _qrels(judged_qrels)
    pairs = {}
    for pair in pool["pairs"]:
        key = (pair["query_id"], pair["file_id"])
        if key in pairs or pair["query_id"] not in common:
            raise ValueError("参考池含重复或未知查询配对")
        expected = "pooled" if pair["file_id"] in common[pair["query_id"]] else "outside_random"
        if pair["selection"] != expected:
            raise ValueError("参考池selection与Top20并集不一致")
        pairs[key] = pair
        if "existing_qrel" in pair:
            frozen = pair["existing_qrel"]
            if (frozen["query_id"], frozen["file_id"]) != key:
                raise ValueError("冻结银标配对不一致")
            if key in labels and labels[key] != frozen:
                raise ValueError(f"禁止覆盖冻结银标，存在冲突: {key}")
            labels[key] = frozen
    expected_pairs = {(qid, fid) for qid in qids for fid in common[qid]}
    if {key for key, p in pairs.items() if p["selection"] == "pooled"} != expected_pairs:
        raise ValueError("参考池遗漏Top20配对")
    missing = sorted(expected_pairs - set(labels))
    if missing:
        raise ValueError(f"Top20统一池缺失标签，共{len(missing)}对: {missing[:5]}")
    for key in pairs.keys() & labels.keys():
        grade = labels[key].get("grade")
        if type(grade) is not int or grade not in (0, 1, 2, 3):
            raise ValueError(f"非法相关性等级: {key}")

    positives = {qid: {fid for fid in common[qid] if labels[(qid, fid)]["grade"] == 3}
                 for qid in qids}
    results = {}
    for method, rankings in methods.items():
        per = [dict(query_id=qid, **_score(rankings[qid], positives[qid])) for qid in qids]
        results[method] = {"scope": "full", "queries": len(qids),
                           "scored_risk_queries": len(chosen_ids),
                           "summary": _aggregate([r for r in per if r["query_id"] in chosen_ids]),
                           "per_query": per,
                           "zero_direct_positive_queries": [qid for qid in qids if not positives[qid]],
                           "ndcg_scope": "common_top20_pool; binary direct support (grade=3)",
                           "reference_quality": "model silver pending human"}
    diagnostic_per = []
    for qid in qids:
        random_keys = [key for key, p in pairs.items()
                       if key[0] == qid and p["selection"] == "outside_random"]
        judged = [labels[key] for key in random_keys if key in labels]
        diagnostic_per.append({"query_id": qid, "sample_count": len(random_keys),
                               "judged_count": len(judged),
                               "unknown_count": len(random_keys) - len(judged),
                               "direct_positive_count": sum(r["grade"] == 3 for r in judged),
                               "grade_counts": {str(g): sum(r["grade"] == g for r in judged)
                                                for g in (0, 1, 2, 3)}})
    diagnostics = {key: sum(r[key] for r in diagnostic_per)
                   for key in ("sample_count", "judged_count", "unknown_count", "direct_positive_count")}
    diagnostics["per_query"] = diagnostic_per
    diagnostics["purpose"] = "independent outside-pool diagnostic; excluded from every NDCG ideal"
    return {"methods": results, "outside_random_diagnostics": diagnostics,
            "common_top20_pool_pairs": len(expected_pairs),
            "metric_policy": "MRR@20, Top1, P/Success@1/5/10/20, binary grade3 pool NDCG",
            "model_inference_performed": False}
