# V2规范化独立规格审核

最新小范围追加复审：合法旧结构兼容 **spec PASS**。实际固定 SHA256 为 `650f294176b879011018d8dffb25374c951caa20985cbe886e9053a11b1113c7`；先独立完成规格阶段，再进入该小改代码质量阶段。下文保留先前规格阶段历史证据，最新验证见文末。

审核日期：2026-10-12。范围：`normalize_v2.py`、`test_normalize_v2.py`，实际八表契约及获准的候选/来源导出；未修改实现，未读取凭据、盲验资料或桌面正文。

首次审核实现SHA256：`34AEF320CEF573FD41A52C218B5F455814F76F2DD825495EF2E57A71ECED6566`。

第二次审核实现SHA256：`B45C64A59490ED0F5960A1ADDC2127DF3E8C0EF080F9B8E1CAA648F4F170962B`。

最终规格复审实现SHA256：`5FB5797DF65F0C89300BE0D81E5ACE298F33BC6F4D67685EB88DFFBF01A59331`，已独立读取文件哈希确认。

## 最终结论：PASS（本次规范化规格阶段）

最终23项测试独立运行全部通过，48份跨四批真实样本独立复验通过；原B1-B4及B5三项反例全部被正确拒绝，五个规格阻断均已关闭。源码已对三类reading重建完整预期行并比较整行及对象集合覆盖，阅读事实和状态与核心记录/原稿绑定，不仅检查几个特定字段。本次规格阶段PASS，不表示9639全量生成或语义/真人审批验证完成。按分工在此结束，未进入代码质量阶段。

## 已确认通过

|规格|实际证据与边界|
|---|---|
|八核心表和扩展区别|与`contracts/recall-v2/schema.json`八表键一致；核心表声明类型/枚举由复验检查。扩展不冒充核心表。|
|原稿及迁移生效稿分开|`candidate_snapshots`保留完整base_draft；有变化时另存effective_draft，记录两稿规范JSON SHA；没有变化时明确引用base_draft。授权由调用方负责，规范化不伪造批准。|
|稳定ID及跨文书隔离|ID包含file_id、source/text SHA、text_version、对象类别和local_key；15测试验证输入顺序不改变ID、跨文书同key不合并。|
|个案/主体/金额不串案|每案单一受罚主体；保留每条penalty及原币种，不跨主体求和；行为case_key必须存在。|
|quotes与精确位置|逐字段保留quotes，查找所有Unicode码点[start,end)位置；重复出现标记歧义；未匹配保留原值、记录issue且不生成假坐标。复验复算全部出现位置。|
|事实/标签/限定关系|原action等核心事实与conditions/negations/exceptions/uncertainties保留；risk_tag_basis保留推断依据、限制及条件；不把标签推断转成事实。|
|缺失说明|原unknowns保留；适用字段增加缺失/null原因。契约要求string的filename/name用空串、材料功能用unknown；有明确缺失解释，不声称原稿已记载。|
|不生成审批|生成的annotations.reviewer/reviewed_at、reviews.reviewer/reviewed_at/decision为null，approved_scope/field_scope为空；来源状态继承仅pending/unknown默认，无真人审批动作。最终复验覆盖注释、reviews及reading状态与原稿/核心记录一致性。|
|导航主记录与证据位置|document_table/record_table/candidate_snapshot的路径、行号及目标记录由复验检查；evidence_locations的路径、坐标、text_id以及证据完整集合也检查。最终三类reading整行与核心记录/原稿重建的预期行相同，集合无缺失/重复。|
|实际候选形状|只读9639候选扫描：所查核心标量字段缺失为0、同案材料local_key内容冲突为0、重复factor_id为0；9629稿为candidate/pending，10早期稿缺该状态并由包装继承。此形状结论不等于全量生成通过。|

## 首次阻断证据及本次关闭验证

用现有`test_normalize_v2.fixture()`分别生成独立临时目录，先改指定产物，再按实际文件重新计算manifest中对应文件的bytes和SHA256，调用`verify(out)`。所有临时反例目录均由TemporaryDirectory清理；未写真实输入。

