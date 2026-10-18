# FinRisk知识组织增强实施方案

> 执行说明：实施者使用executing-plans技能逐任务执行，按下列复选框记录实际进度。方案日期为2026-10-18；本文为实施计划，任务框不表示已经完成。审核由助手承担，保留模型审核身份。

**目标：**在现有知识库上增加机制边界卡、分层导航、法规依赖阅读及条件证据包，用小批对照验证价值，再决定扩展范围。

**架构：**保留原始证据、已有候选与基础索引，新内容采用独立覆盖层。机制卡组织判断线索，法规提供规范边界，案例提供历史模式，所有确定性引文回到登记原句。知识库输出条目、链接和核查清单，由另一窗口的Agent决定调用与追问。

**技术基础：**Python标准库、UTF-8 JSONL、Markdown、SHA256及既有只读加载器；检索继续使用已冻结的BM25、BGE、RRF 1:1和deepseek-flash重排。复用现有模型和向量缓存，不引入新数据库或框架。

## 一 实施顺序

| 顺序 | 优先级 | 任务 | 交付结果 | 前置 |
|---|---|---|---|---|
| 1 | P0 | T00冻结版本与任务范围 | 输入清单、保护指纹、配置和回归基线 | 无 |
| 2 | P0 | T01统一法规阅读注册 | 核心43条＋补充24条，保留不同证据身份 | T00 |
| 3 | P0 | T02整理首批四张机制边界卡 | M11、M01、M02、M04及案例支持、限制和待核项 | T00、T01 |
| 4 | P0 | T03建立分层导航与双向链接 | 机制入口、条件概览、法规/案例链接和覆盖清单 | T01、T02 |
| 5 | P0 | T04实现条件证据包与只读接口 | 可加载条文依赖、原句和核查清单，显式报告缺项 | T01—T03 |
| 6 | P0 | T05冻结开发与保留评测题 | 24段业务话术、分组划分、参考及评价协议 | T00；在新结果可见前完成 |
| 7 | P0 | T06验证知识组织包 | 固定案例排名，比较条件判断、误报和读取成本 | T04、T05 |
| 8 | P0 | T07封存首版与交付 | 机器入口、报告、变更、清单、回滚及解压验证 | T06 |
| 9 | P1 | T08定向上下文前缀实验 | 至多60个片段的新表示及独立检索对照 | 首版稳定；不阻塞T07 |
| 10 | P1 | T09补齐增量维护 | 依赖变更检测、受影响产物重建及回归记录 | T07；T08的产物一并登记 |
| 11 | P1 | T10按机制扩展 | 最多扩到现有12机制，补27标签覆盖说明 | 首批审核与功能通过；有增益才扩量检索干预 |
| 12 | P2 | T11专项探索 | 原型统计、疑难原页核查或结构化检索的限额试验 | P0/P1结果支持明确需求 |

**最先交付T00—T07。** T08没有效果时保留原检索表示；T10可以扩展可读资料，但不会把无收益的检索干预默认全局启用。完整RAPTOR、全库GraphRAG和全库重生成均不阻塞首版。

P0有效工作量预计8—14小时，按1—2天安排；P1另预留6—12小时。估计包含编码、助手审核和小批评测，网络/API排队、来源取证受阻或新增实质错误会增加时间。执行T00后用实际预检修正排期，不能把估计写成完成承诺。

## 二 已有基础与本轮边界

现有基础包含9639份处罚文书、65475个结构化检索单元和45403个原文单元。既有候选已包含条件、例外、否定和因子字段；已有12机制规则、检索辅助表达、五项版本锁、33处绑定修复及局部关系样例。现有官方27标签保持不变，机制与标签是多对多关系。

2026-10-18交付完成43条核心法规比对、24条依赖补充和960个真实排名位置的读取验收。该便携读取包是544单元/381文书的验收子集，不能当作9639份全库服务实例。新实验仍在全9639文书的65475个结构化单元中召回，然后为实际候选制作可读取快照。

首批三类业务对应四机制：

| 业务类 | 机制ID | 需要区分的相邻情形 |
|---|---|---|
| 销售代确认 | M11 | 销售解释辅助、当事人自主确认、代替确认、合同后回访 |
| 回访 | M01 | 诱导本人不实回答与本人如实回答 |
| 回访 | M02 | 非本人冒名答复与预约转接等不同环节 |
| 合同外利益 | M04 | 成交利益与合同约定、服务性质及相关事实未知 |

首批目标48份不同文书：代确认16份、回访16份、合同外利益16份，回访尽量分到M01/M02各8份。来源交叉时按文件ID去重并补足；有效材料不足则按实际数量发布缺口，最多增补至60份，不用弱相关材料凑数。文件数不等于独立事件数。

本窗口负责知识字段、来源审核、阅读接口、离线实验和交付；另一窗口负责Agent的工具注册、调用策略、轮次和用户交互。本方案不向另一窗口自动发消息，不宣称Agent在线已接入。

收费实验的预算、发送范围及模型由执行时有效授权约束；本次编写方案不调用收费API。既有“允许助手审核”的授权继续使用，不要求用户逐条复核。

## 三 输入文件与工作目录

以下根目录已存在：

```text
ROOT = C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai
```

| 简称 | 已存在路径，相对于ROOT | 用途 |
|---|---|---|
| CURRENT | outputs/FinRisk_知识库V2.1轻量收尾_20261015/effective_candidates.jsonl.gz | 当前9639份候选及稳定关联 |
| DOCUMENTS | outputs/FinRisk_知识库V2_20261012/normalized_final/data/documents.jsonl | 冻结全文与来源身份 |
| STRUCTURED | outputs/FinRisk_知识库V2_20261012/indexes/all9639_final/structured.jsonl | 默认检索单元 |
| RAW | outputs/FinRisk_知识库V2_20261012/indexes/all9639_final/raw.jsonl | 原文单元；本轮不擅自增加为第三召回路 |
| BASE | outputs/FinRisk_知识库增量改进_20261018 | 12机制、基线实验、42/43条文及交接材料 |
| P0OLD | outputs/FinRisk_P0P1落实_20261018 | 最新已封存的核验、读取器、67条阅读材料及校准结果 |
| LABELS | outputs/FinRisk_正式测试集V2_20261017/official_labels.json | 已交付的27标签字典 |
| RUNNER | work/finrisk_retrieval_20261012/runner.py | 已验证的原检索组件 |
| RETRIEVE | work/finrisk_kb_improvements_20261018/retrieve_experiment.py | 真实全库召回流程参考 |
| API | work/finrisk_kb_improvements_20261018/night_api.py等 | 已有DeepSeek调度及恢复逻辑参考 |
| READER | outputs/FinRisk_P0P1落实_20261018/code/kb_reader.py | 已核验的只读消费契约 |

以下为**拟建**目录，实施时新建；不修改上述已封存文件：

