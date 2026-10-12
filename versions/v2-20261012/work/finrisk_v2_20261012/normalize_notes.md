# V2候选规范化模块

## 接口与范围

- `load_records(repo) -> (candidate_map, source_map)`：仅读取`repo/data/candidates/*.jsonl`和`repo/data/sources/*.jsonl`，按`file_id`索引；记录实际导出文件绝对路径及1起始行号；重复ID报错。未读取盲验资料。
- `normalize_records(candidates, sources, out, overlays=None) -> manifest`：两图的ID集合必须一致；输出目录必须为空。`overlays`是`{file_id: 完整生效draft}`，不能含陌生ID。原始和生效draft各自记录规范JSON SHA；overlay授权及上游来源批准由调用方核验，本模块不建立审批。
- `verify(out) -> {passed, errors, core_counts, extension_counts, unmatched_quote_count, validation_scope}`：独立读取产物，复算哈希、原稿绑定、引用、坐标、全部引文出现位置、导航指针、关键原稿事实与状态，失败返回具体错误。
- CLI：`python normalize_v2.py --repo <repo> --output <新目录> [--overlays <map.json>]`；复验用`--output <目录> --verify-only`。

## 产物与字段

使用`finrisk-knowledge-base/contracts/recall-v2/schema.json`的实际八表；复制契约到`contract/schema.json`。核心数据位于`data/`，表和主键如下。

|表|主键|主要关联|
|---|---|---|
|source_inventory|source_id|official_file_id、声明来源SHA|
|documents|text_id|source_id、text_version、来源/文本SHA、完整原文|
|cases|case_id|source_ids、text_ids、behavior_ids、单一受罚主体与原始penalties|
|behaviors|behavior_id|case_id、actor_refs、各类evidence_ids、material_ids、annotation_ids|
|evidence|evidence_id|case_id、behavior_ids、text_id、Unicode码点[start,end)与verbatim|
|annotations|annotation_id|case_id、target_id、field、原值value、evidence_ids|
|materials|material_id|case_id、behavior_ids、evidence_ids、original_expression_ids|
|reviews|review_id|candidate_status_snapshot，仅记录继承状态，无审批动作|

核心字段遵循契约声明；额外字段用于保留来源与表达，不宣称完整JSON Schema或全语义校验：

- 通用：`official_file_id/base_draft_json_sha256/effective_draft_json_sha256/access_scope`；状态保留`human_review_status/publication_status/fact_review_status/tag_review_status/scene_review_status/field_review_status/approved_scope/status_origin`。
- 案/行为：`proposal_local_key/source_record_path/field_evidence_state/derived_missing_reasons`。行为另保留`original_case_key/actor_role/negations/qualification_evidence/product_evidence_ids`；标签`risk_tag_basis`保留原始`match_basis/assignment_scope/confidence/limitations/necessary_conditions/retrieval_rank`等字段，不把推断标签转换成事实。原条件、例外、否定、未知及法条对象保留。
- 材料：`original_material/source_record_paths/behavior_ids/derived_missing_reasons`。同case的同原始材料值共享稳定ID；跨case不自动合并；原始local_key存在时优先作为身份。
- 证据：`verification_scope=exported_text_only/original_source_bytes_verification/quote_location_ambiguity/occurrence_count_for_quote/supported_fields`。位置检查仅证明导出文本中逐字匹配；不声称读取原PDF或原TXT字节。
- 来源/文档：保留`original_source_id/original_text_id`、实际`source_export_location/candidate_export_location/original_candidate_path`及存在的原文档元数据。未知原来源路径为null、未知filename为空字符串并标派生缺失；不补造PDF路径。`byte_size`明确为派生导出原文UTF-8字节量，未声称原TXT/PDF文件大小。
- `annotations.creator`缺失时为`unknown`，附缺失原因；reviewer、reviewed_at、decision为null；`reviews`无approved_scope/field_scope。缺失字段只派生pending或unknown状态；缺失早期draft状态继承包装中的candidate/pending。局部原状态/批准范围不会自动扩为整案批准。

附表位于`extensions/`，明确区别于八表：

- `id_registry`：`record_id/namespace/object_kind/file_id/source_sha256/text_sha256/text_version/local_key`。ID绑定文书及来源/文本版本；案/行为保存原local_key，顺序不改变身份，不按名称跨文书自动消歧。
- `document_evidence`：文档级及无案文档引文，证据字段与核心相同但case_id允许null；不虚构个案。
- `quote_bindings`：`file_id/proposal_field/quote/case_id/behavior_id/target_id/occurrences/evidence_ids/status/location_ambiguity/effective_draft_json_sha256`及来源/文本版本绑定。每个原始已填引文字段可独立回溯；所有原文出现位置全部保留。
- `issues`：`file_id/field/target_id/code/original_quote/status/action/origin`及版本绑定。未匹配引文保留原值、隔离证据绑定，不虚构位置、不删除事实掩盖问题。
- `candidate_snapshots`：`base_draft/effective_draft/effective_draft_reference/base_draft_json_sha256/effective_draft_json_sha256/wrapper_metadata/source_record_metadata/document_metadata`。未变更时生效稿明确引用base_draft，避免两份相同稿重复。所有原字段，包括额外未规范化字段，完整保留。
- `responsibility_relations`：当前输入draft没有独立关系对象，附表为空；不凭空推导责任关系。

