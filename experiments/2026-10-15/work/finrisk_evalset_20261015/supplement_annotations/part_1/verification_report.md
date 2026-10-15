# 第1片全文标注验证

- 输入：`outputs/FinRisk_可用测试集_v1_20261015/supplement_inputs/part_1.jsonl`。
- 已分批阅读全文94份，仅判断每份输入列出的题目，共127对。
- 所有等级均由本会话对原文语义独立判断，人工明确写入11个`manual_*.json`批次；程序仅序列化和机械校验。
- 等级分布：0分2对，1分26对，2分16对，3分83对。
- assigned pairs与保存输出逐对精确覆盖127/127；无重复、遗漏、越界。
- 所有原文text的SHA256与输入一致，所有2/3分连续引文均为源text精确子串。
- 所有记录均有明确等级、具体理由和适用限制；标注者`full_p1`，`human_approved=false`，`origin=model_source_review_full_pool`。
- 保存输出重新读回验证通过，覆盖94份文书、127个唯一配对；来源字段及高分引文要求通过。
- 机械校验详情保存在`validation_report.json`，可通过`serialize_validate.py`复核。
