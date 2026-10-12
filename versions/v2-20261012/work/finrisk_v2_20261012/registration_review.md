# V2 补登记脚本独立审查

日期：2026-10-12。审查 `register_v2.py`、`test_register_v2.py` 及其实际调用的冻结 runtime、compatibility validator、Workflow API。未执行 `--execute`，未修改真实 SQLite、配置、旧候选或审核历史。

## 规格结论：PASS

当前版本未发现阻断登记的实际安全缺口。

- 启动明确调用一次 `runtime.verify_package_bindings(None)`，实现会核对整个冻结包文件集合与各文件 SHA、冻结代码/config SHA、schedule/selected 顺序成员、每个 task 与原 raw/text SHA。它不是仅核对一个 batch 的快捷入口。
- 每个目标均先要求基线机械检查成功且 draft SHA 与候选一致，再读取原候选文件，核对原始字节 SHA 和 strict_json 后的内容 SHA。`original_candidate_path` 的原始导出格式为相对仓库根路径；在本任务指定的仓库根 cwd 下，resolve 与实际 authored 路径一致，且限制在 `runtime.RUN/authored` 内。
- overlay 通过现有 `apply_overlays` 绑定原 draft/text SHA，要求同 file_id、candidate/pending；新 target 单独冻结，旧 authored 文件仅被读取。原任务来自已验证的 frozen selected/schedule；每个变化目标在生成预检计划之前必须通过兼容 guard，正式 ingest 时再次使用该 guard。
- 兼容 guard 核对 task/document 与原文 SHA，冻结结构 guard 重新读取/解码 raw 并核对全文与 source SHA；引用、标签、coverage、币种、姓名例外、金额及完整日期等检查由已验证兼容基线提供。仅已知姓名/人民币格式断言使用限定兼容替换，没有跳过其余结构校验。
- execute 分支先用 SQLite `backup()` 为全部现存 batch 数据库生成一致备份及 SHA，再构造 Workflow、plan、ingest。备份文件已存在会拒绝继续，不覆盖旧备份。
- 写入只经现有 Workflow API。实读 `bulk_flow.py` 确认修订必须为旧版本 +1 且在 0..2；新 proposal 会清空当前 review_path/review_sha256、model_second_review_completed=0，历史 proposals/reviews 保留。脚本不调用 ingest_review，也不伪造 approved；写前核对预检记录的旧 revision/SHA，防止漂移覆盖。
- `_make_workflow` 使用旧冻结 config 创建工作流，Workflow 校验已保存 config/metadata 一致，不重置旧 config 或 formal history。当前 registration_plan 每行、summary 和 ingest receipt 均明确记录 `active_validator_version=finrisk-compat-v1` 与活动 guard SHA；不会将兼容校验器假称为旧 config 中的原 guard。

审查时初版 preflight 计划缺少活动 guard 版本/SHA 字段；实现方已补齐 plan 与 summary，复读最新代码确认该问题解决。

## 代码质量结论：PASS

在规格通过之后，独立核查原候选读取、target 字节固定、预检到写入的旧 SHA/revision 检查、SQLite 备份顺序、Workflow 的 config 与历史保护，以及 ingest 失败处理。未发现本次授权登记范围内需要阻断执行的实际安全或完整性问题，没有提出风格重构。

正式 ingest 使用预检保留的相同 proposal/raw，既有 `_serialized` 检查序列化字节与对象一致；调用同一兼容 validator 重新校验。真实 Workflow 以事务维护修订与 proposal/history，禁止跳号、同版本改字节及超过 r2。变化目标成功后当前审核失效，旧审核文件与数据库历史仍保留；不变目标不调用 ingest，既有当前审核不被改写。流程在所有现存数据库备份完成前不调用 Workflow 构造、plan 或 ingest。与旧 config 冲突会被既有不可覆盖文件发布和 metadata SHA 校验拒绝。

## 验证与范围

指定 Python `-B -m unittest discover -s work/finrisk_v2_20261012 -p test_register_v2.py -v`：最新版本 2/2 通过，覆盖新登记 r0、同 SHA 跳过、r0→r1、r1→r2 以及 r2 再变更拒绝。审核另外直接核对了真实 Workflow.plan/ingest_proposal/get_job 的参数、序列化字节接口、当前审核失效和 config 保护实现。

