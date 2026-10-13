# E05 编排说明（代码验证，不是实测结论）

本文件对应 `e05_runner.py`。仅写新编排和必要测试；没有运行正式聚类、真实 GPU 编码或正式检索，没有生成模型摘要，没有更改旧 runner、V3、原交付或生产默认。

## 命令

使用已有 GPU Python，建议带 `-X utf8 -B`。示例中的新摘要/目录文件由 root 在真实簇输出后逐断言写入和审核。每次 cache 必须是新 work 内尚不存在的子目录；输出及侧车任一已存在即拒绝。

```powershell
$gpuPython = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_retrieval_20261012/.venv/Scripts/python.exe'
$e05Code = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_e07_e06_e05_20261013/e05_runner.py'
$e05Out = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_E07_E06_E05探索_20261013'
$e05Work = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_e07_e06_e05_20261013'
& $gpuPython -X utf8 -B $e05Code cluster --nodes "$e05Out/leaves.jsonl" --clusters 4 --output "$e05Out/e05_clusters_l0.json" --cache "$e05Work/e05_cache_l0" --freeze "$e05Out/e05_cluster_l0_freeze.json"
& $gpuPython -X utf8 -B $e05Code cluster --nodes "$e05Out/e05_summaries_l1.jsonl" --clusters 2 --output "$e05Out/e05_clusters_l1.json" --cache "$e05Work/e05_cache_l1" --freeze "$e05Out/e05_cluster_l1_freeze.json"
& $gpuPython -X utf8 -B $e05Code cluster --nodes "$e05Out/e05_summaries_l2.jsonl" --clusters 1 --output "$e05Out/e05_clusters_l2.json" --cache "$e05Work/e05_cache_l2" --freeze "$e05Out/e05_cluster_l2_freeze.json"
& $gpuPython -X utf8 -B $e05Code retrieve --queries "$e05Out/queries.jsonl" --leaves "$e05Out/leaves.jsonl" --directory-nodes "$e05Out/e05_directory_nodes.jsonl" --tree-nodes "$e05Out/e05_tree_nodes.jsonl" --freeze "$e05Out/e05_retrieve_freeze.json" --output "$e05Out/e05_results.jsonl" --cache "$e05Work/e05_cache_retrieve"
```

cluster 最少参数为 `--nodes --clusters --output --cache`，`--leaves` 默认指新输出的 `leaves.jsonl`。`--freeze` 在 cluster 可选；省略时仍快照全部必要依赖 SHA 并在结束时复查。正式执行建议总是提供 freeze。retrieve 的 freeze 必填；不能选择只跑某一 arm。

## 冻结格式和必需依赖

freeze 格式为 `{ "files_sha256": { "绝对路径": "64位小写sha256", ... } }`。开跑核对每一项和必需集合，结束再核对所有项与 freeze 文件自身 SHA，拒绝漂移。`dependencies(e04,demo,old_log)` 返回公共必需集合；已保存同集合到 `e05_required_dependencies.log`，可通过导入本模块及 `modules()`、`read_json(e04.LEGACY_RUN)` 获取，无 GPU 调用。

公共集合包含自身 e05 代码、冻结 E04 编排、旧 backend/adapter、旧 5h 编排/显示层、V3 demo、原 prepared manifest/structured、旧 all9639 run/results、Desktop sparse/tokenization 源码、9639 normalized sources、旧 scope_units/scope_review、24源 cohort，以及旧 structured 文档 cache 的 JSON/NPY 对。原 E04/backend/adapter/manifest/runtime SHA 守卫继续执行，旧代码不作改动。

cluster 在公共集合之外要求 nodes/leaves。retrieve 还要求 queries/leaves/DIR/TREE 和原 V3 `queries.jsonl`、`input_freeze.json`；16 查询的 ID、文本和顺序必须与原 V3 相同。建议 root 把真实三次 cluster 输出、各层摘要、逐断言源审核、目录审核和对应输入包一起加入 freeze：程序核对 SHA；断言语义由 root 审核。

## 节点与算法契约

节点都有 `node_id/text/level/descendant_unit_ids`。21 叶必须和已批准 scope 的文本、segments、source SHA、file/unit ID 完全一致。节点后代非空、唯一，且只在 21 叶白名单。每次聚类输入必须完整硬分区21叶；阶段只接纳 21个level0→4、4个level1→2、2个level2→1。