|编号|最小反例|实际结果|必要修复|
|---|---|---|---|
|B1 来源SHA跨表绑定漏检|只把`data/source_inventory.jsonl`首行source_sha256改为64个0；documents、snapshots、registry保持原值。|`passed=true, errors=[]`|检查每document.source_id对应的source_inventory官方file_id与source_sha256，并与snapshot/registry所属源版本一致。当前源码694-695只查来源状态；未查该跨表源SHA。|
|B2 假造独立二审完成漏检|把`data/reviews.jsonl`首行`independent_second_review_completed=True`且`reviewed_at='2026-10-12T00:00:00Z'`。|`passed=true, errors=[]`|candidate_status_snapshot必须核验reviewed_at=null、独立二审完成标志false及相应origin；当前703-704未核验这些生成固定值。|
|B3 假造注释人审元数据漏检|把`data/annotations.jsonl`首行reviewer改为`invented reviewer`，reviewed_at改为上述日期。|`passed=true, errors=[]`|对preserved_candidate_draft注释核验reviewer/reviewed_at/review_note不被无来源补造；当前699-701只核验review_status。|
|B4 阅读证据导航失效漏检|把`reading/behavior_reading.jsonl`首个evidence_locations的line/start_char/end_char改为999999。|`passed=true, errors=[]`|复验每条evidence_locations的路径、行号、text_id与坐标，且其证据集合等于该目标quote_bindings产生的全部证据；当前711起只核验三种主指针。|

修复后需为B1-B4加入必要负例，确认每项返回passed=false，再运行现有15项及48样本复验。原始source SHA在本模块仅来自声明，文本SHA及切片实际复算；不要求本模块额外读取未经授权的原PDF或原TXT字节。

本次已经独立确认上述修复：19tests新增4个测试、16个子反例全过；独立重新运行B1-B4均返回passed=false，错误分别为`source_inventory_document_binding`、`review_original_snapshot_drift`、`annotation_original_record_drift`、`reading_evidence_pointer`/`reading_evidence_complete_set`。source版本/原始身份与snapshot、registry关联校验已增加；annotations的value/creator/scope/evidence与reviews的original_record_sha、origin、exclusion_scope、二审标志等原值也已核验。上述B1-B4全部关闭。

## 第二次阻断B5及最终关闭：阅读原值与核心记录绑定

第二次检查重点不仅是导航能指到一条存在记录，还包括reading会向读者显示的原值和状态不得偏离该记录。当时`verify()`源码776-798核验主指针及证据位置，但没有比对阅读行所复制的事实、限定或人审状态。

以下三项均使用独立fixture，核心表和snapshot不改；仅改阅读行，并按实际字节更新manifest中的该文件SHA和大小：

|反例|实际结果|
|---|---|
|`reading/case_reading.jsonl`首行case_summary改为`原稿未记载的事实`|passed=true，errors=[]|
|`reading/behavior_reading.jsonl`首行negations由原有否定对象改为空列表|passed=true，errors=[]|
|`reading/behavior_reading.jsonl`首行human_review_status改为approved、publication_status改为approved_core|passed=true，errors=[]|

必要修复：通过现有record_table指针解析实际case/behavior，并校验reading所复制的所有原值与状态（摘要、主体、penalties、legal_refs、conditions/negations/exceptions、标签与basis、uncertainties及审核/发布状态、field_evidence_state等）一致；document_index内复制的版本绑定、列表和状态也应与document/snapshot一致。无须新增猜测事实。为上述三项添加负例，确认复验拒绝，并复跑19项和48样本。

最终复审确认修复：`record_reading()`（源码143-159）统一构造case/behavior阅读行；`verify()`源码782-818从已校验核心表、snapshot、quote_bindings和issues重建三类reading的整行预期值，比较完整字典，同时检查主键集合相等及无重复；其后保留主指针/证据位置独立校验。document_index的源版本、双稿SHA、批次、对象列表、source链接、原路径、问题数、源缺口及完整继承状态全部进入整行比较。新增4项测试包含36个子反例，覆盖摘要/处罚/主体/限定/标签/状态/额外字段/文档索引。B5三项独立反例现全部返回passed=false，错误为`reading_original_record_drift`，B5关闭。

## 本次实际验证

