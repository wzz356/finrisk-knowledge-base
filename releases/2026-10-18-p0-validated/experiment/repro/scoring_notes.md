# 独立评分器口径与接口

本实现仅使用 Python 标准库；模块不读写文件，不调用模型或其他 API。开发和验证只使用手写小夹具，未读取真实 36 题的题目、参考、模型输出或原评分实现，也未执行真实评分。

## 接口

```python
report = score_evaluation(references, mapping, predictions)
interval = wilson_interval(correct, total, confidence=0.95)
```

三个评分参数均为字典记录的可迭代序列；输出可用 `json.dumps(report, allow_nan=False)` 序列化。所有比率均为 0～1，未定义的零分母返回 `None`，JSON 中为 `null`。评分器不修改输入记录。

参考记录必须包含：

```text
query_id: 非空字符串
overall_state: risk | no_clear_risk | insufficient_info
mechanism_ids: 非空字符串 ID 的列表，可为空
uncertain_mechanism_ids: 同上
required_predicate_assessments: [
  {mechanism_id, predicate_id, status: met | not_met | unknown, evidence: [...]}
]
adjudication_status:
  boundary_reference_pending | model_silver_independently_reviewed
```

参考的 `query_id` 不得重复，同一题的 `predicate_id` 必须唯一。参考 `evidence` 必须为列表，但评分器不解释其文字、偏移或法律支持关系。

调度记录必须包含非空字符串 `opaque_id`、`query_id`、`group_id`，以及 `split: development | holdout`、`analysis_set: main | boundary`。`query_id` 和 `opaque_id` 各自唯一；每条调度都必须有参考。调度确定原始评分分母，输出成功与否不改变分母。无参考、非法分类或重复调度会抛出 `ValueError`，不会静默缩小样本。

预测记录通过 `query_id + arm` 对齐，其中 `arm: old | new`。有效预测所需字段为：

```text
valid: true
state: risk | no_clear_risk | insufficient_info
mechanism_ids: ID 列表
predicates: {predicate_id: {status: met | not_met | unknown, quote: 字符串}}
case_unit_ids, legal_article_ids: ID 列表
current_text: 当前原文字符串
displayed_case_ids, displayed_article_ids: 展示过的 ID 列表
validation_errors: []
```

缺失记录记为 `missing`。`valid` 非严格布尔真、`validation_errors` 非空/缺失、未知状态或字段结构不合法均记为 `invalid`。同题同 arm 出现多条预测时整对记为 `invalid`，不会取最后一条。无法对齐的预测记录在 `input_audit.unmatched_prediction_count` 中单列；对应已调度题仍按缺失处理。额外参考也会审计且不增加分母。

## 输出结构

```text
schema_version
strata[development|holdout][main|boundary]:
  n, group_count, reference_status_counts
  arms[old|new]:
    output_status: {valid, missing, invalid}
    output_coverage, output_failure_rate
    classification: {accuracy, macro_f1, per_class, confusion}
    mechanisms: {exact_match, micro}
    predicates:
      reference_condition_states_exact
      full_predicate_id_set_exact
      status_accuracy, unknown_status_accuracy
      missing_required_count
      extra_unscored_condition_count, extra_unscored_condition_query_count
    unknown_subset: {accuracy, failed_output_count}
    false_alarms[normal|nonrisk]:
      risk_predictions, denominator, failed_output_count, rate
    mechanical_citations:
      quote_literal_validity, quote_coverage
      case_id_validity, article_id_validity
      query_checks_pass, measures_semantic_sufficiency
  paired:
    both_correct, old_only_correct, new_only_correct, both_wrong
    total, discordant, accuracy_delta_new_minus_old
    exact_mcnemar_two_sided_p
input_audit
interpretation_notes
```

`accuracy`、各精确率、逐条件准确率及机械事件率的共同结构为 `{correct, total, rate, wilson95: {lower, upper, confidence}}`。`output_failure_rate` 和误报 `rate` 为数值或 `null`。`micro` 包含 `true_positive/false_positive/false_negative/precision/recall/f1`。

四个 `split × analysis_set` 单元始终独立输出，空单元保留零计数和 `null` 比率；不提供把边界题并入主集的合并指标。`boundary_reference_pending` 的结果只是基于待裁决参考的暂定诊断，状态数量会显式报告。

## 指标定义

