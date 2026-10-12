# V2最终交付只读复核

日期：2026-10-12。复核总报告、任务清单、人工入口、召回样例MD/JSONL、实际结果/指标、规范化与恢复摘要、登记摘要及登记验证源码。只新增本报告；未重跑GPU、全量恢复或登记，未改变评分或执行人工核定。

## 结论：PASS

一处实际统计说明错误已反馈并修正：初版总报告声称各题均实际返回5份，但V1 structured/BM25实际Top5总位置为248。复读新版确认已改为固定250个评价位置、缺席按无支撑计入分母，并显式披露V1 BM25实返248，其余组250。指标数值没有因修正文案而改分。当前未发现需阻断本地交付的剩余重要不一致。

## 实际数据核对

- 从已保存 `per_query_metrics.jsonl` 聚合核对全部14组、700个查询—方法记录：每组50题；有用文件/片段、至少一份有用文件/片段、片段误导比例、两项池内条件nDCG与 `metrics.json` 相同；实际返回位置248/250口径一致。总报告12行结构化主指标及4行全9639辅助指标的格式化数值逐行对应metrics；已知来源辅助指标分母43，没有称为全库真实Recall。
- 已保存评分实际为1000个query-file配对、1670片段；独立统计“片段≥2而全文<2”共16处，与总报告一致。本次仅读取评分，没有重评分。指标声明 `model_review_only`、human_judgments=0。
- 两份最终V2实际结果各200行，run状态均complete；文件实际SHA与metrics绑定相同，elapsed为150.272394/161.000828秒，报告150.27/161.00一致。run元数据明确cuda/float16及真实本机BGE/重排模型依赖，未将失败/partial产物纳入这两组。
- normalized_final verification与恢复report的八表/扩展计数相同：9639文书、15620案件、25186行为、455219引文、issues=0、未匹配引文=0、responsibility_relations=0。input_freeze为9639通过、157不同文件有效overlay，与报告相同。恢复仍以已存全量报告和此前独立字节SHA复审为证据，本次未再次全量复建。
- registration_final为registered_complete/executed=true；实际plan、receipts各8509行，86 batch；现存plan/receipt原始字节SHA与summary绑定相同，summary字节SHA与verification绑定相同，验证源码实际SHA与report code_sha一致。receipt统计8471 r0、38 r1、6199 needs_review、2310 checked_waiting_sample，与验证报告一致；所有receipt当前SHA=targetSHA、candidate/pending。3809 new、35 update、4665 already_current、47 backups、4703旧proposal和8547总历史均在总报告中准确引用；未把另外1130候选写成8509专属账本的一部分。

## 重点召回材料回源抽查：PASS

抽查Q009、Q012、Q022、Q032、Q039的RRF与RRF_rerank，共10组、50个Top5位置、43份不同来源文书：

- 样例query文本、rank、file_id、unit_id及完整model_assessment逐项等于实际 `all9639_results.jsonl` 与对应per-query指标。
- JSONL中的actual_context.text/source_text/source_spans/source_segments逐项等于实际结果；每个segment的[start,end)切片严格等于其full_source_text原文。完整文本SHA等于样例/pool保存绑定，且与normalized_final documents中的full_text/text_sha256一致。材料字段 `source_sha256` 在该评分池语境中绑定导出全文UTF-8 SHA，本次没有重新核原PDF/raw字节。
- MD引用块逐字等于JSONL中的实际返回context；模型有用数与每组指标一致。不连续原文间隔标记随实际结果保留，没有再生成摘要替代返回片段。human_decision/reviewer全部null、human_review_status全部pending。
- 三个交付入口中的本地链接目标全部存在。

## 登记验证源码边界与限制披露

`verify_registration_delivery.py` 对业务账本和备份统一以SQLite URI `mode=ro`读取，校验integrity_check、成员/config metadata SHA、任务输入文件SHA及全文SHA、当前proposal SHA/revision、旧历史集合/文件SHA、不变jobs完全相同和变更审核绑定清空；最后只写独立验证报告。没有更改业务SQLite、改审或写批准的路径。本次审源和摘要/receipt绑定核对，没有再执行其全量扫描。其 `source_input_and_proposal_byte_hashes_verified` 指任务输入/proposal字节及保存全文绑定，不应外推成此次验证重新读取所有原raw/PDF字节。

最终文档明确保留：human0与模型辅助评分；16处全文/片段阈值分歧；旧4514关注队列未清；responsibility_relations表0；RRF/rerank帮助度回退与Q009/Q012失败；开发50题不等同360预留盲验或27类完整测试；池内nDCG/已知来源辅助范围；V2未发布GitHub、未切默认库；恢复依赖本机代码/冻结分词器且未恢复PDF/OCR。没有将机械通过写成全库真人验收或语义正确。上述发布/应用状态在文档中明确披露，本复核没有执行发布或应用切换。
