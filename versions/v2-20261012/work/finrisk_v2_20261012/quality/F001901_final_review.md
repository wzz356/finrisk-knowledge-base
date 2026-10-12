# F001901 摘要闭环

完整原文再次核对。原摘要及对应行为描述误写“会议费”，原文仅明示“虚列保险中介业务绩效工资、虚构保险中介业务套取费用”。已将case_summary及其quote、同事项行为自述严格限制为这两项；不增加其他造业务细节。

继承date_semantic该FID新日期2012年10月30日（原文落款二○一二年十月三十日）。两阶段全部历史值、changes、confirmed_findings均保留。主体、罚款200000元、行为期间2011年、责任角色、标签名和未知项保持原值；状态candidate/pending。

行为依据：
```text
经查, 你公司在2011年期间,存在通过虚列保险中介业务绩效工资、虚构保险中介业务套取费用的违法行为。
```
处罚依据：
```text
上述行为分别违反了《中华人民共和国保险法》第八十六条第二款、第一百一十六条第(十)项的规定,依据《中华人民共和国保险法》第一百六十二条、第一百七十二条的规定,我局决定给予你公司罚款20万
元的行政处罚。
```

冻结guard PASS；all_quotes_exact=true；uncovered_tokens=[]；仍requires_review，不等于人工批准。
```json
{
  "requires_review": false,
  "reasons": [],
  "cases": 1,
  "behaviors": 1,
  "quote_fields_checked": 33,
  "quote_spans_checked": 33,
  "all_quotes_exact": true,
  "uncovered_tokens": [],
  "compatibility_version": "finrisk-compat-v1",
  "structural_replacements": {
    "name": 1,
    "currency": 1
  },
  "name_checks": [
    {
      "case_key": "tianan_anhui_false_expenses",
      "rule_or_exception": "whitespace_only"
    }
  ],
  "semantic_status": "candidate",
  "human_review_status": "pending"
}
```

最终bundle应以F001901_final_overlay本行替代date_semantic同FID；原23行不改。
overlay SHA-256：`f5faef9ee8c7ceae03a845a20754394111ed5851b5ec842a27443d35a34e4ee6`。