```text
WORK = ROOT/work/finrisk_knowledge_organization_v1_20261018
OUT  = ROOT/outputs/FinRisk_知识组织增强_v1_20261018

WORK/
  config.json                    本轮输入与运行配置
  freeze_inputs.py               冻结输入及保护指纹
  legal_registry.py              两类法条快照适配和依赖读取
  mechanism_cards.py             机制卡校验及导出
  navigation.py                  分层入口与链接
  evidence_bundle.py             有限范围的证据装配
  kb_facade.py                    对外只读接口
  case_snapshot.py               从完整基库抽取实际读取所需记录
  eval_protocol.py               输入冻结、分组、答案隔离检查
  retrieve_variants.py           复用现有全库检索并支持表示覆盖层
  rerank_jobs.py                 新请求绑定、缓存及计费清单
  evaluate.py                    指标与逐题错误分析
  contextual_prefix.py           定向背景前缀
  dependency_build.py            增量影响与重建清单
  verify_release.py              包验证与复算
  cli.py                         本轮命令入口
  tests/                         有意义的契约及拒绝路径测试
  task_plan.md / findings.md / progress.md

OUT/
  contracts/                     版本、模式、评价和审核协议
  legal/                         67条标准化阅读注册及来源覆层
  knowledge/                     机制卡与逐条证据链接
  navigation/                    根入口、L0/L1及反向索引
  case_reader/                   本轮实际候选的只读快照
  context/                       前缀和新表示，仅T08生成
  evaluation/private_reference/  参考答案、银标；与模型输入分离
  evaluation/model_inputs/       只含业务输入、候选和必要公开资料
  evaluation/results/            原始响应、排名、判断及指标
  maintenance/                   依赖图、变更影响及覆盖台账
  review/                        助手审核、拒绝、修复和接受记录
  reports/                       结果、限制、采用决定及交接说明
  manifest.json                  载荷SHA清单
```

代码每个文件承担单一职责，校验/读取与API执行分开。旧脚本含硬编码输出及旧费用上限，按函数级能力复用；不直接对旧目录运行旧入口，不把旧授权复制成新授权。

## 四 数据合同

### 4.1 统一身份与版本

- 原有`FRV2-CASE-*`、`FRV2-BEHAVIOR-*`、`unit_id`、`article_id`保持稳定。
- 保留原五项`base_versions`及原清单SHA；新增`enhancement_versions`记录机制卡、导航、法规注册、证据包和前缀版本。33条旧补丁的`requires_versions`仍按原五项校验，不能直接替换成新覆盖层版本。
- 新法条注册以原`article_id`为键，67条ID唯一。核心43条与补充24条拥有不同快照表示，统一API不等于统一伪造成官网原件。
- 每条新增记录含`review_origin=current_session_model`、`human_approved=false`、输入SHA、依据位置及审核状态；程序确定性生成物另标`origin=deterministic_build`。
- 对话输入、原始证据、官方条文、模型解释、候选机制及统计结果分别标明身份。

### 4.2 法条注册

`legal/articles.jsonl`每行必须包含：

| 字段 | 约定 |
|---|---|
| article_id、source_id | 原有稳定ID |
| text、text_sha256 | 条文正文与正文SHA |
| source_representation | `core_text_snapshot`或`official_reader_capture` |
| source_artifact、source_artifact_sha256 | 相对路径及保存文件SHA |
| source_span | 非bool整数的字符半开区间；有字节位置时另列UTF-8字节区间 |
| transform | 核心正文用literal_slice；阅读快照用明示的去行号/排版变换，原快照保留 |
| official_url、source_version | 实际已有来源字段，未知明确为空及原因 |
| validity_evidence、validity_cutoff | 官方现行标签、带截止日目录或待核状态 |
| research_reference_allowed、production_active | 沿用已核验覆层；本轮不自动把后者改为true |
| scope_limits、dependency_ids | 主体、产品、时间、业务环节、例外及有依据的依赖 |

依赖边另存`legal/dependencies.jsonl`，区分`official_cross_reference`与`assistant_required_context`；前者需条文原句，后者需明确说明为何共同阅读。法规“相关”不自动等于必要依赖。

读取接口返回同一正文和来源身份，不把去行号后的字符位置冒充原始快照位置。L007保留其所见版本及现行状态限制；L011/L012继续隔离，不因新增接口自动准入。

### 4.3 机制边界卡

`knowledge/mechanisms.jsonl`每卡包含以下字段：

```json
{
  "mechanism_id": "M11",
  "title": "销售代替当事人确认订立合同文书",
  "identity": "assistant_authored_screening_guide",
  "candidate_label_links": ["客户信息不真实"],
  "label_mapping_is_automatic": false,
  "predicates": [],
  "scope_axes": ["actor", "product", "stage", "date", "version", "exception"],
  "adjacent_mechanism_ids": ["M01", "M02"],
  "article_ids": [],
  "supporting_case_links": [],
  "adjacent_case_links": [],
  "facts_to_check": [],
  "cannot_infer": [],
  "coverage": {},
  "review_origin": "current_session_model",
  "human_approved": false
}
```

上面只说明字段形状，空数组不满足交付验收。实际`predicates`沿用已有`predicate_id`，每个必要条件含定义、业务范围、官方文字引用及模型解释身份。卡片不因一个`canonical_label`就自动确定官方标签；M11与客户信息不真实的独立事实条件继续分开。

每张首批卡至少有2份不同来源文书的有效支持链接，记录是否可能同事件；不足时该卡为`partial`而非填充伪例。相邻案例按实际证据登记，不要求每张卡强行找到“合法反例”。

案例链接含`file_id/unit_id/case_id/behavior_id`、稳定ID、登记span、角色、归责限制和原句SHA。文书中未记载的条件标`not_documented`，不得填作`not_met`。

### 4.4 证据包

`evidence_bundle.py`的输出包含：

- `mechanism_guide`：模型解释卡及其版本。
- `facts_to_check`：该机制要求核查的字段；本窗口不据此宣称题面缺少哪些事实。
- `case_evidence`：历史案例原句、角色、允许读取层与来源限制。
- `legal_evidence`：主条、定义、例外、过渡或其他已登记依赖，各自身份保留。
- `coverage`：`dependency_status=complete/partial`、未解析依赖、适用范围未知项、读取截断及材料覆盖范围。
- `current_input_facts_assessed=false`：知识包不自动评判本次业务事实。
- `full_corpus_relevance_complete=false`：包完整不代表所有相关案例已找齐。

每个子块独立标记来源。前缀与机制卡不能作为处罚文书引文。资料包含类似指令的文字时仍按外部资料读取，不能改变权限、规则版本或工具行为。

### 4.5 拟新增只读接口

以下为待实现的接口合同，**不是已存在API**：

```python
class KnowledgeFacade:
    def list_mechanisms(self): ...
    def read_mechanism(self, mechanism_id, *, level="L0"): ...
    def read_article(self, article_id, *, include_dependencies=True, as_of=None): ...
    def read_case(self, unit_id, *, layer="hit"): ...
    def get_evidence_bundle(self, mechanism_id, unit_ids, *, budget_chars=8000): ...
    def coverage(self, mechanism_id): ...
```

