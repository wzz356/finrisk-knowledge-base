# 既有契约与样板映射
八张主表保留原名称、字段和语义。source_inventory/documents覆盖全量来源；样板cases/behaviors/evidence等只覆盖10文书候选。
另保留document_evidence表示文书级证据，responsibility_relations表示责任关联，retrieval_units表示已有候选上下文片段。
P10到新ID映射在data/id_migrations.jsonl；所有ID引用一致替换，引文/区间/源值不改。原始P10包保持只读。
新增institution_hierarchy、missing_reasons、schema与配置指纹为扩展；原语义审核与真实批准不因结构迁移升级。
supported_fields_schema仍为声明的pilot草稿契约，具体路径对runs/pilot_drafts中的原草稿核对，不假称为最终表路径。
schema.json为typed_field_contract_v1，顶层声明字段类型检查＋独立嵌套/引用/证据/状态检查，不冒称完整JSONSchema实现。
对应教材：核心+扩展模式，第98–99页；可审查变更，第92页。
