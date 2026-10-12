# V2 已保存输入恢复独立复审

日期：2026-10-12。审查 `recovery.py`、`test_recovery.py`、实际调用的 normalize/prepare/overlay 接口与保存的恢复报告。没有重跑全量恢复，没有修改实现、真实数据、ledger 或审核记录。

## 规格结论：PASS

当前 9639 项保存输入的恢复演练满足本次规格，未发现实际阻断。

- 重建输入仅来自 `normalized_final/extensions/candidate_snapshots.jsonl`、`normalized_final/data/documents.jsonl`、显式传入的最终 overlay 与保存的 contract。原稿以 `base_draft` 恢复 wrapper；有效稿另存 effective map，未将有效稿覆盖原稿。metadata 深复制，正文从已保存 documents 取得；原稿/effective 内容 SHA、wrapper draft SHA、正文 UTF-8 SHA、重复/缺失文书和总体成员集合均有拒绝检查。
- 后续 `normalize_records` 再核对 wrapper/source/base/effective 的 file_id、一致文本 SHA 与 document metadata，保留原 source/text version 绑定，生成稳定 ID 并核对引用关系；`verify` 核验声明字段、状态继承、ID registry、引文坐标、文件 SHA/大小等。状态沿用保存候选，未添加真人批准。`prepare_dataset` 只加载新写的 recovered_inputs，并经现有 `apply_overlays` 核对原 draft/text SHA、file_id 与 candidate/pending；投影继续记录 pending_human_acceptance。
- 规范化载荷逐文件比较保存 manifest SHA；raw/structured 投影比较已保存准备结果 SHA。任一不一致均拒绝产生 PASS 报告；normalized verify 不通过也拒绝。恢复输出要求空目录，未覆盖原产物。
- 源输入读取链没有调用原仓库 data、原 task/raw 文件或 PDF/OCR。`prepare_dataset` 的 backend/分词器调用使用本机既有冻结代码，载入该代码和本机 tokenizer；这是代码依赖，不是原业务数据恢复。原 raw SHA 仅保留先前核验后的声明绑定，本演练没有重新读 raw 字节。

## 代码质量结论：PASS

规格通过后复核内存对象分离、内容 SHA、重复/成员检查、后续 identity/status 校验以及失败前的输出边界。未发现本次实际保存输入范围内需阻断的完整性或来源声明问题。未提出无关风格改动。

结论限定于当前 canonical 保存输入及本机依赖：normalizer 的引文遍历保留输入对象键顺序，任意未 canonical 化的外部 Python 字典首次规范化后再从 canonical 快照重建，可能出现证据/引用行顺序差异；本次全量保存输入已逐字节哈希核验一致，因此不将结果外推为任意输入顺序均可复现。未声称异机依赖安装、原 PDF/OCR 恢复或语义/真人审批通过。

## 独立验证证据

- 指定 Python `-B -m unittest discover -s work/finrisk_v2_20261012 -p test_recovery.py -v`：2/2 通过，验证原稿/有效稿分离且输入对象不变、文本漂移与重复 snapshot 拒绝。
- 另用工作区自动清理的小 fixture，按真实保存数据的 canonical 格式先规范化，再仅从生成的 snapshots/documents 重建并规范化：19 项载荷 SHA/大小全部相同，verify PASS；人为改变 base 内容 SHA 或 wrapper file_id 均被拒绝，pending 状态保留。
- 重新读取 `normalized_final` 与 `recovery/normalized` 的实际文件字节：19 对、38 个文件的大小/SHA 全部符合原 manifest。再读取原 `indexes/all9639_final` 与恢复投影的 raw/structured 实际字节：2 对、4 个文件 SHA 全部符合原准备 manifest。不是只比较两个 manifest 中的字符串。
- 保存的 `recovery/recovery_report.json` 为 PASS：9639 source_files、19 normalized payload、raw/structured 全相同；verify errors=[]、455219 quote_bindings、unmatched_quote_count=0、issues=0。报告中的恢复代码 SHA `181e78382be3590409461bbcccb5c18cdacfec5229a12879a235e408341c8923` 与本次审查源码实际字节一致。全量 verify 使用已存报告，本次没有再次全量复建或运行全量 verify。

本结论是当前数据的独立恢复与机械完整性复审；不等同于模型语义正确、真人批准或独立机器环境可直接运行。