另独立运行既有 `test_bulk_flow.WorkflowTests` 中以下三项临时 fixture 测试，全部通过：`test_source_or_config_drift_is_refused`、`test_review_revisions_keep_old_files_and_stale_review_cannot_release`、`test_only_two_revision_rounds_are_allowed`。测试仅写自动清理的临时目录，未触及真实 ledger。

实际只读对账已完成（session14313，exit_code=0）：8509 个原 candidate 的 authored 路径限制、原始字节 SHA 及 strict_json 内容 SHA 全部通过；47 个现存 SQLite 均以 mode=ro 读取。原稿对应登记状态为未登记 3809、已有 SHA 不同 33、已有 SHA 相同 4667；33 个 SHA 不同目标的旧 revision 全部为 0。该对账仅比较原稿，五个 overlay 的最终目标数量和兼容预检结果应以本次完整 dry-run 计划为准，没有将原稿计数冒充 overlay 后计数。

本结论是登记工具代码与接口审查，不是已执行登记或登记后状态验收；没有声称 3809+33+5 已写入正式 ledger。

## 首次执行配置阻断后的独立复审（2026-10-12）

规格复审：PASS；随后代码质量复审：PASS。未发现当前修正需要阻断下一次登记的实际问题。本次仅审源、读取配置/SQLite metadata 和运行临时 fixture，未执行真实登记。

首次实际尝试的保存摘要仍为 `preflight_complete`、`executed=false`：8509 项预检通过，3809 new、35 update、4665 already_current；其 `before_sqlite/backups.json` 保留 47 项备份。这是修正前的执行证据，不是修正后已登记成功的证明，也不能覆盖为成功摘要。

修正仅将入口改为 `import fast_runtime as startup_runtime; runtime=startup_runtime.base`。冻结 fast_runtime 会在 base 上替换 `verify_package_bindings` 与 `_make_workflow`：前者先核验启动 overlay 文件集合、manifest/代码 SHA 及原冻结包 manifest 绑定，再调用原完整包校验；后者再次核验 overlay 与启动返回绑定，并向原冻结 config 加入原有的三项启动 SHA。原 8509-source 全包核验、逐 task/raw/text 检查和原 Workflow 配置不可覆盖/metadata SHA 校验均未删除。冻结 source/runtime/engine config 没有为兼容登记而改写。

独立读取现存 47 个 batch config：其完整配置除 batch_id 外均与 b001 相同，三项启动 overlay SHA 全部一致；各 SQLite 仅以 `mode=ro` 核对 metadata 中 config SHA 与现存配置原始字节 SHA，47/47 通过。独立运行最新 `test_register_v2.py`：3/3 通过（14.735 秒）。新增测试将真实 b001 config 原始字节复制到临时目录后调用实际 `_make_workflow`，确认构造成功且 config 字节不变；其余测试确认 r0→r1→r2 连续、同 SHA 跳过、r2 后变更拒绝。首次测试因系统 sandbox Temp 的 fixture 写权限失败；将临时目录指定在工作区后通过，未扩大真实 ledger 写权限。

代码质量复读确认：备份完成后才构造/plan/ingest；已有备份拒绝覆盖；原候选只读，目标另存；写前重新检查旧 revision/SHA，Workflow 内部继续禁止跳号、超过 r2 与同修订不同字节。新 proposal 清除当前审核绑定而保留旧 proposal/review 历史；没有 ingest_review 或真人批准路径。plan/summary/receipt 显式记录 `finrisk-compat-v1` 及实际兼容 validator SHA，不假称旧 config 中原 guard。candidate/pending 和 human_approved=0 的约束仍在。

下一次实际尝试应使用独立 `registration_final` 输出目录，保留原 `registration` 下的首次预检、47 个备份和失败边界。此复审解除的是启动配置兼容性阻断；最终登记完成、8509 项逐项对账和登记后历史保护仍须由下一次实际执行证据验收。
