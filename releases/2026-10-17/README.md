# FinRisk 最小交付与答辩实验材料

发布日：2026-10-17。先阅读[答辩索引](答辩索引.md)。本目录集中保存当前有效案例库、法规库、正式测试集和关键实测结果；原仓库历史材料保留。

## 最小知识库

- [案例库版本入口](outputs/FinRisk_知识库V2.1轻量收尾_20261015/version.json)：9639份有效候选、15620个受罚主体案件、25186条行为／责任候选，沿用官方27标签。
- [当前有效候选](outputs/FinRisk_知识库V2.1轻量收尾_20261015/effective_candidates.jsonl.gz)：已合并5份既有修正，直接读取每行的`draft`，无需自行叠加旧稿。配套[file_index](outputs/FinRisk_知识库V2.1轻量收尾_20261015/file_index.jsonl)、修正记录和验证工具均保留。
- 原文复用仓库的[data/sources](../../data/sources)与[定位索引](../../data/file_index.jsonl)，全量规范表及检索投影复用[V2基线](../../versions/v2-20261012)。使用全量规范表时按F编号替换本包`patch_normalized`中5份文书的范围。
- [法规原文](outputs/FinRisk_法规库V1_20261017/articles.jsonl)、[来源及版本](outputs/FinRisk_法规库V1_20261017/catalog.jsonl)、[条件规则卡](outputs/FinRisk_法规库V1_20261017/rules.jsonl)：10份官方来源阅读快照、64条入选条文、24张解释卡，覆盖12机制。
- [快速修复操作条件](outputs/FinRisk_法规库快速修复回归_20261017/operational_rules.json)：补齐必要依据，区分事实不成立与材料未知；原始法规与模型解释分别保存。

本目录不是已上线的Agent应用。法规检索代码、段落索引及只读契约保留；重新运行BGE检索仍需配置模型、分词与路径。无需模型即可读取全部候选、条文和保存的输出，并复算指标。

## 测试集与实验

|材料|入口|范围|
|---|---|---|
|正式测试集V2|[题目](outputs/FinRisk_正式测试集V2_20261017/queries.jsonl)、[数据卡](outputs/FinRisk_正式测试集V2_20261017/dataset_card.json)、[协议](outputs/FinRisk_正式测试集V2_20261017/完整评价协议.md)|90道合成业务输入、12机制；必要参考标签覆盖官方27类中的10类|
|闭集完整相关性|[100篇真实文书](outputs/FinRisk_正式测试集V2_20261017/corpus.jsonl)、[24题](outputs/FinRisk_正式测试集V2_20261017/closed_queries.jsonl)、[2400对标注](outputs/FinRisk_正式测试集V2_20261017/qrels_closed.jsonl)|相关性分母完整，只把3分直接支撑计为主相关|
|闭集检索结果|[实测报告](outputs/FinRisk_正式测试集V2_闭集实测_20261017/实测报告.md)、[指标与逐题数据](outputs/FinRisk_正式测试集V2_闭集实测_20261017/metrics_final.json)|BM25、BGE、1:1 RRF、DeepSeek真实排名，K=1/5/10/20|
|全库与最终判断|[两层验证报告](outputs/FinRisk_两层验证_20261017/两层验证报告.md)、[检索指标](outputs/FinRisk_两层验证_20261017/full_pool_metrics.json)、[风险对照](outputs/FinRisk_两层验证_20261017/risk_comparison.json)|9639篇全库检索的24题对照；90题×两臂实际判断|
|法规引入与修复|[首版结果](outputs/FinRisk_法规库V1_20261017/实验报告.md)、[快速修复结果](outputs/FinRisk_法规库快速修复回归_20261017/修复实测报告.md)|36题故障回归29→34正确，保留错误和修复前后输出|

所有参考仍是模型银标，人工批准数为0。用户允许跳过人工核定，不等于把参考升级为专家金标。带答案的`master.jsonl`、`qrels*`及法规确认参考仅供离线评分，不能提供给待测系统或写入检索知识库。

## 离线核验与复算

下载整个仓库、保留目录层级，在仓库根目录执行：

```powershell
python -S -X utf8 -B 'releases/2026-10-17/reproduce.py'
```

只需Python标准库，不联网、不读取密钥、不调用模型、不改写结果。核对194份来源载荷、9639候选及共享原文指纹，复算4路线闭集指标、4路线全库参考池指标、180份最终判断与6组法规回归指标。发布文件完整SHA见[manifest.json](manifest.json)，筛选来源及两份模型输出摘录方式见[selection_provenance.json](selection_provenance.json)。原始解析JSON逐项保留；省去重复HTTP响应、完整尝试日志和费用账本，费用仅保留汇总。

生成时点的数据卡、冻结记录和原报告未改写，里面“尚未运行／未上传”是历史状态。当前完成情况以本说明、结果文件和本次Git提交为准；部分原报告列出了完整本地审计包的文件名，精简版实际载荷以本目录manifest为准。

## 明确保留的限制

闭集Recall只针对100篇；全库的已知参考覆盖率、池内NDCG不是真实全库Recall。90题参考与输入存在合成偏差，不能宣称生产准确率；36题修复回归已被开发者见过，不能充当独立新题成绩。法规保存的是官方阅读快照，部分效力待核；当前库仍是候选版，现有应用默认未切换。

本次未新增上传教材、凭据、完整API日志、大型token审计文件、模型权重、临时恢复目录或重复ZIP；9639篇源文书及全量检索投影通过仓库已有文件复用。本轮发布没有新增模型调用。
