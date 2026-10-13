# 五小时实验 runner 说明

实现文件：本目录 experiment.py。仅由 root 统一执行真实 GPU 实验；本子任务未执行 GPU 推理、未写实验成绩、未修改旧交付或主仓库。

## 冻结接口

CLI 参数：`--queries --scope-units --scope-reviews --mechanism-cards --mechanism-reviews --freeze --output --cache`。所有参数为本地路径。输出必须位于本轮 outputs/FinRisk_E01-E04五小时实验_20261013 内，cache 必须位于本轮 work 子目录且启动时为空。结果文件或任一 partial/run/failure/token/score sidecar 已存在即拒绝覆盖。

execution_freeze.json 的 `files_sha256` 是绝对文件路径到 SHA256 的映射。启动及完成均核验这些文件，冻结文件自身 SHA 也绑定到本轮推理和分数池。强制包含新 runner、五项输入文件、旧 E02 cohort/source packages、旧 E04 experiment.py；root 冻结其余旧代码、完整 index/data、缓存指纹和本轮评价器。

scope_review.jsonl 每行须含 unit_id、status（approved_model_review/rejected）、scope_units_sha256（整个 scope_units.jsonl）、row_sha256（UTF-8 canonical JSON，ensure_ascii=False/sort_keys=True/separators=(',',':')/allow_nan=False）、source_sha256、reason、human_approved=false。mechanism_review 同理使用 card_id/mechanism_cards_sha256/row_sha256/reason/human_approved=false。

## 检索与真实推理

保留原 9639 文书和 65475 单元，全量竞争。原 frozen helper 只读验证人口、来源和模型契约；不复用任何旧 query vectors 或旧 reranker logits。

- B0：原版 BM25+BGE，RRF 1:1，rerank100。
- S1：仅审核通过且非 ambiguous_unchanged 的表示和返回范围替换。
- C2：S1 的同一批准集合，增加经批准的逐字 extractive prefix。
- W4：原版 BM25:BGE 的 RRF 权重 2:1，其余同 B0。
- M3：原版两路加真实 BGE 机制卡支持单元路，RRF 1:1:1；card_top_k 固定为 2，卡总数最多 5；最终 rerank/返回仍使用原案例单元和原 context。

各原检索路 Top100、RRF k60，最终各方案候选恰为100；BGE/reranker 使用原 CUDA/float16/batch16/max_length512 和相同模型、tokenizer、软件版本。42 输入统一编码一次。旧文档缓存由 frozen seed helper 验证模型/有序文本/array SHA 后拷入新的隔离目录；未变文档不重新编码。S1/C2 全数组 shape 和父 unit 顺序保持一致，实际不同文本表示跨两方案按 representation_id 去重编码一次。representation_id 由父 unit ID 和完整文本 SHA 派生。批准行数、表示行数、实际 changed_text 行数、新编码行数分别记录。

本轮分数池键绑定 query ID/text SHA、unit/file/source SHA、indexed text SHA、由文本 SHA 派生的 representation ID、完整模型 runtime、manifest 和本轮输入 SHA。相同模型输入跨方案只真实打分一次，写出首次方案和共享 provenance；相同 ID 改文本必须另打分。评分池每查询独立，不接受旧分数导入。模型内部 token audit 之外，在推理前保存带完整输入 SHA 的 token 长度检查；超512时拒绝静默截断，失败 sidecar 保留。

## 回源与返回契约

每个 scope segment 的 text/span 严格匹配 source，indexed_text 严格为各 segment.text 的换行连接。新 scope 必须含原 unit 原话；有重复匹配时须覆盖所有原话位置，否则拒绝。ambiguous_unchanged 必须保留原索引文字且 prefix 为空，任何方案不装饰其原返回。

S1/C2 修改的命中携带 scope_profile='5h-scoped-v1'、scope_review_status='approved_model_review'、original_unit_text、original_unit_spans（全部匹配位置）、source_text（segments.text 无缝连接）、source_segments（逐段 text/span）、source_spans、representation_id。正文为：

```
【命中原话】
<original_unit_text>

【命中原话的对应原文（逐段独立，不合并主体）】
<各段原文，间隔为旧协议的 [原文间隔，分段摘录]>
```

C2 有 prefix 时在正文最前增加 `【仅适用于下方命中片段的背景（原文摘录，候选）】`，保存 prefix_claims/source/unit/SHA/model-review 绑定。原候选 case/behavior 映射只继承，不新增关系；occurrence_ambiguity/matched_occurrences 保留重复源位置，不把并列两行当同一事件或角色。

机制卡至少两份来源。每个 support 验证 file/unit/source SHA、逐字 quote/span，并要求支持区间与原 unit 的真实原文匹配位置有非空交集；这允许引用恢复被截断的段首，同时拒绝召回同文书中无关联区间的 unit。概括和归因必须由独立 mechanism_review 审核，卡片文字从不作为原文证据。

## 验证和限制

runner_tests_red.log：最初14项因缺失实现失败。runner_tests_vector_red.log：相同文本表示的分数绑定及编码剂量字段先失败。runner_tests_contract_red.log：实际冻结查询标记的契约先失败。runner_tests_support_red.log：完整原段与截断父 unit 的包含关系先失败。runner_tests_green.log：最终21项全部通过；包括真实42输入/旧manifest键、24源候选及5卡的结构回源检查，后者仅在内存使用 rejected 审核，不创建或冒称语义批准。runner_cli_help.log 记录 CLI。合成推理对象仅验证调用编排与输入绑定，不属于真实 GPU 实验结果。

只有3–5张卡，Top2 仍可能向多数查询给出许多或全部支持单元；run log 记录实际卡选择组合分布，报告必须说明这项局限。局部24候选变化不代表全库切分收益。真实 GPU 成绩与采用结论由 root 的后续统一执行和新评分产生。