这是签名合同，不是交付代码。实例化时必须传入固定的基础/增强版本及清单指纹；未知ID、跨版本、任意未登记span和不允许的阅读层应拒绝。`as_of`未能核准历史适用时返回未知，不选择“最新法规”倒推旧行为。

`budget_chars`明确按Unicode字符计量，API实际token使用量另记；不把字符数冒充模型token数。超预算按完整证据单元选择，不能剪掉例外却声称依赖齐全。

## 五 P0任务

### T00 冻结版本与执行基线

**预计：**0.5—1小时。**教材：**3.3.3，证据、知识、服务索引分层及可回滚更新。

**文件：**新建`WORK/freeze_inputs.py`、`OUT/contracts/input_freeze.json`、`protected_assets.json`、`scope.json`、`source_registry.jsonl`。

- [ ] 读取上表实际路径、旧清单和版本锁，枚举本轮涉及的所有输入SHA；从LABELS核对27个唯一标签。
- [ ] 冻结四机制、48份目标/60份上限、资料选择规则、允许来源和排除事项。
- [ ] 固定原始检索模型/缓存指纹、分词与BM25参数、RRF常数60/权重1:1、Top100候选及DeepSeek重排协议。
- [ ] 对旧候选、两类索引、原文、旧标注/排名/成绩和已封存P0交付记录保护指纹。
- [ ] 将原14项读取/关系测试所需代码复制到WORK的baseline_check后运行，原封存目录保持只读；原包只读验证入口回放960位置。保存实际结果；若已冻结软件或数据失配，先解决版本问题，不开启新实验。
- [ ] 写出预检耗时、预计唯一模型配对数、实际可用预算及有效授权范围。

**验收：**输入可定位、SHA闭合；旧基线可复现；新增工作路径与已封存目录隔离。这里只建立新工作目录，不改旧源码或默认检索。

### T01 统一67条法规阅读注册

**预计：**1—2小时。**教材：**3.3.1自然语言与结构互补、3.3.3版本及场景限定。

**文件：**新建`WORK/legal_registry.py`、`WORK/tests/test_legal_registry.py`；导出`OUT/legal/articles.jsonl`、`dependencies.jsonl`、`source_registry.jsonl`、`verification.json`。

- [ ] 适配旧43条及24条补充材料，核对ID互斥、正文SHA、快照SHA及各自坐标表示。
- [ ] 对补充条文执行“原快照切片→去已声明行号/排版→正文比对”，保留原快照位置和变换说明。
- [ ] 按现有43条审核覆层的`required_context_articles`生成必要阅读边；检查全部依赖可解析，记录证据与解释身份。
- [ ] 先编写并运行失败用例：负数/bool/越界位置、重复ID、错快照、漏依赖、跨版本、隔离来源被加入。
- [ ] 实现最小`LegalRegistry`，依赖读取使用visited集合处理循环；上限32个节点，触顶返回partial及未解析ID，不能静默标complete。
- [ ] 对67条逐条回读及依赖闭包核验；无原始HTTP/PDF的状态保留。

**验收：**67个唯一可读ID；所有正文与对应快照一致；待核现行状态和历史适用限制随文返回；不新增生产准入。

### T02 完善四张机制边界卡

**预计：**2—3小时，按实际全文长度调整。**教材：**3.3开篇第88页规则边界、3.3.6模块化因子。

**文件：**新建`WORK/mechanism_cards.py`、`tests/test_mechanism_cards.py`；输出`knowledge/mechanisms.jsonl`、`case_links.jsonl`、`claim_evidence.jsonl`及`review/mechanisms/`。

- [ ] 从现有12机制规则选择M11/M01/M02/M04，保留原必要条件ID和官方27标签候选关系。
- [ ] 根据原文和旧候选筛选目标48份来源，按支持、相邻、归责歧义和条件缺项分层；不得使用新评测答案选择材料。
- [ ] 逐卡列出必要条件、适用范围、相邻机制、待核事实、可支持与不可推出事项。
- [ ] 每项规范性断言回到已核法规及必要依赖；案例概括回到全文与登记原句。针对“不满足某条件”与“文书未记载”分开审核。
- [ ] 先测后实现结构校验：必要条件非空、ID无冲突、链接有效、官方标签合法、未知不转false、历史案例不转当前事实。
- [ ] 助手以独立审核上下文核对全文和来源，检查机构行为、个人直接行为、管理责任是否混同。
- [ ] 每卡最多一次初稿、一次证据审核、一次修复复审；仍有实质争议的断言隔离，卡片发布partial及原因，不无限循环。

**验收：**4张完整或明确partial的卡；每条新增断言可回源；每卡支持不足及相邻机制明确；`human_approved=false`。卡片事实审核和检索相关性评分分开记录。

### T03 建立分层入口与双向链接

**预计：**0.5—1小时。**教材：**3.3.2纵向摘要和横向链接。

**文件：**新建`WORK/navigation.py`、`tests/test_navigation.py`；输出`navigation/index.json`、`reverse_links.jsonl`、`coverage.json`、`overview.md`及每机制的少量概览文件。

- [ ] L0输出机制名称、业务环节、一句话用途和状态，建议80—160个汉字，作为本项目上限而非框架API规格。
- [ ] L1输出约400—800汉字的条件概览、相邻机制、适用限制和链接。
- [ ] L2指向真实案例、条文及登记原句；不复制全文到每张概览，不拆出数万小Markdown文件。
- [ ] 从同一份结构化链接表同时生成前向和反向索引；多机制归属允许并存。
- [ ] 先测孤立节点、失效链接、单向漏链、同文书主体合并、解释文本伪作原文，再实现导出。
- [ ] 覆盖清单按“机制、资料、条件、官方标签、待核项”分别计数；未涉及标签显示未覆盖。

**验收：**无悬空链接，双向可达；L0→L1→原句不超过3次确定性读取；目录只辅助导航，不作为全库检索硬过滤条件。

### T04 实现条件证据包和读取门面

**预计：**1.5—2.5小时。**教材：**3.3.1关联组织、3.3.4检索工具化。

**文件：**新建`WORK/case_snapshot.py`、`evidence_bundle.py`、`kb_facade.py`及对应三份测试；输出`case_reader/`、`contracts/read_api.md`、`reports/readback_receipt.json`。