- **三分类**：精确比较三个完整标签，不按字符串中的 `risk` 子串判断。缺失/无效输出进入混淆表独立的 `invalid` 预测列，准确率固定算失败。macro F1 固定平均三个标签，某类别既无参考也无预测时按零 F1 参与平均；空单元整体为 `null`。
- **机制**：只读取模型实际返回的 `mechanism_ids`，按集合计算整题精确匹配与标准 micro P/R/F1。`uncertain_mechanism_ids` 不自动添加为阳性参考机制，也不会用于补预测。多报机制正常计 FP。缺失/无效输出的整题精确匹配固定为失败，即使参考为空集；micro 将其视为空预测，参考正项正常计 FN，绝不伪造 FP。阴性参考下 micro 不能表达输出失败代价，因此必须连同整题精确匹配、覆盖率和失败率读取。
- **条件主指标**：`reference_condition_states_exact` 只要求该题参考登记的全部 pid 均有输出且状态逐一相同。漏项、把 `unknown` 改成其他状态、以及整题缺失/无效均失败。额外候选 pid 不计入主条件准确率分母，也不默认为错误，以 `extra_unscored_condition_count` 单列。参考无登记条件的有效输出满足该指标；缺失/无效仍失败。
- **条件结构诊断**：`full_predicate_id_set_exact` 仅比较完整 pid 集合，不判断状态；不作为条件主指标。逐条件 `status_accuracy` 的分母为全部参考登记条件数，缺失/无效输出中的每个参考条件均算错。`missing_required_count` 对其计入全部漏项。额外条件统计仅基于有效输出。
- **unknown 子集**：参考 `overall_state == insufficient_info`，或 `uncertain_mechanism_ids` 非空，或至少一个参考条件状态为 `unknown` 的题目并集。`unknown_subset.accuracy` 计算该子集的整体三分类准确率，缺失/无效照样计错。`predicates.unknown_status_accuracy` 另以参考状态为 `unknown` 的条件数为分母。
- **误报**：`normal` 的分母仅为参考 `no_clear_risk` 的题数；`nonrisk` 的分母为参考非 `risk` 的题数，包括 `insufficient_info`。分子均只计有效输出中实际判为 `risk` 的题数。缺失/无效输出留在分母，并以各子集的 `failed_output_count` 单列；零误报不代表模型成功处理了这些失败题。
- **机械引用**：在有效输出中，非空 `quote` 必须逐字包含于 `current_text`；每个返回案例/法条 ID 必须存在于对应展示列表。引用及 ID 项目级比率的分母为实际提供的项目数量，未提供时为 `null`；`quote_coverage` 的分母为该有效输出实际返回的全部条件数。`query_checks_pass` 使用完整题数分母，缺失/无效失败，有效且无任何引用/ID的输出仅在机械意义上可空真通过。引用文字真实出现不代表状态正确，也不代表相关、支持或充分；`measures_semantic_sufficiency` 始终为 `false`。`current_text` 与展示 ID 的来源可靠性由调用层负责。
- **配对比较**：每题同时检查 old/new 的整体三分类是否正确，缺失/无效作为错误保留。`accuracy_delta_new_minus_old = (new_only_correct - old_only_correct) / n`。精确 McNemar 双侧 p 为 `min(1, 2 * P[Binomial(b+c, 0.5) <= min(b,c)])`。有题但无不一致对时为 1；空单元为 `null`。实现仅使用整数二项式系数，不依赖 scipy。
- **区间**：Wilson 默认 95%，零分母返回两个 `null` 端点。区间只描述相应二项事件比率，不是 macro/micro F1 或差值的区间。

## 验证证据

运行命令（项目根目录，`-B` 避免产生额外缓存文件）：

```powershell
python -B -m unittest discover -s 'work\finrisk_p0_effect_validation_20261018\tests' -p 'test_scoring.py' -v
```

实际红绿循环：

| 阶段 | 实现前观察 | 实现后观察 |
|---|---|---|
| 缺失/无效、机制集合、分层、精确标签 | 5 tests，5 failures | 5 tests，OK |
| 条件状态、unknown、机械引用 | 10 tests，5 failures | 10 tests，OK |
| 配对计数、McNemar、Wilson、输入审计 | 19 tests，11 failures（含子测试） | 19 tests，OK |
| 主条件改为参考子集，额外候选单列 | 20 tests，4 failures | 20 tests，OK |
| Wilson 接近 1 的合法置信度避免分位点舍入至 1 | 25 tests，1 failure（复现 StatisticsError） | 25 tests，OK |

补充现有行为与 Wilson 数值边界的验证后，最终为 **25 tests，OK，退出码 0**。接近 1 的置信度改用下尾分位数计算，测试同时固定了默认 95% 在 1/2 成功率下的原有端点。测试完全手写，包含三分类全对、`no_clear_risk` 完整标签、空机制参考下 invalid 不得白得整题分、未知条件、漏条件、多余候选、相同字句但相反条件状态、边界与 split 隔离、重复记录、配对缺失/无效，以及手算 p=0.625 和 p=1/32 的例子。每次评分测试同时以 `allow_nan=False` 检查 JSON 可序列化。

## 局限

这是小样本银标比较，不能据此认定具有一般化效果；边界待裁决参考的正确性尚未成立。Wilson 区间与 McNemar 检验均未校正同一 group 的相关性，也未校正多重比较；McNemar 按题配对，`group_count` 仅作描述。条件指标不推断未登记的机制、条件或证据的语义正确性。参考 pid 在同题唯一是预测字典接口的必要约束。适配层需保证参考、调度和模型实际输出的标识来源及分层均可靠。
