# E02工具独立只读审查

状态：**PASS**。最终代码SHA与实现者交付一致，无未解决P1/P2问题，可进入既定本地GPU实验。审查者尚未运行GPU、读取本轮结果或作收益判断。

## 范围与证据

按本轮task_plan.md及design.md审查evaluate.py、experiment.py、对应测试，并只读追踪冻结E04/V2评价及检索函数。审查者仅持久化此报告，未改旧库、旧工具、生产缓存、.env或360正文，未重复完整旧索引预检。使用verification-before-completion原则，结论依据实际回归和逐项代码核验。

- 独立运行评价器16项回归：全部通过，退出码0，含真实文件prepare→incomplete→summarize往返。
- 最终修复后独立运行检索23项回归：全部通过，退出码0，含66条编排、4400条评分来历、冻结缓存仅复制绑定pair及候选整文件漂移拒绝；评价器16项也重新全部通过。两份CLI帮助成功退出。
- 额外负向夹具：同步重渲染的虚构原body、篡改source_segments区间、篡改source_spans区间均被拒绝。
- 实际24条前缀按author input的原单元/完整来源重新机械核验：24通过、45条精确引文、最大176字符；prefix_quality绑定的6份prefix/review文件SHA全部相符。此核验不替代已完成的逐条同主体/同行为peer审核。
- 基于现有文件与代码核验，未加载本地GPU模型或调用推理。编排合成测试使用模拟数值，仅证明调用与记录契约，不能作为收益或真实推理证据。

最终审查版本（SHA256）：

|文件|SHA256|
|---|---|
|evaluate.py|e6f7d1b3b9646b45384fd50b9605b076b73dcc1cc7f22c9b68519aeb40ed5e4d|
|test_evaluate.py|7a2ceb971bdd0b78f17fa64142fef0be1e114cad72927786e47feaf406c94cad|
|experiment.py|6f671bd3234d56645022cf35e99d40417c48def1b3df2b3eb5e59800c243e353|
|test_experiment.py|30469606d04ff6a3ea29e02967f1a4e0f30aea629dc34ffe664789b2c2c44941|
|prefix_quality.json|0a2915efd487d41fa1a490c70f1f91b5833fac690e5163e9a399ec92e7abb2ac|

本次最终差异仅增加validate_quality、load_replay中的整文件校验、quality始末输入跟踪及相应负向测试；已核对实际prefix/review文件通过新guard。实现者最后交付的实验器与测试SHA与上述实际读盘值一致，主代理确认以此版本冻结执行。

## 规格核对

|边界|结论与依据|
|---|---|
|原文与区间|有背景时先把base_context_text交给原V2规则核验；source_segments逐段与source_spans对应并逐字回源，原body及间隔标记都必须一致，再重建背景显示文本，没有放宽原校验。|
|前缀与原话|标签限定、1–3引文、180字符、精确区间和模型审核状态均强制；prefix_text只能是label：quote逐行渲染。评分引用仍须同时在实际片段和完整来源连续出现，派生标签不能当原话。|
|评分包盲化|评分池剔除算法、排名、分数、unit身份、锚点、作者预期及query_task；未隐藏实际返回的背景存在性，不能声称对干预完全盲。完整来历在独立provenance保留。|
|重新评分与分母|不允许外部旧pool/judgment复用；本轮同query-file全文只评一次，不同实际文本独立评分。固定每题5位置、有用>=2，缺全文或片段评分为incomplete，不当0或完整。|
|版本与隔离|评分输入绑定queries/results/sources、E04/V2评价代码与新evaluate.py SHA；新评价phase必须是E02输出子目录。检索输出及全部侧车拒绝已有文件，缓存必须是E02 work的空子目录。|
|全库P1|运行前要求9639文书/65475单元；真实SparseRetrievalIndex以完整overlay重建，真实BGE全矩阵取Top100；RRF1:1/k60及实际rerank100沿用冻结模型参数，无规则替代或旧语义分替代。|
|增量向量|复制并验证冻结文档向量绑定，旧缓存仅只读；只将审核单元的prefix+原unit文本做真实编码并覆盖对应行，其他行复制保留；当前24/24通过，即24变化行。|
|原文不可编辑|make_overlay只替换审核单元的索引text，其余字段与24以外单元保持原值；原单位和上下文用于聚合，随后仅装饰实际winner unit。|
|P0与P2|P0原files/cases/全部stages逐字复现；P2从P0深拷贝，只给实际获胜且在approved中的单元补背景，保留indexed_text、身份、源区间、分数、排名与stages。不能按file归属给另一个winner补背景。|
|token预算|按本轮冻结规格使用512；真实tokenizer先按truncation=False检查query embedding、变化文档embedding与每题rerank100的组合输入，超限即拒绝。冻结base缓存的truncated记录也拒绝。主代理已明确本轮没有额外256限制。|
|完整记录与来历|保存双路、RRF union/Top100、rerank候选/排序、files/cases、P0/P1 score_pool与模型/文本/来源/输入SHA、prefix剂量、token审计和实际耗时来历；66条/22题及运行末SHA检查通过才发布完成文件。|

## 发现与处理

1. [P2，已修复] 初版review只绑定prefix_text/source SHA，重复原句的claim.span或link_reason改变可能保持旧review摘要不变。最终版以独立prefix_quality.files_sha核对实际prefixes/review整文件，并将quality纳入运行始末SHA跟踪；旧摘要不变而span或link_reason变化的负向回归及实际文件校验均通过。当前24条没有发现实质内容错误。
2. 三arm完整性由runner的66条/22题门槛及主代理最终verification负责；评价器自身验证每个已出现arm覆盖全部输入及judge完整性。本审查不要求扩展为通用评价系统。

未解决问题：无。

## 判定限制

代码审查通过仅意味着可进入既定本地GPU实验，不代表本轮真实调用、零截断或收益已经发生。24单元为有目的的诊断抽样，22输入为已用回放；语义前缀及最终评分均为模型意见，不能当独立真人金标或全库收益证据。F004155的多出现位置/主体歧义仍保留，批准的文书身份不推出个人实施所有片段行为。
