# Priority20 完整内容核查记录

核查范围：固定 selection_manifest.json 的20份名单，逐份读取 candidate/source 全文并绑定原始草案和源文本SHA-256。每份核对主体与责任角色、处罚主体和金额、日期/否定、行为覆盖与机制；selection signals只作为复核提示。修复所引原文片段均连续匹配。未调用API、未读取盲验材料，人工审核状态保持pending。

名单（20份）：F000385、F000743、F001972、F001965、F003945、F001976、F005044、F004362、F009272、F004962、F004309、F004991、F003958、F006485、F004864、F003989、F004461、F004695、F003992、F006484。

## 确认并修复

- F003945：3名个人主体行直接列明案由，改为直接个人违法行为。
- F003958：3名代理人被同一处罚条目明确关联到具体行为，改为直接个人违法行为；合计0.3万元不分摊。
- F003989：3组明示“及相关责任人员”；65条个人行为记录的角色修正为responsible_person，具体事项及合计罚款仍不逐人分配。
- F004695：18条个人主体行直接列明各自违法行为，修正角色、动作、摘要和标签归属；不外推实施机制。
- F003992：两组明示“及相关责任人”；50条个人行为记录的角色修正为responsible_person，具体行为与合计罚款不逐人分配。

## 未发现可确认错误

F000385、F000743、F001972、F001965、F001976、F005044、F004362、F009272、F004962、F004309、F004991、F006485、F004864、F004461、F006484：已核对处罚主体、表格相邻行边界、日期与空值、行为机制。没有证据时保留unknown/document_related，未把相邻机构案由扩展到仅列处罚的个人。

## 完整性验证

- Review 共20行且ID与固定名单一致；20份均标记全文已读，六项维度为PASS或REPAIRED。
- Overlay 共5行；base草案SHA、源文SHA与manifest及file_index一致，updated_draft canonical SHA已重算。所有updated_draft保持candidate/pending。
- 事实投影检查通过：改动仅落在confirmed finding覆盖的行为角色/动作/摘要/标签归属，以及对应case summary/unknowns；未改主体、处罚、金额、日期、文号、否定、法规条款。
- priority20_overlays.jsonl SHA-256：`f837f3fcfbdc8760aba3b1abff7de5f395e302cfbfe81339ce7fd39e52519d68`
- priority20_review.jsonl SHA-256：`20397196b4bc6549ff227e461c0d7965ad4689ac28dab342042d103c96f7a43d`