- [ ] 从完整索引中按所需unit_id选择实际记录，流式读取对应当前候选和全文；不把P0OLD的381份来源当成全库。
- [ ] 复用已核验KnowledgeReader及其manifest格式；筛选与快照unit_id对应的33条补丁，保留旧五项版本校验。未登记的版本失配先隔离，不自动补造绑定。
- [ ] 仅已有细分范围审核的单元开放supplement；其余允许hit/extended，并保留归责歧义。
- [ ] 装配机制卡、选定案例原句、法规依赖和核查字段；法规和历史案例不得填入`current_input`事实。
- [ ] 实现四类coverage：本轮材料范围、依赖阅读状态、规范适用未知项、包内容是否被预算限制。不要由此推断全库相关性完整。
- [ ] 先测缺依赖仍称complete、超预算删例外、历史案例填当前事实、修改主体角色、任意span、未知ID、版本和SHA失配，再实现门面。
- [ ] 用四机制和原960位置做实际读取回归；记录新增快照实际单元/文书数量，不预填成旧544/381。

**验收：**六个接口均可离线调用；新包对旧命中引文与稳定ID无非预期变化；重要歧义与缺项可见；当前输入是否满足条件仍由外部判别环节承担。

### T05 冻结评测协议和24段新话术

**预计：**1—2小时。**教材：**实验3-8/3-10的组件对照；评价细节为本项目设计。

**文件：**新建`WORK/eval_protocol.py`、`tests/test_eval_protocol.py`；输出`contracts/eval_protocol.json`、`evaluation/queries.jsonl`、`group_split.json`、`private_reference/expected.jsonl`和`input_freeze.json`。

- [ ] 每个机制构造2个不同业务故事，每个故事3种关键条件：风险线索明确、未见该机制、信息不足。4机制×2故事×3条件=24段。
- [ ] 输入均为80—200汉字的营销/培训/操作话术，不写成法条问答，不在输入附上风险标签、参考答案或预期文件ID。
- [ ] 按故事组划分：每机制1组开发、1组保留，合计开发12题/保留12题。反事实三条不跨集合；只有8个故事组，不能当24个独立样本计算不确定性。
- [ ] 参考制定者依据法规、题面明确事实和范围独立给出三态与机制集合，逐条核对证据；缺外部合同/产品事实时允许unknown，不为配齐类别伪造事实。
- [ ] 先做题目和答案可判定性审核再冻结；实际无法构成预期状态的题在结果可见前重写，冻结后不按成绩删题。
- [ ] 将参考与模型输入分目录；验证所有API输入不含参考标签、旧分数、目标文件或盲标理由。公开规则/机制卡作为实验知识不属于参考泄漏，逐题预期答案属于泄漏。
- [ ] 冻结评分协议、缓存键、预算、失败/缺失处理、采用门槛；保留集一旦查看结果即记为已使用。

**验收：**24条、8故事组、12/12分组清晰；输入与参考SHA分开；助手审核来源明确。合成、模型银标与小样本局限写入协议，不能称专家金标。

### T06 分开验证知识组织与检索表示

**预计：**1—2小时调度和分析，另加API等待及盲标时间。**教材：**3.3.4/3.3.5组件对照，3.3.6条件分析。

本任务只跑下节实验K。实验R留给T08，避免背景变化和知识组织变化混成一个效果。

**文件：**新建`WORK/retrieve_variants.py`、`rerank_jobs.py`、`evaluate.py`及对应测试；输出routes、请求输入、usage账本、排名、判断、qrels、指标和逐题归因。

- [ ] 适配既有全库检索函数，先证明B0在旧冻结输入上可复现；新24题只接收输入文本和哈希。
- [ ] 冻结本轮案例阅读策略；两臂用完全相同的案例Top20和案例原文，检索阶段均为BM25/BGE各100、1:1 RRF100、DeepSeek重排100。
- [ ] 重排输入继续由完整索引及已冻结的原上下文构造策略准备，不经过48份试点材料过滤。排名完成后，把实际Top20并集与机制卡所引单元加入新的case_reader快照；开发/保留阶段各留版本，最终导出其有效并集并固定新清单。
- [ ] 先跑开发12题排错，固定K1后再一次性跑保留12题；保留结果不再用于修改同轮方案。
- [ ] 相同输入/单元/实际重排文本/规则/模型配置的评分复用；两臂只改变判别端知识组织包，不重复支付同一重排。
- [ ] 判别输出采用相同JSON结构：总体三态、机制集合、必要条件状态、当前输入引文、案例引用、法规引用和限制。程序仅核查一致性，语义由盲评复核。
- [ ] 实际Top20按query-file去重，全量盲评3/2/1/0相关性；参考制定与结果评分不接收方案、排名、分数或预期答案。
- [ ] 对新增误报、事实来源混淆、漏掉例外和归责错误逐条回源；记录所有退步，不只展示改善例。
- [ ] 复算指标、成本及基线保护SHA；按门槛输出采用/实验保留/拒绝决定。

**验收：**开发和保留分别报告、24题结果覆盖明确、无隐藏未完成项、排名及指标可复算。固定排名的K实验不能宣称检索召回率提升。

### T07 封存首版并交付

**预计：**0.5—1小时。**教材：**3.3.3审核后发布、回归和可恢复。

**文件：**新建`WORK/verify_release.py`、`tests/test_release.py`；输出`OUT/manifest.json`、交付报告、机器接口说明、审核记录、采用决定、zip及外部封包核验记录。

- [ ] 分别检查规格覆盖、代码质量、实际数据与报告数字；不以测试全过替代法规或语义复核。
- [ ] 确认核心法条、补充法条、模型解释和当前输入身份分离；所有新审核保持human_approved=false。
- [ ] 导出只读代码、必要文书子集、卡片、法条、导航、冻结协议及能支撑结论的实验数据；模型权重、密钥、教材原文和非必要运行缓存不入包。
- [ ] 清单登记所有载荷SHA；在新目录解压，用标准库入口完成读取/指标复算和原文回读。
- [ ] 对需要BGE或联网的实验给出环境指纹和命令，不把标准库包验证称为已经重跑了模型。
- [ ] 比较旧保护文件指纹；写出默认配置、可选实验配置和回滚方法。GitHub发布作为独立后续动作，以具体待发布文件集为单位，不在本轮规划阶段推送。

**验收：**交付目录及解压目录验证一致；每项结论有结果文件；部分/失败/未知不被写成全量完成。P0即使没有测得准确率增益，也可交付可读可追溯组件，并保持可选状态。

## 六 两类对照实验

### 6.1 实验K 知识组织包是否帮助判断

| 项目 | K0本轮共同素材基线 | K1知识组织包 |
|---|---|---|
| 输入 | 同一原始业务文字 | 完全相同 |
| 案例来源与排名 | 全9639文书双路召回后固定Top20 | 完全相同，不新增案例候选路 |
| 案例原文 | 按冻结规则装配，最多4000字符 | 同一实际原文块及字符顺序 |
| 法规可用集合 | 同一67条注册；使用现有规则说明及其主条引用 | 同一67条注册；新边界卡、导航及依赖闭包 |
| 机制候选 | 复用冻结词表，最多2个假设，不读取参考 | 同一结果；无触发时展示首批4机制的简短入口 |
| 法规及指引预算 | 最多4000字符 | 同一上限，卡片和依赖共同占用 |
| 判别模型与协议 | 相同DeepSeek配置、JSON结构和输出预算 | 完全相同 |

