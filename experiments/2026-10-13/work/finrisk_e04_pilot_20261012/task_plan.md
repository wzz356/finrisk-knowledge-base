# E04小批量融合与重排实验 Implementation Plan

> **For agentic workers:** Use executing-plans or subagent-driven-development to execute the following tasks with verification. Independent query preparation and experiment implementation use dispatching-parallel-agents; completed implementation is reviewed for specification first, then code quality.

**Goal:** 在当前9639份V2离线候选库上，比较融合权重和重排深度，按案例/返回片段是否帮助风险判断选出可继续验证的配置。

**Architecture:** 新建隔离实验目录，原代码、知识库、冻结50题、旧评分与应用默认配置只读。开发集复用已冻结真实BM25/BGE路由，重排Top100的同输入分数仅在来源、查询、代码、模型与运行参数绑定一致时复用；额外候选使用同一本地真实reranker。确认集在配置选择后才运行，使用新来源和新措辞，不读取360份预留文书。评分隐藏配置、排名、已知正例，已有评分只按同查询、同源和同返回文本复用。

**Tech Stack:** Python标准库、既有GPU Python、冻结runner.LocalModels、BM25/BGE、RRF、bge-reranker-base、SHA256与JSONL。

缓存边界：旧vector_cache只读；必要的已验证文档缓存复制到work/finrisk_e04_pilot_20261012/vector_cache，新查询缓存只在新目录写入。所有新评分输出仅新E04目录；同phase恢复需相同输入绑定，禁止旧数据目录和输入别名作为输出。

## 授权与边界

用户已同意先做E04小批量实验，并明确要求“规划，然后开始”，由助手完成模型判断。无需再次请用户审批同一范围。无付费API，无线上部署，无应用接入，无自动发布GitHub，无全库内容审核。派生判断只记model_review，不生成真人批准。工作只在新work/outputs目录；实验不修改任何Git仓库文件，不需要为只读基线另建worktree。

## 实验设计

- 四个配置：A0 BM25:BGE=1:1、RRF k60、rerank深度100（原基线）；A1 2:1、深度100；A2 1:1、深度200（最多为两路真实并集数量）；A3 2:1、深度200。
- 单路Top100、RRF按排名而非原始分数融合、单位按分数降序和unit_id稳定排序；结果沿用V2文书聚合及完整上下文。
- 开发集12题：营销5题含已知失败Q009/Q012、其他业务4题、边界3题，其余固定种子选择。是诊断开发集，不报告为27类代表样本或独立金标。
- 确认集10题：从9639允许集合选取与旧50题锚点不重叠的来源，6条业务风险输入、4条条件/否定边界输入。配置冻结前不依据确认集成绩调参。确认集由模型构造，明确共同偏差与小样本限制。
- 对照结果Top5逐项判断返回片段帮助度0–3，≥2有用；同时判断全文帮助度。有用、边界对照和无关分开，边界案例不能直接认定输入违规。
- 主指标：有用片段@5；辅指标：至少一段有用片段覆盖、全文帮助度、模型误导标记、已知锚点辅助命中、阶段丢失、耗时。固定5个位置分母，缺席记无支持。
- 开发集选择规则：片段有用率优先、覆盖不低于A0、误导标记不高于A0；并列按较浅重排/接近基线的配置选。没有合格改善则保留A0。
- 确认集仅测A0与开发选择配置，允许结论为没有改善或不值得扩大。若开发没有改进，确认A0及预先定义的A3探索对照，但不称A3为胜者。

## Task 1：冻结输入与名单

Files: outputs/FinRisk_E04小批量实验_20261012/design.md、dev_queries.jsonl、confirmation_queries.jsonl、input_freeze.json。

- [x] 核对A0结果、查询、投影、runner/adapter、字典、评分与源SHA，保存保护指纹。
- [x] 固定种子20261012选12题，记录分层、强制失败题和实际名单。
- [x] 独立准备10题确认集，附来源、原话、条件、用途和文本SHA；冻结后再选配置，确认分数不参与开发选择。

## Task 2：实现实验工具

Files: work/finrisk_e04_pilot_20261012/experiment.py、test_experiment.py。

- [x] 先写失败测试：加权RRF的排序、路内重复不叠加、截断与缺失路、非法权重、100/200候选差集、分数缓存绑定、结果文书聚合保留来源。
- [x] 实现weighted_rrf(routes, weights, k=60, top_k=200)，使用从1开始的排名并去除路内重复，禁止用原分数直接相加。
- [x] 实现开发接口：读取旧两路及Top100真实rerank分数，核对精确查询/模型绑定，额外候选统一打分；输出四配置真实阶段、来源及缓存来历。A0须逐项复现原结果。
- [x] 实现确认接口：同冻结模型真实BM25/BGE路由，再跑A0和已选配置；共享同查询的编码与候选评分，不用模拟向量/规则重排。
- [x] 运行测试，先规格审查再质量审查；只修实验工具重要问题，不改冻结基线。

## Task 3：评分与开发选择

Files: work/finrisk_e04_pilot_20261012/evaluate.py、test_evaluate.py；outputs下dev_results、blind_pool、judgments、dev_metrics、selection.json。

- [x] 先写失败测试：新文本不继承旧片段评分、同file不同query不复用、逐字引用/来源校验、固定5分母、缺少评分拒绝计算完整结果、确认选择锁定。
- [x] 生成盲池：每query-file一个池对象，全文与所有实际返回上下文绑定SHA；盲评分包不含算法、排名、已知正例。
- [x] 复用同query/同源/同context的已有分数，新出现的全文/上下文由当前会话模型实际阅读判别；正评分至少一段逐字原话，未知保留。
- [x] 核验评分全集和引文、统计四配置；依据预先定义规则写selection.json并冻结SHA。

## Task 4：确认与交付

Files: outputs下confirmation_results、confirmation_judgments、confirmation_metrics、实验报告.md、失败样例.md、verification.json、delivery_manifest.json。

- [x] 配置选择冻结后实际跑10条确认查询，基线和选择配置使用完全相同输入和返回上下文规则。
- [x] 独立盲评并核对来源，不因确认成绩再调参；单列正常/边界输入的错误类比风险。
- [x] 给出开发与确认的实际指标、逐题变化、失败机制、局限、实测耗时、下一步是否值得扩量。
- [x] 核验记录全集、源SHA、阶段与模型来历、评分缺口、保护对象未改，保存可复跑入口和成果。

## 检查点

当前：本轮E04首次受控小实验已完成。开发48条、确认20条真实检索结果；132个配对及132个片段模型评分无缺项。保留A0，A3确认无主指标改善。交付前核验与55项测试（54通过、1硬链接权限跳过）通过，报告独立核对无P1/P2。交付清单已保存，记录本轮成果及实现/日志指纹。盲评只指方法/排名盲：部分确认评分者接触query_task，限制详见报告和notes。没有完成全部锦上添花、全库人工金标或应用接入。