- 指定Python：`C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`。
- `python -m unittest discover -s work/finrisk_v2_20261012 -p test_normalize_v2.py -v`：15项，5.677秒，OK。
- `verify(work/finrisk_v2_20261012/normalize_fixtures/real_sample_v1)`：passed=true，errors=[]；48来源/文书，73案，127行为，672核心证据，863文档证据，908注释，85材料，48状态review；2923引文字段，0未匹配。
- B1-B4分别均返回passed=true、errors=[]，证明复验漏检；没有全量重跑，没有修改实现或测试。

本次复审结果：

- 同一指定Python独立运行19项测试：13.848秒，OK。
- 原B1-B4独立反例全部返回passed=false；已关闭，不再作为当前阻断。
- 本次48样本独立复验：passed=true、errors=[]，八表计数与首次相同。
- 新B5三项反例分别返回passed=true、errors=[]；当前阻断未关闭。
- 本轮没有重扫/加载全9639，仅使用已有fixture和48份样本；未修改实现和测试，未进入quality阶段。

最终规格复审结果：

- 固定实现SHA与派发值一致：`5FB5797DF65F0C89300BE0D81E5ACE298F33BC6F4D67685EB88DFFBF01A59331`。
- 同一指定Python独立运行23项测试：28.515秒，OK。
- 原B1-B4及B5三项，共7项最小反例各自新建fixture、变更对应文件、重新绑定manifest后独立复验，全部passed=false。
- 最终48样本复验：passed=true、errors=[]；48来源/文书、73案、127行为、672核心证据、908注释、85材料、48状态review；863文档证据、2923引文字段、0issues。
- 最终规格阶段PASS；没有全9639重扫/加载、没有修改实现或测试、没有进入quality。

## 非阻断边界

- 本模块不声称完整JSON Schema、法律现行有效性、风险标签合理性、原PDF一致性或真人批准已经验证。
- 当前9639输入没有材料显式local_key冲突、重复factor_id；实现对未来这两种形状可能首值合并/后值覆盖，作为输入前提记录，不把未发生的形状当本次全量阻断。
- 上游原候选字节SHA与overlay授权需由执行入口绑定；本模块只保留声明和规范JSON双稿SHA，不独自证明原候选文件字节已核验。

## 合法旧结构兼容追加独立规格复审

结论：**本项 spec PASS**。指定标准 Python 独立重跑 `test_normalize_v2.py`：**31 tests，57.181 秒，OK，退出码 0**。当前源码 SHA 与派发值一致。

生产协议核对：legal_refs 的旧 string／array 成员保存为 `legacy_raw_uninterpreted`，保留完整原值与原类型，value／quote 为 null、evidence_ids 为空、效力 unknown；结构对象仍保留既有原字段。非字符串 case_summary 在契约 string 字段用空串占位，同时保存 original_case_summary、legacy／unknown状态和派生原因；unknowns／uncertainties 的显式null以契约数组占位，另保留原null、unknown状态与原因。非数组 related_party_names 直接保留原 string／null，增加原类型和未解析／未知说明，不拆名单。阅读视图显示这些旧值和状态，verify 从 snapshot 重构预期并核对字段存在性／值及完整阅读行。

独立额外组合 fixture：同时设置旧 string／array 法条、对象数组摘要、null 案未知、null 相关主体与null行为未知。原稿和双稿 snapshot 深比较保持，规范核心／reading 的原值、类型、unknown解释均逐项通过。专门把旧法条文字实际放进原文，兼容项仍没有 value／quote／evidence；随后仅向该旧项补造这个“逐字存在”的法条quote并更新实际产物manifest SHA，verify明确拒绝且报 `case_legal_drift`，证明精确原文存在不等于获准提取法条。

另独立经公开file_index定位读取F005066／F005270两条候选及来源，生成临时产物并实际verify通过：2个原数组摘要、1个null案未知、2个null行为uncertainties、4个null相关主体字段、4个旧string法条均保留原形及unknown／legacy说明；原候选和来源对象未变。仅读取这些定位记录及合成fixture，未全库加载或重扫；临时目录自动清理。

实现者notes记载的14异常FID与48样本结果作为实现背景，本轮没有冒称重新独立跑完该14／48集合。独立结论来自本轮31tests、必要组合反例与2份真实定向记录；不替代root正在运行的9639全量生成／真实verify结果，不声称全量验收或人审完成。