K0为本轮统一素材下的平铺阅读基线，不是旧实验原始成绩，也不代表另一窗口Agent的最优能力。两臂可用法条集合一致，K1改变知识表达与证据装配；这是组合改进对照，不能单独归因给目录、卡片或依赖中的某一项。

主要评价：

1. **三态正确数**：风险、未见所测机制、信息不足。分别给出各类分母与混淆表。
2. **机制集合准确情况**：完整正确、遗漏、额外机制；不自动等同官方27标签准确率。
3. **边界错误数**：必要条件未知仍认定成立；明确不满足仍认定成立；把历史案例当当前事实；跨主体归责；无视条文范围或例外。
4. **引用支持情况**：字面回源正确率与语义支撑率分开。字面可自动核对，适用/支撑由助手盲评，不互相替代。
5. **读取成本**：案例/法规/指引字符数、实际API usage、请求数、成功/失败/重试和耗时；预加载、索引构建与单请求延迟分开。

Top-1、MRR、P及pool NDCG可作同一案例排名的描述，K0/K1理应相同；不得把这些不变指标包装为知识组织提升检索的证据。

采用门槛分为两层：

- **功能交付：**零悬空链接、零来源或版本混用、所有必需依赖状态可解释、零新增跨主体归责。达到后可以交付可选知识组织组件。
- **试用建议：**在保留12题上，K1的三态正确数不低于K0，且边界错误至少减少1例；未见所测机制/信息不足两类均无新增错误，引用支撑不下降、同预算内运行。若K0已经零边界错误，只报告保持正确及成本变化，不宣称解决了边界错误。

门槛用于这批开发试用决定，不是总体效果或统计显著性保证。保留集只有4个故事组，报告逐题差异及组结构；不以24题独立假设计算置信区间。即使过门槛，也先作为实验配置供另一窗口试接，不直接替换全系统默认。

### 6.2 实验R 定向前缀是否改善召回与排序

| 项目 | R0 | R1 |
|---|---|---|
| 知识库 | 完整9639文书、65475结构化单元 | 同一完整集合，仅覆盖至多60个被选单元的索引表示 |
| 片段表示 | 当前原表示 | 已审核的块特定背景＋原表示 |
| BM25/BGE | 原索引/原向量 | BM25按修改文本重建；BGE只重编码受影响向量 |
| 融合和候选深度 | 各100，RRF常数60/权重1:1，融合100 | 相同 |
| 重排 | DeepSeek读取统一规则下的实际文本 | 背景若纳入重排即绑定新输入；只比索引时两臂重排正文保持一致 |
| 证据引用 | 原文登记span | 原文登记span；前缀单列解释，不能作处罚引文 |

首个R试验冻结为**仅改变索引表示**：R1前缀参与BM25与BGE，重排使用与R0相同的案例阅读策略和原句，不另改重排提示词或上下文。这样测的是候选变化。若后续要把前缀送入重排，另开新版本，不在同轮混加。

固定查询、相同全文参考，按源文书去重报告K=1/5/10/20：Top-1、MRR@20、P@K、Success@K及pool NDCG@K。相关性3为直接支撑；NDCG增益0/1/3/7。所有参与比较的Top20全文配对均需标注，未标不是0分；IDCG为零时记未定义并公开有效分母。

同时跟踪已知直接案例在哪一步丢失：任一路Top100、融合Top100、重排Top20。该覆盖统计仅对已知参考池有效；没有全库相关分母就不报告真实Recall。

R1的开发门槛：P@5及pool NDCG@20均不下降，且Top1至少多1题，或MRR@20提高至少0.03；没有新增主体/范围错误。开发通过才运行保留12题。保留试用门槛为Top1和MRR不下降、至少一项前排指标改善，所有退步逐题披露。小样本通过仍不足以自动铺到全库。

本方案按P0完成后再做P1排期，因此R不复用已经看过结果的K保留12题。R开发沿用原开发12题；其保留组另写12条新话术，仍为四机制各一个新故事的三态组，先审核并冻结，不能看R结果后选择题。全部阶段合计最多36条不同输入。执行台账记录每组何时被谁查看。

### 6.3 模型、参考与缓存

- 题目参考、检索相关性和结果支撑均标模型银标；用户不需人工复审，助手负责回源与争议隔离，不能改称金融专家审核。
- 每个query-file配对只保留一个共享相关性参考，跨方案复用；不得各自按本方案结果调整标准。
- 新查询不能沿用旧同机制题目的等级；相同查询但参考协议有变时另版本存储。
- 缓存键至少含原始query文本SHA、unit_id、实际重排文本SHA、规则SHA、模型标识/响应模型、完整生成配置和读取策略SHA。输入不同不得复用分数。
- 引文与评分分别保存；无效生成引文不得作为支持引用，程序回读只证明原文存在。格式恢复规则在运行前冻结，变更后保存新协议及统一敏感性检查，不能按分数挑响应。
- HTTP尝试、评分槽位与有效结果数分别计数；所有最终缺失按冻结规则报告，不用静默删题使成绩升高。

## 七 P1任务

### T08 定向上下文前缀

**预计：**2—4小时，另加可选保留试验等待。**教材：**3.3.5实验3-10。

**文件：**新建`WORK/contextual_prefix.py`、`tests/test_contextual_prefix.py`；输出`context/selection.jsonl`、`prefixes.jsonl`、`representation_overlay.jsonl`和实验R结果。

- [ ] 在48份材料内，按缺少主体/业务环节/产品条件、代词依赖、片段只有证据清单等事先规则选择至多60单元；不按新题答案或排名挑片段。
- [ ] 从父段、已核字段和原句可恢复的先用模板；确有语义归纳需求再由当前会话生成短背景，建议50—120汉字。
- [ ] 每个背景事实登记原文支持位置、角色与审核限制；含糊归属不补成确定主体，不添加当前案件未记载的产品/时间/结论。
- [ ] 先测背景冒用其他主体、source SHA变化、原句被覆盖、unknown被补全、把前缀作证据，再实现输出。
- [ ] 原文、前缀与索引表示分列，保留同一unit_id及新representation_id；新向量缓存按新文本SHA登记，原缓存只读。
- [ ] 用实验R的开发12题对比，未过门槛立即停止扩量；通过后才考虑未污染的保留组。
- [ ] 若开发通过，按T05同一方法准备并冻结R专用新保留12题。R0在这12题重新召回和重排，不复用K旧题分数；R1与其对照。

**验收：**最多60个有证据背景，无原文改写；两路索引确实使用新表示，实际送入重排的文本符合冻结干预；无收益则保持默认原表示并保存失败结论。

### T09 依赖驱动的增量维护

**预计：**1—2小时。**教材：**3.3.3增量更新与定期整理。

