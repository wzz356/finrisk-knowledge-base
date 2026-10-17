# 候选阅读导航

所有状态来自候选或原记录；位置验证只验证导出文本，不能替代语义审核、PDF核验或真人批准。

文书 5；个案 8；行为 13。

- [全量文书索引](reading/document_index.jsonl)
- [个案阅读](reading/case_reading.jsonl)
- [行为阅读](reading/behavior_reading.jsonl)
- [未匹配引文及问题](extensions/issues.jsonl)
- [全部引文字段与位置](extensions/quote_bindings.jsonl)
- [原稿与生效稿绑定](extensions/candidate_snapshots.jsonl)

JSONL索引的line是1起始行号；原文仅存于documents表，每份文书一行。原文坐标为Unicode码点[start,end)。
材料、注释和证据ID均可连接对应数据表；没有按名称跨文书合并主体或案件。

|批次|文书数|
|---|---:|
|prior1000|2|
|remaining8509|3|
