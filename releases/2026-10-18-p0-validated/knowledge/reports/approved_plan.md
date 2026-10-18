# FinRisk 全库证据读取修复实施计划

> 按subagent-driven-development执行，test-driven-development先测后改；审核不需要用户再次逐项确认。用户已确认范围，当前ROOT无Git仓库，使用新WORK/OUT隔离。

**Goal:** 完成全库读取、规范证据选择与多风险覆盖三个P0，并准备独立新题。

**Architecture:** 只读全库消费索引＋原资料的固定版本适配＋独立证据装配与覆盖报告；现有BM25/BGE/RRF/DeepSeek排名不动。

**Tech Stack:** Python标准库、SQLite、JSONL/GZIP、SHA256、既有只读阅读器。

## 路径

ROOT=C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai

WORK=ROOT/work/finrisk_evidence_runtime_v1_20261018

OUT=ROOT/outputs/FinRisk_知识库P0修复_20261018

旧工作目录work/finrisk_knowledge_organization_v1_20261018及封存输出只读；写入文件均在上述WORK/OUT。

## A 全库读取（full_reader.py、tests/test_full_reader.py、full_reader/）

- [ ] 冻结全库5项版本、4类输入SHA、旧697载荷清单及source文件。扫描有效/隔离分布，不先宣布110878都通过。
- [ ] 先测试：未知ID、重复ID、错来源/候选、旧绑定缺补丁、bool/越界span、DB篡改、错版本、只读写入失败、有界缓存。
- [ ] 实现build_full_reader(target)及FullKnowledgeReader(root,expected_manifest_sha256,expected_versions)。原unit/source/candidate内容保存不重写；压缩行可zlib，键为稳定ID；源自旧scope的只读层继续复用。
- [ ] 完成全量机械回读和旧960位置逐值一致；报告构建/启动/读取耗时与实际行数、隔离原因。无模型调用。
- [ ] 独立规格审核，再做代码质量审核；影响正确性的缺口必须修正。

## B 适用范围侧表（scope_author/、article_scopes.jsonl）

- [ ] 内容作者按实际67条条文/来源登记范围；每项非unknown值附literal依据、来源身份及模型解释限制。
- [ ] 重点核对L001-A0116/L001-A0131与L005-A0016的主体/产品；其余条文逐条保守登记，不凭常识编排法律效力。
- [ ] 独立审核同ID/同版本/原句/范围，未知不填false，隔离来源不新增准入。

## C 装配与覆盖（scope_selector.py、risk_coverage.py、runtime_facade.py、tests/）

- [ ] 先写真实反例与拒绝路径：投连不使用万能特有要求定性、代理/公司分别读取；未知不被硬过滤；不得拆例外；范围证据必须来自current input；复数机制不被2个上限截断。
- [ ] scope_selector.match_article(registered_scope,scope_facts)返回matched/conditional/mismatch及理由；校验scope_facts身份/引用但不冒充事实语义审核。
- [ ] risk_coverage.analyze_coverage(text,available_cards,read_ids,checked_ids)给候选/触发span/未检查/未映射/官方标签缺口；whole_input_risk_free_supported固定false，读取不等于判断。
- [ ] RuntimeKnowledgeFacade复用固定法规/机制资料并接入全库读器，六个原操作保留；新get_evidence_bundle能输入当前文本与明确范围、独立报告覆盖/省略/依赖与精确字符预算。
- [ ] 同一已知失败输入的旧/新装配对照，只报告工程指标；不伪称新判别模型效果。
- [ ] 独立规格/代码审核，修复与针对性复验。

## D 新题及交付

- [ ] 独立作者36条新自然话术＋分组＋模型银标；不读取旧题/旧模型输出，12机制和多风险均覆盖，正常与事实不足明确。
- [ ] 审核输入自然性、边界、参考身份和重复组，修复后冻结SHA；与模型请求分离。
- [ ] 冻结输入复验，生成统一cli/接口/未执行项说明，清单及ZIP；新目录真实解压，回读法规/全库索引与代表性案例/测试，记录实际耗时。
- [ ] 明确全量机械验收≠全量语义审查；本轮新题未调用付费模型做判别；Agent在线接入和P1全库召回估计单独列出。

运行使用已验证的标准库解释器C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe，参数-S -X utf8 -B。测试从WORK执行 `-m unittest discover -s tests -p test_*.py -v`；不安装依赖，不读取密钥。