阅读产物：`reading/document_index.jsonl`、`case_reading.jsonl`、`behavior_reading.jsonl`及`INDEX.md`。每份文书有索引，所有案/行为有阅读行；通过表路径与1起始行号定位记录，再以text_id和码点坐标回到documents表全文。`evidence_locations`逐一列出引文位置；原文只写一次，不为9639份文书复制重复全文页。`manifest.json`列明核心/附表/阅读表计数及各文件字节数与SHA。

## 验证结果与边界

- 合成测试先失败再实现，当前31项全过：跨文书key隔离、输入顺序稳定、多主体金额不求和、重复引文位置、标签推断与限制、否定/未知/来源缺口、未匹配引文、材料共享引用、双稿SHA、早期状态、无案文档、文件篡改/重复导出ID；追加负例在重新绑定manifest哈希后仍检测原稿事实漂移、孤立field_evidence、引文位置减少、错误导航行、无来源人审批准、阅读副本事实/条件/状态/元数据漂移、必需清单/文件哈希漏项，以及旧式法条/摘要和null未知被篡改或虚构提取。
- 对9639份输入仅做集合/形状读取；跨四批次48份实际样本生成并复验通过：73案、127行为、672核心证据、863文档证据、908注释、85材料、48状态review，2923引文字段、0未匹配。包含4份无案文档和缺材料name的早期特殊形状。样本证据在`normalize_fixtures/real_sample_v1/`；最新复验记录在`normalize_fixture_real_sample_verify.log`。
- 校验范围为声明字段类型/枚举、独立外键/哈希/坐标/核心原值与状态检查；契约nested_constraints所述全部语义、标签是否合理、审批有效性及原PDF一致性未被宣称验证。
- 全量输出由root绑定最新overlays执行；本模块不写旧文件、正式审批、ledger、公开仓库，不使用付费API、不提交或push。

## 独立规格审核B1—B4修复

独立审核发现来源跨表SHA、人审元数据和证据导航有四类复验漏检；已先加入4项测试、16个子反例确认全部红，再修复verify。生成逻辑与原48样本未改；修复没有重新整库加载。

- B1：沿`documents.source_id`找到实际source_inventory行，比较official_file_id与来源SHA，并回查snapshot.source_record_metadata原始file_id/来源SHA/文本SHA/版本/original_source_id/original_text_id。registry每项的版本绑定与快照原值一致；source/text ID的对象类型和原始身份也被核查。
- B2：基于candidate_snapshot.wrapper_metadata原路径与字节SHA、原文书继承状态、该文书实际案/行为ID重构candidate_status_snapshot review期待值。核对origin、目标集合、来源记录路径与SHA、reviewed_at、独立二审完成布尔值及完成标志origin；不接受凭空二审完成或人审元数据。
- B3：从生效原稿的对应case/behavior字段重构注释value、creator、model_or_prompt_version、scope及evidence_ids，再核对该注释来源、reviewer/reviewed_at/review_note。原稿真实记录的creator允许保留；未记载创建者和审批人不能被补造。
- B4：逐条检查evidence_locations只指向核心/文档证据表、合法行、同text_id与精确[start_char,end_char)；导航实际证据集合必须等于该target的quote_bindings全部证据，且不允许遗漏、额外位置或重复项。

实际最新验证：指定捆绑Python运行19项测试，13.439秒、全部通过；对原48样本verify-only返回passed=true/errors=[]，核心与附表计数不变。四类新增测试在重绑manifest SHA后仍返回passed=false，覆盖3种来源变异、4种review变异、4种注释变异、5种导航变异。独立spec复审由root在本实现固定后安排，不把自检冒充独立复审。

## 独立规格复审B5修复

B1—B4已由独立规格复审关闭；复审追加发现阅读副本的显示事实、否定限定和审批状态仍可能偏离核心记录。已新增4项测试、36个子反例，先确认RED全部漏检，再统一重构阅读预期：

- `record_reading`为case/behavior读取视图的纯函数，生成与verify共用同一完整投影；verify从实际核心行、真实行号和已绑定的原文证据构造整条预期阅读记录，再做全值比较。覆盖摘要、主体、处罚、法条、未知、条件、否定、例外、标签与依据、审核/发布状态、字段证据状态和所有指针，缺失或额外业务字段同样拒绝。
- document_index从candidate_snapshots的原稿/生效稿、原wrapper/source元数据、核心document以及实际案/行为ID顺序重构整条预期记录；包含全部来源版本/SHA、原路径、原文档PDF元数据、列表、问题计数和继承状态。
- 三类阅读表均核验记录集合完整且无重复；不把一条导航能指向存在记录等同于其显示事实正确。
- VERSION、ID算法、load_records及既有产物字段保持不变；生成纯函数重构保持相同内容。未整库加载、未修改旧48样本或其他产物。