**文件：**新建`WORK/dependency_build.py`、`tests/test_dependency_build.py`；输出`maintenance/dependencies.jsonl`、`impact.json`、`coverage.json`及`reports/update_runbook.md`。

- [ ] 登记原始证据→法条/卡片→导航/证据包→索引表示/向量的直接依赖及输入SHA。
- [ ] 原文或法规快照变更时，标出直接及传递受影响产物；无关输入不重生成。
- [ ] 仅元数据修订不重新编码向量；实际embedding/BM25输入变化时必须更新对应索引。法条现行状态变化仍触发相关卡片与阅读状态复核。
- [ ] 先测单一条文变化、片段文字变化、无关文件变化、循环依赖和失败重建不得发布，再实现闭包与导出。
- [ ] 给出完整范围的覆盖清单和待整理队列；按主题分批整理时，记录未覆盖范围，不把随机抽样称为全库审核。
- [ ] 整理冲突时按时间、对象、产品、地域及业务环节限定，历史依据与现行判断分别保存，不用“保留最新”覆盖历史。
- [ ] 发布前跑代表性案例回归及已知失败例；回滚时同时回滚覆盖层与索引版本。

**验收：**至少3种实际可复现变更场景通过；重建影响可解释；未完成重建的版本不能激活。本方案提供手动运行步骤，不创建定时任务或后台自动监控。

### T10 从四机制扩展到现有12机制

**预计：**3—6小时资料与审核工作，按实测分批修正。**教材：**3.3.2索引组织、3.3.3覆盖整理、3.3.6模块化知识。

**文件：**扩展`knowledge/mechanisms.jsonl`及链接；新增`contracts/expansion_batches.json`、`navigation/label_coverage.json`和范围报告。

- [ ] 先完成M07退保、M08保障/免责，再处理M05/M06收益与性质、M03避债免税，最后按实际价值补M09/M10/M12。
- [ ] 每批2—3机制，复用已经合格的支持材料；首轮扩展全部文书去重后上限144份，不强行补足配额。
- [ ] 每个机制沿用公共因子：主体、动作、对象、环节、时间、事实来源；按机制增加少量产品/合同/资格等扩展字段。
- [ ] 已有四卡的回归仍保留；每个新增机制构造一个独立故事的三态回归，12机制合计36条只作范围冒烟与回归，不替代独立确认。
- [ ] 将官方27标签映射为已覆盖、部分覆盖、无足够规范/案例支持，解释机制与标签的多对多关系。
- [ ] 每批审核及机械检查通过后单独封存；法规或材料不足的机制发布partial，其余机制继续交付。

**验收：**以实际通过数量说明范围，不能用12机制声称官方27标签全部有完整法律边界。导航可扩展，T08索引干预只有在自身实验通过后才能按同规则扩展。

## 八 P2专项及进入条件

| 专项 | 进入条件 | 最小试验 | 停止条件 |
|---|---|---|---|
| 案件原型与统计摘要 | 用户确有跨案例归纳需求，关键因子可回源且unknown可分离 | 在已有144份以内计算确定性字段覆盖/共现，最多3—5个原型 | 类别受缺失数据主导、无法解释或不能回源时不继续聚类 |
| 因子重要性 | 有可靠结果标签与足够对照，能控制任务/版本/产品差异 | 先报告描述性关系和不确定性 | 无监督聚类特征不能变成法律因果、必要门槛或违规概率 |
| 表格/扫描源修复 | 发现实际影响判断的错行、金额/主体归属疑点 | 最多10份疑难文书，查看原页图并登记页码/表行 | 原件不可得则保留未知，不用模型补正文 |
| RAPTOR | 出现需跨文书综合、分层概览的真实查询 | 一个主题、可回源摘要树，与原库同预算比较 | 无新增有效证据或成本显著增加则不扩量 |
| GraphRAG | 出现明确多跳关系问题，局部链接无法满足 | 仅相关主体/事件子图，保留原文和关系边身份 | 事件/实体消歧不可靠或关系推断无证据时不扩量 |
| 多模态嵌入记忆 | 真实输入/证据包含必须视觉匹配的需求 | 单独立项、单独评价 | 当前纯文本风险识别不为展示效果先铺全库 |

每个专项首次最多投入半天，先写问题、基线、可测收益和成本，再启动。可将原型统计、疑难源修复作为针对性工作；不把所有专项列为必须完成。

## 九 运行命令与实现检查

下面命令为**本轮拟实现的统一CLI合同**，由`WORK/cli.py`和各任务提供；当前没有这些新入口，不能现在运行并宣称工作已完成。实施时各子命令必须支持`--help`、明确输出位置、默认不覆盖已存在结果，并在真正修改前完成输入冻结检查。

`WORK/config.json`初始配置合同如下。相对输入路径均相对`project_root`解析；路径与清单SHA必须在freeze阶段读取实际值。`authorization_file=null`表示API执行被禁用，不影响离线准备。

```json
{
  "schema": "finrisk-knowledge-organization-config-v1",
  "project_root": "C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai",
  "work_dir": "work/finrisk_knowledge_organization_v1_20261018",
  "output_dir": "outputs/FinRisk_知识组织增强_v1_20261018",
  "inputs": {
    "current": "outputs/FinRisk_知识库V2.1轻量收尾_20261015/effective_candidates.jsonl.gz",
    "documents": "outputs/FinRisk_知识库V2_20261012/normalized_final/data/documents.jsonl",
    "structured": "outputs/FinRisk_知识库V2_20261012/indexes/all9639_final/structured.jsonl",
    "raw": "outputs/FinRisk_知识库V2_20261012/indexes/all9639_final/raw.jsonl",
    "base": "outputs/FinRisk_知识库增量改进_20261018",
    "reviewed_release": "outputs/FinRisk_P0P1落实_20261018",
    "official_labels": "outputs/FinRisk_正式测试集V2_20261017/official_labels.json",
    "retrieval_runtime_record": "outputs/FinRisk_召回率校准_20261013/retrieval_results.jsonl.run.json"
  },
  "pilot_mechanism_ids": ["M11", "M01", "M02", "M04"],
  "source_document_target": 48,
  "source_document_cap": 60,
  "contextual_unit_cap": 60,
  "retrieval": {"top_per_route": 100, "rrf_c": 60, "bm25_weight": 1, "bge_weight": 1, "rerank_top": 100},
  "evaluation": {"K_development": 12, "K_holdout": 12, "R_development_reuses_K": true, "R_new_holdout": 12},
  "context_budget_chars": {"cases": 4000, "laws_and_guides": 4000},
  "api": {"model": "deepseek-flash", "authorization_file": null, "max_attempts_per_job": 3},
  "default_auxiliary_route_enabled": false
}
```

在ROOT打开PowerShell，设置本轮路径：

```powershell
$kbRoot = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai'
$kbWork = Join-Path $kbRoot 'work/finrisk_knowledge_organization_v1_20261018'
$kbOut = Join-Path $kbRoot 'outputs/FinRisk_知识组织增强_v1_20261018'
$kbPy = 'C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
```

