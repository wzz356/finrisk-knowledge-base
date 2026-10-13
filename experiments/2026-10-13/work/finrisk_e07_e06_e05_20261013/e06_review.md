# E06只读独立复核

最终结论：**PASS**。本轮实际16个旧1:1 Top20控制、角色/源边与D011范围说明均通过；审查发现的未知事件回退契约问题已修复并独立复验，无未解决实质问题。

审查范围：只读e06.py、test_e06.py、finalize_e06.py、局部图、E06保存结果/指标/判断、旧V3实际显示结果、获胜原unit及相关V2源绑定。只新增本文件，未改图、评分或结果，未执行main、模型API或GPU。验证执行仅为读取与三个纯函数的独立重放，禁用Python字节码缓存写入。

## 1. 本轮实际分组与标注：PASS

- 独立读取278个获胜原unit，核对全部320个命中的local_event_id、local_actor_role、local_actor_name；与严格按原source_spans全包含得到的结果一致。
- event_for_unit只处理source_supported，核对完整来源SHA，每个原source_span须完整落入一个已核event_spans；多事件匹配报错，无强制合并。uncertain组不参与。
- 16个实际Top20均同一file_id只出现一次。按三个纯函数从旧V3实际Top20逐行重放，16/16输出与e06_results完全一致；80个原Top5的文件、unit、rank、score、实际显示正文与基线一致。
- 原rank和score均保留，新增display_rank表达后置顺序。仅D014/D016的Top5发生变化；重复占位3→0可复现。
- 17个成员角色引文及全文SHA、3条源边均重新逐字核验通过。王斌直接组织设计制作、叶德模亲自使用电脑模板打印均有源动作；其他明确管理人员没有被标为亲自销售/发布。闻怀强与孙健仅保留explicit_direct_responsibility且role=unknown，未细化成本人操作。
- 图字节SHA与e06_metrics绑定一致。80个保存判断汇总为51个有用位置、14个覆盖输入，逐输入计数与metrics一致；本审查未重新裁定有用性。

## 2. D011不去重的具体解释：PASS，但需准确表述

F000929获胜原unit是[401,595)，完整包含于图中宝应事件范围[401,596)，因此可以标注本局部事件。

F000922获胜**原unit**是[329,555)，图中已核同事件范围是[340,556)。它超出的具体部分仅为前置11字符[329,340)“一、编制虚假资料行为\n”。虽然正文事实与宝应事件相符，严格全包含判断仍失败，所以local_event_id=null、不后置去重是准确的。不能为改变占位指标事后扩大图。

F000922的**显示source_spans**是[329,726)，显示返回进一步包含二号育肥猪条款费率问题。要区分显示区间与获胜原unit：如果说明写成“获胜原unit包含第二项育肥猪行为，所以不能去重”，则不准确；实际原unit没有该第二项。准确说法是“获胜原unit带有未纳入本次批准范围的前置标题，严格区间全包含未通过；扩展显示还包含另一行为”。

同样，D016两份璧山显示从文首开始，不能误用显示source_spans判断：F001319原unit[464,608)，F001320原unit[487,631)，二者均完整位于已核事件范围，按原unit分组符合批准契约。文书头部只作显示上下文，不自动获事件分组批准。

## 3. 历史[P2]问题：未知事件回退键使用file_id（已解决）

位置：e06.py第29行与第42行。

历史实现的`diversify`在没有已核事件时使用`"unlinked_file:" + hit["file_id"]`，`duplicates`使用相同键。不同未知unit若来自同一文件，会被当作一组并后置/计入重复，即使没有任何source_supported事件；这与局部图的file_id_only_grouping_allowed=false及未知事件保持独立不一致。

实际纯函数探针：无任何event，u1/u2属于UNKNOWN文件但原文区间分别[0,1)/[2,3)，u3来自OTHER文件。输入u1,u2,u3得到u1,u3,u2，且全部local_event_id=null；duplicates返回1。说明该路径确实以file_id合并未知命中。

当前16个Top20每文件仅一命中，所以历史问题没有改变本轮排序、重复指标或判断结果。root已将两处回退键改为`unlinked_position:unit_id:rank`，保持不同未知位置独立，新增test_unknown_units_same_file_remain_independent。审查者只读复验现有5个必要测试，5/5通过、0失败；同一历史探针现在得到u1,u2,u3、duplicates=0。另按修复后的纯函数从旧实际Top20独立重放，16/16结果与保存e06_results逐行完全一致。局部图、结果、指标及finalize脚本SHA未变。本任务仅更新本审查记录，没有实施代码或结果修改。

E06实验报告第34行已准确写明D011原unit前置11字符标题超已核范围、原unit未含育肥猪事实，且没有拓宽图。最终审查PASS。

## 最终绑定文件SHA256

- `work\finrisk_e07_e06_e05_20261013\e06.py`: `cf6734f50506048e4811cc23dce8d2ed52d8575a8bf7c04ededfd3b587de8c29`
- `work\finrisk_e07_e06_e05_20261013\test_e06.py`: `17fe688bf00566ff44cc1153a70f98b72821863a92200f2ea3e85c954da7952e`
- `work\finrisk_e07_e06_e05_20261013\finalize_e06.py`: `6021b7e90efa6e6548ab5eb57db8eb60d9001d5854b88c4daa7c49f4e8ec75e5`
- `outputs\FinRisk_E07_E06_E05探索_20261013\local_graph.json`: `ee0e6743f6195367cb2a37b7083e41820b73b61e8b5fe0571a1c1168aa9857c6`
- `outputs\FinRisk_E07_E06_E05探索_20261013\e06_results.jsonl`: `e128411c683df29f7dae12987ec0f3bd710aa5c6829b8df2020007d35e84850e`
- `outputs\FinRisk_E07_E06_E05探索_20261013\e06_metrics.json`: `045010fca9bff863509b7c71794dfd8eac6af94f2799736611556448d8c3359c`
- `outputs\FinRisk_E07_E06_E05探索_20261013\E06实验报告.md`: `8326a6ec7b805c15c51db14369d52c9e3d11c6e9c4fd12966c646594e6070587`
