# FinRisk V2 规范化代码质量独立审查

日期：2026-10-12。最终结论：**quality PASS，唯一 P2 完整性阻断已修复并独立复验关闭**。本轮未发现新增重要未决问题。

最新合法旧结构小范围追加审查结论：**spec PASS → quality PASS**，实际 SHA256 `650f294176b879011018d8dffb25374c951caa20985cbe886e9053a11b1113c7`。本项无新增重要未决问题，验证见文末。

复审固定实现 SHA256 已实际核对：`b0e53cbaf1efec93f66e5ca7d909d0dc6de9746d3770ea79cec733b1810ab6e9`。下文保留首轮证据；最终修复复验见“修后独立复审”。

审查范围仅 production `normalize_v2.py` 的代码质量。先读取最新 `normalize_spec_review.md` 的独立 spec PASS，再进行质量审查；本报告不替代或重写规格结论。审查版本 SHA256：`5fb5797df65f0c89300be0d81e5ace298f33bc6f4d67685eb88dffbf01a59331`。

只写本报告；未修改实现、测试或真实数据；未加载／扫描全9639；未读凭据、盲验或未经授权的原文件；未调用模型或网络服务。临时反例与重建目录使用已有测试 fixture，在 `normalize_fixtures` 内由 TemporaryDirectory 清理。

## 重要发现

**P2（已关闭）：清单漏掉阅读类别可静默关闭该类全部完整性检查。**

位置：`normalize_v2.py:809`，`for name, count in manifest['reading_counts'].items()`。代码先构造固定三类 expected_readings，却按待校验清单自身的键决定实际检查类别，没有核对 `reading_counts` 必须完整包含 `document_index`、`case_reading`、`behavior_reading`。

最小反例只改临时产物：生成合法 fixture 后，把行为阅读的 `human_review_status` 改为 `approved`、`negations` 改为空；更新该文件实际 SHA／字节数，并从 manifest.reading_counts 删除 `behavior_reading` 键。实际 `verify(out)` 返回 **passed=true、errors=[]**。核心表／snapshot 仍保留 pending 和原否定信息，说明漏检并非来源许可。

影响：清单缺键会使该类阅读事实／状态、对象集合覆盖和导航指针全部跳过；既可能接受失真的审批状态，也无法可靠确认阅读导航完整重建。应在读取和遍历前封闭核对必需的三类阅读键集合，并检查 manifest 必需 core／extension／reading 产物的完整清单；不能让产物自己的 metadata 决定哪些强制验证可以不执行。新增删除各必需阅读键的负例，确保全部 passed=false，再独立复验。该项关闭前不能以规范化 quality PASS 执行全量发布。

## 可执行最小反例

在仓库根目录使用指定标准 Python 运行；仅创建和自动清理临时 fixture，不读取全库：

```python
import sys, tempfile, json
from pathlib import Path
sys.path.insert(0, 'work/finrisk_v2_20261012')
import normalize_v2 as n
from test_normalize_v2 import fixture

w, s = fixture()
root = Path('work/finrisk_v2_20261012/normalize_fixtures').resolve()
with tempfile.TemporaryDirectory(dir=root) as tmp:
    out = Path(tmp) / 'result'
    n.normalize_records({'F000001': w}, {'F000001': s}, out)
    path = out / 'reading/behavior_reading.jsonl'
    rows = n.read_jsonl(path)
    rows[0]['human_review_status'] = 'approved'
    rows[0]['negations'] = []
    n.write_jsonl(path, rows)
    mp = out / 'manifest.json'
    m = json.loads(mp.read_text(encoding='utf-8'))
    del m['reading_counts']['behavior_reading']
    m['files']['reading/behavior_reading.jsonl'] = {
        'bytes': path.stat().st_size, 'sha256': n.file_sha(path)}
    n.write_json(mp, m)
    print(n.verify(out))
```

该代码已实际执行：`passed: True`、`errors: []`，退出码 0。

## 已实际通过的验证

