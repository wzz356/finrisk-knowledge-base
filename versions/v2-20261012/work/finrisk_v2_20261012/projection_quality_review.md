# FinRisk V2 投影代码质量独立审查

日期：2026-10-12。结论：**production projection_v2.py quality PASS**。未发现该模块自身需要阻断交付的重要代码质量问题。

本轮只审 `projection_v2.py`；已先读取独立 `projection_spec_review.md` 的 spec PASS，再进行质量审查。未编辑实现和测试，未读取凭据／360 盲验，未调用模型或网络服务。

首轮审查版本 SHA256：`6dab731385d3f533ca88cf4c0d3ed2039ba88ebc0b26d6dd51d7307c328137e7`。

合法旧 null 兼容追加复审版本 SHA256：`7f8805bdfa99f9a1f07e7d92415f85b86eee534b5d76b032258cb123f1a315ca`，本轮已实际核对。追加结论：**spec PASS 后 quality PASS**，无新增重要未决问题。

## 实际验证

- 使用指定 Python 实际执行 `-m unittest discover -s work/finrisk_v2_20261012 -p test_projection_v2.py -v`：21 tests，0 failures，`OK`，退出码 0；含 F002401、F001369 公开定向回归。
- 额外构造 CRLF 原文、15 字符短块／3 字符重叠、两主体共享 finding、独立条件、申辩续句及机关拒绝回应组合：18 个 production units 全部通过唯一正文、短原文、空 prefix、逐 span／segment 精确回源、展示分隔、长度标记、candidate/pending 与 draft 深比较不变断言。
- 阅读生产实现的输入／引用校验、精确位置缓存、正文去重、父段恢复、限定回填、歧义标记和输出协议；未用测试实现代替生产代码审查。

## 质量判断

同文件同 corpus 的正文索引只创建一次，后续关联累加所有 case/behavior 与引文种类；原文位置通过同一精确匹配入口保留。短模型输入和完整 context 具有独立字段。所有展示 context 块明确回源，非连续块显式分隔，候选归属不会改变原稿或冒充人工认定。没有隐藏的外部访问或写源文件路径。

父段／回应识别仍依赖明确结构规则；复杂 PDF、无标识回应和表格的限制已在 `projection_notes.md` 声明，本轮没有扩大语义识别要求。

## 适配边界

投影输出的 association／qualifier link 字典可在多个 unit 间共享引用；这是实际输出对象形态，调用方若就地改写应先复制其所有权。本轮发现 `run_v2.normalize_unit_links` 未处理该边界，会在第二次转换限定 ID 时失败；已向 root 反馈并归入首轮 adapter spec FAIL。root 修复后独立组合复审已通过，见 `run_adapter_review.md`；投影模块本身未修改。投影质量通过与适配器规格／质量通过仍为分别作出的结论。

## 合法旧 null 兼容追加质量复审

先实际重跑25 tests并独立复核F005270、嵌套null／未知coverage组合，向root明示本项spec PASS后，才进行本项质量判断；具体原文回源与正文不变证据见最新 `projection_spec_review.md`。本轮25 tests全部通过；真实F005270为19 units、2 null audit，原稿未变。

生产实现通过统一 `_quote_collection` 处理 JSON 数组／显式null，非数组类型仍明确拒绝；另外 `_null_quote_fields` 保存原始路径，故 null 只在遍历机制上无可枚举元素，不被包装成确定的无条件或无不确定性。覆盖关系的null成员／membership分别留审计，未知membership不进入行为关联。unit汇总关联的未知字段，并在证据歧义理由中保留未知解释；有合法原引文时仍走原精确匹配和上下文恢复流程，没有生成正文、位置或来源事实。

额外使用当前冻结不改的 adapter 做只读互操作：规范化 unit links 后，关联仍保留全部 unknown／null字段且case ID正确；`evidence_row`返回association中的未知元数据与 `legacy_null_metadata_unknown` 解释，indexed短原文不变。实际 adapter SHA仍为 `c846cac66071c7f83028d99fb5968332655d51bb550abe4047cf0505c5ad44d4`。未改该适配器或执行中的旧代码快照。

仅修改两份 projection 审查报告；未改实现／测试／原稿，未全库加载，未读取凭据或盲验，未重跑GPU，不以本项质量通过替代全量索引绑定验证。