按顺序执行：

```powershell
& $kbPy -X utf8 -B "$kbWork/cli.py" freeze --config "$kbWork/config.json"
& $kbPy -X utf8 -B "$kbWork/cli.py" legal --config "$kbWork/config.json"
& $kbPy -X utf8 -B "$kbWork/cli.py" cards --config "$kbWork/config.json" --phase pilot
& $kbPy -X utf8 -B "$kbWork/cli.py" navigation --config "$kbWork/config.json"
& $kbPy -X utf8 -B "$kbWork/cli.py" bundle-check --config "$kbWork/config.json"
& $kbPy -X utf8 -B "$kbWork/cli.py" eval-prepare --config "$kbWork/config.json"
```

`freeze`预期输出保护/输入计数及SHA；`legal`应输出43/24/67计数与依赖异常；`cards`输出4张卡及partial数量；`navigation`输出链接核验计数；`bundle-check`输出原句回读和拒绝测试计数；`eval-prepare`输出24输入/8组/12开发/12保留及参考隔离结果。预期的是符合合同的实际计数，不在代码里硬写成功回执。

检索和API分两步，先准备，再按有效授权执行：

```powershell
& $kbPy -X utf8 -B "$kbWork/cli.py" retrieve --config "$kbWork/config.json" --split development --variant base
& $kbPy -X utf8 -B "$kbWork/cli.py" api-prepare --config "$kbWork/config.json" --split development --experiment K
& $kbPy -X utf8 -B "$kbWork/cli.py" api-run --config "$kbWork/config.json" --split development --experiment K
& $kbPy -X utf8 -B "$kbWork/cli.py" evaluate --config "$kbWork/config.json" --split development --experiment K
```

检索子命令使用既有可运行Torch环境；上面的`$kbPy`适用于标准库步骤，`retrieve`的CLI应检测并转交冻结的检索解释器，或提示使用其明确路径，不能临时安装替换旧依赖。现有候选路径为`ROOT/work/finrisk_retrieval_20261012/.venv/Scripts/python.exe`，T00核验存在、模型/运行时指纹后写入config。

`api-prepare`只生成输入、唯一配对数、预算预留和待执行清单；`api-run`在没有匹配的有效授权或超预算时拒绝，绝不默认授权。保留组使用`--split holdout`，仅在候选配置冻结且holdout未污染时运行。R实验使用`--experiment R`和`--variant contextual`；执行前先跑T08前缀生成子命令`contextual-build`。

CLI应使`--experiment R --split holdout`明确解析到R专用的新12题，不解析到K保留集。T09提供`impact`和`rebuild-affected`两个子命令；T10使用`cards --phase expand --mechanisms M07 M08`这一明确机制列表的合同，不把所有12机制隐式重生成。

测试和封包：

```powershell
& $kbPy -X utf8 -B -m unittest discover -s "$kbWork/tests" -p 'test_*.py' -v
& $kbPy -X utf8 -B "$kbWork/cli.py" verify --config "$kbWork/config.json"
& $kbPy -X utf8 -B "$kbWork/cli.py" package --config "$kbWork/config.json"
```

`verify`返回实际清单/源文/指标核验结果；`package`先核查目标绝对路径，生成新zip并在WORK内新目录解压验证。没有旧结果时不得伪造“复算一致”；不对计算机其他目录执行递归删除或移动。

### 9.1 关键测试代码合同

以下测试写入`WORK/tests/test_contracts.py`。被导入函数是本方案要求新增的函数；先运行并观察失败，再实现。测试使用最小合成字符串，不能把样例当真实法规或处罚证据。

```python
import unittest
from legal_registry import checked_slice, dependency_closure
from evidence_bundle import require_current_fact
from navigation import reverse_links

class Contracts(unittest.TestCase):
    def test_range_rejects_bool_negative_and_overflow(self):
        for start, end in [(False, 2), (-1, 2), (0, 99), (2, 2)]:
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValueError):
                    checked_slice("甲乙丙", start, end)
        self.assertEqual(checked_slice("甲乙丙", 0, 2), "甲乙")

    def test_missing_dependency_never_complete(self):
        got = dependency_closure(["A"], {"A": ["B"]}, {"A"}, limit=32)
        self.assertEqual(got["status"], "partial")
        self.assertEqual(got["missing"], ["B"])

    def test_cycle_is_bounded_and_not_duplicate(self):
        got = dependency_closure(["A"], {"A": ["B"], "B": ["A"]}, {"A", "B"}, limit=32)
        self.assertEqual(got["status"], "complete")
        self.assertEqual(got["resolved"], ["A", "B"])

    def test_empty_roots_cannot_claim_complete(self):
        with self.assertRaises(ValueError):
            dependency_closure([], {}, set(), limit=32)

    def test_historical_case_cannot_be_current_fact(self):
        with self.assertRaises(ValueError):
            require_current_fact({"origin": "historical_case", "quote": "甲"}, "甲")
        require_current_fact({"origin": "current_input", "start": 0, "end": 1, "quote": "甲"}, "甲")

    def test_reverse_links_preserve_multiple_owners(self):
        got = reverse_links({"M01": ["A"], "M02": ["A", "B"]})
        self.assertEqual(got, {"A": ["M01", "M02"], "B": ["M02"]})

if __name__ == "__main__":
    unittest.main()
```

最小实现如下，分别加入对应模块；这只实现基础不变量，不能代替T01—T04的真实快照适配、角色/归属核对与完整API。

```python
# legal_registry.py
def checked_slice(text, start, end):
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
        raise ValueError("invalid source range")
    return text[start:end]

def dependency_closure(roots, adjacency, registered, *, limit=32):
    if type(limit) is not int or limit < 1:
        raise ValueError("invalid dependency limit")
    if not isinstance(roots, (list, tuple)) or not roots or any(not isinstance(x, str) or not x for x in roots):
        raise ValueError("nonempty article roots required")
    pending = list(dict.fromkeys(roots))
    seen, resolved, missing = set(), [], []
    while pending and len(seen) < limit:
        item = pending.pop(0)
        if item in seen:
            continue
        seen.add(item)
        if item not in registered:
            missing.append(item)
            continue
        resolved.append(item)
        pending.extend(x for x in adjacency.get(item, []) if x not in seen)
    remaining = sorted(set(pending) - seen)
    return {"resolved": resolved, "missing": sorted(missing), "unread": remaining,
            "status": "partial" if missing or remaining else "complete"}
```

```python
# evidence_bundle.py
from legal_registry import checked_slice

def require_current_fact(evidence, current_text):
    if evidence.get("origin") not in {"current_input", "scenario_given_fact"}:
        raise ValueError("historical or normative text is not a current fact")
    if checked_slice(current_text, evidence["start"], evidence["end"]) != evidence.get("quote"):
        raise ValueError("current fact quotation mismatch")
```