最新实际结果：指定捆绑Python运行23项测试，26.517秒、全部通过；其中36个新增反例在重绑manifest后都被拒绝。原48样本verify-only返回passed=true/errors=[]、全部计数不变。实现固定，交root安排独立B5复审。

## 独立代码质量P2清单漏项修复

独立规格已通过；代码质量审查发现删除manifest.reading_counts的类别键能跳过该阅读表全部检查。已先增加2项测试，复现3个必需类别漏项、1个“状态/否定篡改后删除behavior_reading”绕过反例及19个必需文件哈希漏项，25项测试出现23个RED失败。

最小修复只在复验入口与读取循环：reading_counts必须恰有document_index/case_reading/behavior_reading三类；复验固定遍历这三类，不由待校验清单决定工作范围。manifest.files必须包含核心8表、附表6表、阅读3表、contract/schema.json与INDEX.md共19个必要产物的bytes/SHA。类别或文件哈希漏项明确报错，无法静默跳过；原读取/规范化行为、VERSION和ID算法不变。

最新指定Python结果：25项测试46.041秒、全部通过，新增23个漏项反例均被拒绝；原48样本verify-only为passed=true/errors=[]、计数不变。未加载全库。实现固定，交root安排独立质量复审。

## 实际全量执行暴露的旧结构兼容

root全量执行在legal_refs旧字符串处发生TypeError，尚未生成完整产物。此处失败不能被计作全量完成。随后按批准范围逐行扫描全部9639候选的规范化实际读取字段类型，未调用load_records聚合全库，也未输出全文、改变原事实或扩展quote解析。

精确旧类型分布如下，全部位于prior1000：

|字段|类型与数量|实际FID/局部key|
|---|---|---|
|cases.legal_refs成员|dict8378、string4、array14|string：F005066(jiade/liu_qing)、F005270(she_xiaobo/yang_min)；array：F005723(1)、F005777(6)、F005845(1)、F006204(6)|
|cases.case_summary|string15618、array2|F005066(jiade/liu_qing)|
|cases.unknowns|array15619、null1|F005066(liu_qing)|
|behaviors.uncertainties|array25184、null2|F005270(she_responsibility/yang_responsibility)|
|cases.related_party_names（附加字段）|array15607、string9、null4|string：F001245(long_ping)、F001865(闵兴/高扬)、F004341(bi_zhiqiang)、F004414(xiong_yi)、F006128(ou_jun)、F008215(zheng_chenli)、F008251(liu_manxiang)、F008295(liu_wei)；null：F005066(jiade/liu_qing)、F005270(she_xiaobo/yang_min)|

另5个材料缺name/form/function为已有明确unknown兼容；其余所扫描case/behavior顶层、处罚/法条/标签/材料/场景/因子成员、draft顶层结构、保险/营销相关值、金额/币种类型、标签tag、因子ID、材料可得性及行为material_function枚举未发现其他阻断类型。

新增6项测试先RED再GREEN，处理方式保持原类型和原义：

- 法条string/array转换为显式legacy_raw_uninterpreted结构项，保存legacy_original_value/type；value和quote为null、evidence_ids为空、metadata_status=unknown并注明derived原因。未把数组两项猜成quote/value，未把姓名或未知说明冒充已提取法条。verify从snapshot原成员类型和值精确重建，拒绝篡改原值/类型或补造法条、引文、证据。
- F005066的两个摘要array在string核心字段中使用空串占位，同时保存original_case_summary、legacy_non_string_uninterpreted状态和derived缺失原因；未将处罚对象数组猜写为事实摘要。null案unknowns与行为uncertainties以契约数组[]承载，同时保存原始null、unknown状态及明确原因，不表示没有未知或不确定性。
- 非数组related_party_names是附加字段，原string/null直接保留，增加原类型与legacy/unknown元数据，不拆名单、不推断关系。阅读记录显示全部这些原值和状态；verify逐字段回查snapshot，拒绝隐藏未知、改类型或猜测摘要/名单。
- VERSION、ID算法、load_records不变。对原本有效类型的生成内容保持兼容；原稿和生效稿完整快照仍保留。

最新实际验证：指定Python运行31项测试，53.581秒、全部通过，旧25项无退化。定向取上述全部14个异常FID实际生成并verify通过：14来源/文书、28案、30行为、219核心证据、522文档证据、236注释、13材料、14reviews、952引文字段、0引文问题；明确保留18旧法条成员、2旧摘要、1null案未知、13旧相关主体字段、2null行为未知。测试目录通过workspace内TemporaryDirectory创建、验证边界后清理，未改真实输入。原48份样本最新复验同样passed=true/errors=[]、计数不变。

这证明异常形状的样本兼容；尚不等于9639全量成品或全量验收完成。只有root完成全部data生成并真实verify通过，才能声明全量完成。