- 使用指定 Python 独立重跑 `-m unittest discover -s work/finrisk_v2_20261012 -p test_normalize_v2.py -v`：**23 tests，30.792 秒，OK，退出码 0**。
- 独立完整重建两个小 fixture：第二份正文增加 emoji；两次输入 map 顺序相反，全部 **20 个文件逐字节相同**，两套 `verify` 均通过，原候选及来源对象深比较不变。这验证固定输入排序、Unicode 码点坐标、ID 与导航的正常重建路径稳定。
- 阅读生产状态继承、双稿 SHA、source/text 版本绑定、ID 描述、证据位置、引用逆向关系、审批空值、三类阅读行重建及重复／孤立校验路径。当前已有 source/text/state 的规格修复未发现新的独立重要质量问题；主要问题为上述强制类别清单未封闭。

## 边界

生成与复验采用聚合内存结构；本轮没有加载整库或预测全量峰值，也没有提出无关重构。未来材料显式 local_key 冲突／重复 factor_id 已由规格报告作为当前输入前提记录，本轮不据未发生形状新增阻断。上游 overlay 授权及原候选字节 SHA 仍按现有调用边界负责；本模块不代填真人批准或声称 PDF／法律语义核验完成。

## 修后独立复审

- 已阅读实际修复：`READING_TYPES` 固定三类；先核 `reading_counts` 类型与精确键集合；必需产物集合包含八核心表、六扩展表、三阅读表、契约与 INDEX，共19个文件；缺任何必需文件哈希均返回错误。实际阅读循环按固定三类执行，不再由输入清单键决定检查范围。
- 指定标准 Python 实际重跑 **25 tests，42.651 秒，OK，退出码 0**。新增测试覆盖三类阅读缺键及全部19个必需文件哈希漏项。
- 独立重新执行上方原始 P2 最小反例，仅将预期改为拒绝：实际 `passed=false`，错误包含 `manifest_reading_categories_incomplete_or_unknown`、`reading_count:behavior_reading`、`reading_original_record_drift:behavior_reading:…`。不仅缺键本身被拒绝，该类被篡改行也继续实际检查。
- 源码变更限于必需清单封闭与固定阅读循环，原状态继承／源版本／ID／引用／导航构造逻辑保持本轮质量审查通过边界。未全量生成或加载9639，不以 quality PASS 声称全量运行或语义审批完成。

## 合法旧结构兼容追加独立质量审查

先独立完成31tests、合成必要反例和F005066／F005270真实生成复验，并向root明示本项spec PASS后，再检查该小改质量。具体规格结果与边界见最新 `normalize_spec_review.md`；本轮 **31 tests，57.181 秒，OK**。

生产质量核对：

- `legal_ref_record`、`uncertainty_fields`、`case_compat_fields` 将兼容表示集中为明确的纯字段投影，原值通过深拷贝保存；没有文本解析、法条／名单推断或额外文件读取。typed空值／空数组均伴随原始值与unknown说明，避免把契约占位混同已记录的不存在。
- verify从已绑定snapshot原记录重建旧法条整项、case兼容字段和行为未知字段，并核对字段是否存在及其值；reading沿现有完整字典比较路径显示且约束全部兼容元数据。独立补造“真实原文中存在的法条quote”也被拒绝；不是只凭片段存在就认可结构事实。
- 双稿SHA与snapshot完整保留，原源文本／位置生成路径、状态继承、ID描述／算法、必需19文件清单／三阅读类别、引用及导航守卫未被替换。当前输入的原有效字段保持原表示；增加的旧值／unknown说明不授予审批或改变主体关系。
- 实际小fixture和两份真实定向生成后原输入深比较不变，阅读与核心原值一致、机械verify通过。没有新增全库加载、外部访问或源文件写路径；不提出无关内存优化。

只更新两份规范化审查报告，未改实现、测试、数据或全量运行进程。质量通过不代表正在运行的 `normalized_final` 已完成；root仍须等待完整输出并实际verify及来源绑定检查后报告全量完成。