TREE 必须恰有 4个level1、2个level2、1个level3。每个摘要节点还需要 `child_node_ids`，可直接采用上次簇输出的 `clusters[*].member_node_ids`：L1 指21叶 node ID，L2 指4摘要 ID，L3 指2父 ID。每层恰好分区下层，后代 unit 集合必须等于子节点并集。DIR 全部后代合计需覆盖21叶，其 node ID 不得与 TREE 重复。

球面 KMeans 用 numpy，固定 seed17，输入/中心 L2 归一化，余弦分配，零/非有限向量拒绝；空簇从非单成员簇最弱余弦成员确定性搬入。它是硬聚类小样本原型，不是 RAPTOR 的 UMAP/GMM 软聚类复现。簇输出包括成员实际文本及 SHA、规范化向量路径/SHA、中心、固定种子、空簇修复数、model fingerprint、runtime、token audit/summary、21叶来源和原歧义标记。

旧短索引有6叶 evidence_ambiguous=True；F004155 的已审范围仍含 occurrence/attribution ambiguity。它们在已批准 scope 范围内接纳，原标记逐叶记录，不把旧歧义重写为确定主体或同事件。摘要和后续判断由 root 保守处理。

## 三 arm 的真实运行

仅 dense 导航不同。BM25 为原65475文本、k1=1.5/b=.75/weight=1；BGE 和 reranker 都用旧本地模型与冻结 runtime，BM25/BGE 两路 Top100，RRF 等权/k60/union最多200/rerank100。最终 adapter.aggregate 保存 file/case Top20，另保存 file Top5；已审21叶的显示复用 V3 scoped_hit，model indexed fields 仍为原单元。

旧文档向量只读校验 source/text/model/runtime/cache SHA 后复制到新 cache；不重编码原文档。16查询在同轮新编码一次，DIR+TREE节点新编码一次。B0 与旧原行 tie break 一致。DIR/TREE 将完整原库 cosine 与导航节点 cosine 一同 Top100 排序，再按节点排名、节点 score、稳定 unit_id 展开合法叶，去重取最多100；不在21叶内制造 rerank100。展开分数明确是节点 score，不是叶子的独立 cosine。

保存各查询/arm 的 BM25、dense、node hits、逐叶 accepted/重复/容量跳过 expansion provenance、RRF、真实 rerank、模型分数 binding、实际新重排数/精确共享数及阶段耗时。绑定包括同轮 run_id、query ID/text SHA、unit/source/indexed text SHA、manifest、runtime、所有执行输入。每查询新池，不能复用旧 V3 logits 或旧查询 dense 分数。

embedding/rerank token 审计由旧 LocalModels 记录实际 input/used/truncated。导航文本另有 SHA 绑定的 token preflight，超512在编码前拒绝供 root 修订/重新冻结；原文 rerank 按原模型行为记录实际截断，不伪报0。摘要只参与召回导航，不能作为最终引用证据。

## 已做验证与尚缺事项

- `e05_tests_red.log`：12项因实现缺失失败；`e05_layer_red.log`：完整分区守卫缺失失败；`e05_scope_red.log`：复现错误拒绝已审但原短索引带歧义的叶。
- `e05_tests_green.log`：15项通过，覆盖 seed/覆盖/空簇、非法向量、节点白名单/空/重复、原 dense 不变、节点竞争后展开/去重/score语义、叶绑定、树分区/并集、同轮严格分数绑定、cache/output拒绝覆盖、freeze漂移。
- `e05_scope_preflight.log`：只读来源/范围核对通过，9639文书/65475单元/21 approved/21 leaves，GPU_run=False。
- CLI help 和语法检查只验证入口，不构成模型实验。单元测试中的小数组和 rerank 测试模型是合成控制测试，不是实际语义评价。

尚缺由 root 正式执行：三次真实 BGE 编码聚类、4/2/1摘要和逐断言源审核、简单目录审核、冻结正式文件、同轮16×3真实全库检索、统一Top5语义判断及采用/后置结论。上述未完成前不能声称 E05 增益。
