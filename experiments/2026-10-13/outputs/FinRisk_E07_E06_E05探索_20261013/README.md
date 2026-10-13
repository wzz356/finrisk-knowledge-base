# FinRisk E07、局部E06、小样本E05探索

先看[实验总报告](实验总报告.md)和[当前完整方案](完整方案.md)。当前1:1主流程保留，E08暂缓；本轮所有语义判断/来源审核为模型意见，human_approved=false。

最终E07在e07_final；根同名文件为首稿。E06 metrics/all_judgments为完成结果，pending_judgments是补判前历史队列，已经全部补完。E05 metrics/all_judgments为83上下文统一新评分；sensitivity单独记录80历史绑定+3新宽口径意见，不能混作新主分。

clusters_level1/2/3为三次真实聚类，summaries_level1/2/3和tree_nodes为模型逐断言写的7源绑定摘要，directory_nodes为6人工机制目录。e05_results及run/score_pool/token_audit保存真实全库阶段；service_gap_diagnostic是事后只读定位。freeze_cluster1/2/3及freeze_retrieve记录实际输入依赖。

verification_final、e05_verification、delivery_manifest分别给结构/源/旧封包核验和最终字节清单。源码/测试/红绿日志/审查在work/finrisk_e07_e06_e05_20261013；旧代码、初稿和失败测试保留为历史，不是当前待办。详见[复跑说明](复跑说明.md)。
