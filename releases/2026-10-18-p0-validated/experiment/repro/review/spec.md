# 第一阶段：规格审核

结论：本次范围内通过。2026-10-18；先完成规格复核，再进行第二阶段质量审核。

只读范围：effect_common.py、retrieve_new36.py、cache_case_reads.py、protocol.py、prepare_initial.py、api_runner.py、tests；后经父层明确扩展，加入prepare_judgments.py。同时读取冻结36题协议、api_request_plan.json、experiment_config.json。未读取真实参考答案、实际模型结果或密钥，未联网、调用API、启动全库读取器或修改实现。

## 规格核对

- input_queries强制36条、仅opaque_id/text字段、输入与ID唯一。初始请求仅含当前题完整text及公开候选材料；原ID、分区、组别、参考字段不进入请求。
- 协议预注册24主分析/12边界挑战及开发18/留出18；prepare保持已冻结输入顺序，以私有mapping仅筛分区。未读取mapping/参考逐题复核。
- 全库检索入口强制9639文档/65475单元；BM25与BGE各100候选，1:1 RRF、c=60、100候选。初始任务共36 scope及3600共享rerank；judgment每分区18题×2臂，最多72个。
- prepare_judgments只从完整且SHA绑定的initial结果取100评分；按分数及稳定unit_id排序、文档去重取20个候选，统一装配4000字以内整块案例，两个arm引用同一实际case_text和显示案例ID。
- 同一输入仅计算一次候选机制、条件定义和scope_facts。两臂共用这些内容和输出协议，只改变法规/指南及其法律覆盖ID；未看到参考答案进入模型payload的路径。
- scope来自当前题的独立scope请求；字面引文校验和current_business_facts_verified=false均明确不证明真实业务事实。
- max_tokens按scope/rerank/judgment锁定512/384/2048，model、system、JSON格式与请求body键集受验证；每题新独立上下文，重试只补结构错误说明。
- 读取密钥前校验新scope授权、精确request-plan SHA、pre-inference冻结、job冻结、结构及恢复绑定、唯一任务上限。
- 全相位共用一个持久账本；每次发送前落盘预留；未知用量完整计费；重启把未结算预留按未知处理；尝试次数跨重启累计，每job最多3次、最多12并发。
- phase checkpoint与终态分开；judgment耗尽仍保留missing/invalid并可进留出；initial不完整不能生成最终排名。

## 已发现并修复

S01（原P2）：HTTP200顶层数组和可选usage details=null触发未捕获AttributeError，绕过逐次记录。现增加顶层dict验证、nullable details处理；外层响应和模型JSON内容均用strict_json拒绝NaN/Infinity等非标准常量。合成反例和轻测已通过。

S02（原P2）：无效rerank引文按规格保留评分，却把source_quote改成None，导致同一initial phase恢复再验证失败。现保留原字符串，另记validated_source_quote=None；已补规范化幂等回放测试并通过。

父层原已知phase不完整快照无法恢复的问题也已修复，相关测试通过。无剩余阻断项。

## 验证与范围

37个轻量测试通过：protocol 6、api_runner 7、纯手写合成评分夹具24；总运行0.298秒。另用纯合成卡片验证paired_payloads共用控制字段，以及pack_cases整块预算，均通过。未作评分实现源码审核，未读取实际评分参考或结果。

pre_inference_freeze尚在父层最终装订阶段，本审核确认执行入口在读key前验证冻结，但未读取/签认最终冻结清单内容。父层已报告用户明确授权共2美元；本审核未读授权凭证，runner仍要求精确plan SHA授权。

非阻断记录：已运行BGE同分按固定语料位置，RRF/rerank按稳定unit_id。父层已接受在首次推理冻结前把config的笼统rank_tie说明改准确，无需重新检索。

此结论是实现与协议符合性复核，不是模型效果验证结果。对应源码SHA-256见spec.json。
