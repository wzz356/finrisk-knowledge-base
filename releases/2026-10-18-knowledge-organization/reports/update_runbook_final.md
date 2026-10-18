# 最终依赖登记与手动维护

最新图为 `maintenance_final/dependencies.jsonl`。旧 `maintenance/` 及其 3950 个节点原样保留，新图共 4313 节点。主 CLI 的 `impact` 与 `rebuild-affected` 可使用原有 `DependencyGraph` 直接加载新图；没有新增激活接口。

## 已有产物与未来任务

本次补登记实际存在的 20 条 literal 前缀、20 条检索表示、20 个已计算 float32 向量行及其 `(20,512)` 矩阵，以及既有上下文缓存绑定和 controlled 缓存绑定。`maintenance_final/vector_rows.jsonl` 保存每行在 NPY 文件中的半开字节范围及 2048 字节 SHA256。使用标准库读取 NPY v1 头、类型、形状和有限数值；没有加载模型、调用编码器或重新生成向量。

输入侧表的行指纹与原矩阵文件 SHA 同时登记。前缀文字变更会使相应表示、向量行、矩阵和绑定失效；矩阵文件字节变化会保守地要求重核全部已登记行。登记 SHA 是对现有文件的核验，不等于自动生成了新向量。

实际 20 条 literal 前缀的直接依赖仅为当前 `knowledge/source_spans.jsonl` 中所引原句及原 pilot 单元文本。它们不读取法规或卡片解释；法源效力元数据变化不应无端重编码这些前缀。前缀可能涉及其他主体，既有归责限制继续保留。

旧图 78 个 `FUTURE_PREFIX` 和 78 个未来 contextual embedding 节点仍是 pending，未借这次补登记冒充完成。新图总 pending 队列为 1961 项，包含旧规划节点、未来索引/重建工作及变更后的复核门禁；实际已有的 20 个向量行使用独立 `ACTUAL_VECTOR_ROW` 节点标记 present。

扩展范围实际为 12 张卡、59 份全文、78 个原句片段、109 个案例链接，及 12 机制导航。正文和元数据分开投影：法源元数据仍传递到卡片 review、导航和阅读包复核。扩展反向链接保存在 `expanded/navigation/index.json` 内，未虚构单独的反向链接文件。

## 使用最新图

先在 WORK 新目录中复制候选输入，保留原包。路径应指向真实候选副本，下面的示例只用于这次已创建的文字变化副本。

```powershell
$kbPy = 'C:/Users/11051/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$kbWork = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/work/finrisk_knowledge_organization_v1_20261018'
$kbOut = 'C:/Users/11051/Documents/Codex/2026-10-09/c-users-11051-desktop-agent-ai/outputs/FinRisk_知识组织增强_v1_20261018'
$graph = "$kbOut/maintenance_final/dependencies.jsonl"
$candidate = "$kbWork/maintenance_final_task/s/p/in"
& $kbPy -S -X utf8 -B "$kbWork/dependency_build.py" impact --graph "$graph" --root "$candidate"
& $kbPy -S -X utf8 -B "$kbWork/dependency_build.py" rebuild-affected --graph "$graph" --root "$candidate" --stage "$kbWork/maintenance_final_task/manual_stage_001"
```

`--stage` 必须为从未存在的新目录。默认重建器只暂存当前输入的字段投影；它不重新提取原句、生成前缀、改写卡片或重算索引。受影响的向量节点由暂存器保持 pending，后续矩阵/绑定因依赖不完整而不能完成。即使仅有无关文件变化、暂存状态为 staged，也仍返回 `activation_allowed=false`。

暂存回执沿用通用暂存门禁标签，不用其中的历史 T07 标签判断 T07 的实际完成状态。本次登记没有生产重建器和发布激活能力。需要发布新版本时，仍须由相应生成/复核流程真实完成受影响产物、保存文本/模型/配置/输出指纹并通过代表性案例与已知失败例回归。

## 核验与复现

`maintenance_final/verification.json` 保存旧输入及新登记输入前后 SHA、原始缓存只读指纹、无环与基线空影响检查，以及三种真实副本变化。`maintenance_final/scenarios/` 和 WORK 的 `maintenance_final_task/s/` 保留每个变化的影响及暂存回执。

- 前缀文字变化：应影响 1 条实际前缀和 1 个向量行，并使矩阵及 controlled 绑定失效。
- 法源元数据变化：应触发相关扩展卡片 review，实际 literal 前缀及其 20 个向量行均不受影响。
- 无关文件变化：不触发已登记产物重建。

定向测试位于 `WORK/maintenance_final_task/test_finalize_maintenance.py`，同时检查真实向量行哈希、截断 NPY 拒绝、旧节点保留、literal 依赖及三种副本结果。首次失败证据与通过记录保存在同目录。首次补登记曾引用不存在的独立扩展反向链接路径，失败产生的两个新侧表移至 `failed_registration_1/` 保留；未更动任何原载荷，修正为真实内嵌字段后重新运行。

原模型与原始向量缓存只读，本次没有读取 K/R 逐题结果或调用 API。源材料覆盖仍是知识组织范围，不是全库 9639 文书审核，也不是所有标签的完整法律确认。L007 现行状态待核、L011/L012 隔离、原件数量 0、历史适用与当前业务事实未自动确认等边界不因登记扩展而改变。回滚必须同时匹配法规/覆盖层、卡片、导航、检索表示、矩阵及绑定版本，不能只切换某一文件。