```python
# navigation.py
def reverse_links(forward):
    result = {}
    for owner, targets in forward.items():
        for target in set(targets):
            result.setdefault(target, []).append(owner)
    return {target: sorted(owners) for target, owners in result.items()}
```

还必须实现的真实拒绝路径见T01—T04/T08/T09；它们验证具体源文/版本/归属风险，不靠“测试数量足够多”验收。现有边界校验器只作参考，复用时补齐非bool整数及必要条件集合非空检查，避免空集合自动支持。

## 十 审核 成本和停止规则

### 10.1 审核分工

程序先检查格式、ID、SHA、span、链接、依赖和版本，助手再审核规范断言、条件与角色。只有新增断言、冲突或来源变化进入语义复核，常规导出不反复全文重审。

内容作者与审核者使用分离上下文，审核者可读取原文、法规及完整相关材料；不只拿作者摘要复述。同家族/同会话模型审核如实登记，不写成异源独立专家审核。每批一次审核和一次修复复审，仍有争议的部分隔离；其他合格条目继续推进。

评测相关性盲标隐藏方案、排名和参考，允许查询输入与完整文书；当前输入事实/规范适用判断另行检查。参考修订必须写单独版本和固定排名敏感性，不能覆盖原参考后只保留更高成绩。

### 10.2 请求规模和预算

| 范围 | 评分/判断规模上限 | 可复用项 |
|---|---:|---|
| P0案例重排 | 24题×100=2400评分槽位 | K0/K1相同案例输入只算一次 |
| P0最终判断 | 24题×2=48次 | 精确相同输入才可缓存 |
| P0检索相关性 | 至多24×20=480个query-file配对 | 两臂共享参考 |
| P1前缀重排 | R1开发12×100＋新保留12×2×100=3600槽位 | 原开发R0沿用P0相同输入；其他精确相同项可复用 |
| P1新增相关性 | 开发至多240＋新保留至多480=720配对 | 原开发参考不重复标注；新题不复用旧等级 |
| 可选P1最终判断 | 至多36次 | 原开发基线相同输入可复用；其余另算预算 |

P0/P1合计最多6000个重排评分槽位、1200个检索相关性配对，外加48次P0及至多36次可选P1最终判断。以上不等于实际HTTP请求数；失败、重试和缓存另计。开发门槛未过时不运行P1保留组。原型/多模态专项另做预算，不自动混入本轮。

优先用当前会话生成和审核48份材料及四卡，不全库重抽，不默认调用API生成数万前缀。API执行前按当日官方价格、序列化请求、最大输出、重试预留计算最坏费用；建议首版及P1合计先以2美元作为预算提案，**最终以本轮实际有效授权为准**。金额是硬上限建议，不是价格或费用预测。

每次请求预留最坏费用，未知usage保留完整预留；超额度不发出新请求。每个任务最多3次传输/格式尝试，取最早合格结果，不按得分择优。模型返回身份、字段与引文政策沿用冻结合同；不得在运行时无限放宽校验或自动扩大预算。

### 10.3 停止或降级

- 来源或版本失配：暂停受影响组件，先核查输入，不重跑全库掩盖问题。
- 法规现行/历史适用无法核定：随文标未知，不写确定法律结论。
- 主体/行为归属不清：保留原范围及歧义，不靠生成背景补齐。
- 卡片规范断言无法回源：隔离该断言；有意义时发布partial。
- 前缀开发对照无收益：停止扩量，不跑更多参数寻找好成绩。
- 保留集退步：维持原默认、交付失败结果和原因，不继续调同一保留集。
- API余额或有效授权不足：完成离线构建、请求准备和未执行清单，不假称实验已完成。
- 无法在计划时间完成专项：先交T00—T07，再按已有门槛处理P1/P2。

## 十一 分阶段交付与验收

| 交付点 | 必须包含 | 能证明什么 |
|---|---|---|
| D1资料与读取 | 4卡、67条注册、双向导航、证据包、冻结与回源测试 | 这批知识可定位、可读取、范围明确 |
| D2 P0首版 | D1＋24题分组评测、原始结果、误差归因、预算、采用决定 | 知识组织对这批话术的增量表现 |
| D3前缀实验 | 至多60新表示、真实双路索引变化、R对照及失败例 | 定向上下文是否改善所测检索 |
| D4范围扩展 | 通过审核的机制批次、27标签覆盖表、依赖维护和回归 | 实际扩展到哪些机制，哪些仍缺资料 |

最终报告须回答：完成了哪些任务；实际覆盖多少机制/文书/单元；哪些unknown/partial保留；性能变化发生在初召回、排序、证据阅读还是判断；有效分母及模型银标限制；成本和延迟；是否推荐采用，以及另一窗口应读取哪个版本。

可用于答辩的表述以实际结果为准：案例库、法规依据、机制核查清单和可追溯读取构成知识组织层；实验验证其在所测范围内的价值。不能把目录链接称为完整GraphRAG，不能把小样本门槛通过称为27标签全面验证，也不能把池内覆盖称为真实全库Recall。

## 十二 教材与现有成果对应

| 教材内容 | 书内页码 | 本方案任务 |
|---|---|---|
| 原始案例的最近邻偏置、边界和完整性信号 | 87—88 | T02、T04、实验K |
| 保留自然语言，结构化索引补充 | 88—90 | T01—T04；P2专项进入条件 |
| L0/L1/L2及条目之间横向链接 | 91 | T03、T04 |
| 增量更新、回源、冲突限定、全量覆盖清单 | 92—93 | T00、T07、T09、T10 |
| Agent按需使用知识工具及来源安全边界 | 93—96 | T04接口及交接；不代替另一窗口Agent开发 |
| 块特定背景前缀，同时改BM25和dense | 96—98 | T08、实验R |
| 核心＋扩展因子、案件原型及统计 | 98—99 | T02、T10、T11 |
| 多模态原始载体及记忆 | 100 | T11疑难原页/多模态进入条件 |

页码换算：PDF页码=书内页码＋8。条目数量、预算、任务命令、试验门槛和排期均为本项目工程设计，不能表述为教材规定。

参考材料：

- [教材3.3探索记录](C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_section33_exploration_20261018/findings.md)
- [最新P0/P1交付报告](C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_P0P1落实_20261018/本轮完成报告.md)
- [12机制及辅助检索试验](C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_知识库增量改进_20261018/验收报告.md)
- [E01—E04旧小批对照](C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E01-E04五小时实验_20261013/实验总报告.md)
- [E07/E06/E05旧探索](C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E07_E06_E05探索_20261013/实验总报告.md)
- [Anthropic原始方法](https://www.anthropic.com/engineering/contextual-retrieval)
- [OpenViking分层说明](https://github.com/volcengine/OpenViking/blob/main/docs/en/concepts/03-context-layers.md)
- [RAPTOR论文](https://arxiv.org/abs/2401.18059)
- [GraphRAG论文](https://arxiv.org/abs/2404.16130)
