# E07 / 局部E06 / E05节点作者实现后独立代码核查

最终结论：**PASS（本轮发现的防漂移P2已由root修复并独立复验）**。未发现剩余P0/P1或需要改变本轮已有来源、摘要、分组和判断结果的实质问题。

审查对象为root新增的 `e07.py`、`e06.py`、`finalize_e06.py`、`author_nodes.py`、`author_upper.py`，对应最终E07记录、局部图/E06控制产物、21叶/6目录/7摘要与三次真实聚类的依赖、向量和token侧车。没有把本人此前实现的 `e05_runner.py` 作为独立代码审查对象。未读取正在执行的E05检索结果/成绩；未调用GPU、模型API、网络或运行正式聚类。审查期间只新增本记录，未改既有代码/数据，Python禁用字节码缓存写入。

## E07：PASS

- 实际使用 `e07_final` 最终记录；报告明确根目录同名文件是修订前首稿。首稿30未知与最终33未知并非当前结果冲突，不能混用。
- 16条最终记录的query_id/text均对应既有16输入；64条件重新汇总为present19、absent12、unknown33，与最终execution一致。field IDs完整唯一，所有非空输入quote均是输入逐字子串。
- 逐条重放validate_input_record/followup_fields：31个待补问题与记录一致；D004没有额外利益时只抑制关联/兑现两个问题，两个状态仍为unknown。未把未知自动转否。
- D006授权/实际回流、D011实际查勘核实均保留未知；D009计划开展销售不会升级为已实施。present状态说明只代表输入记载，不声称外部核实。
- 7份机制源support的全文SHA、连续quote和全部span重新核对通过。来源限历史案例和核查方向，source_support_role明确不是该输入实际召回证据，未引入新监管通则或官方27类之外的标签。
- 8个补信息分支明确constructed/not_real_customer_material/new_retrieval_performed=false、human_approved=false。作者与判断者为同会话模型，报告没有将4风险/4边界分支当独立正确预测、准确率提升或真实客户答复。

## 局部E06：PASS，历史P2已修复

- 图中8候选组、17成员含7个source_supported和1个uncertain；分组只用每个获胜原unit的全部source_spans完全落入同一已核event_spans，且唯一匹配。不同文件名、主体同名或角色相似不授权合并，context_supports不授权扩范围。
- 独立校验成员完整源SHA及95个anchor/context/role源引文位置；已核动作与管理责任分离。西安P0600*候选不分组，F004155/F004090表行负例不移植主语、行为或责任。
- 当前unknown回退键是unit_id+原rank，未知位置保持独立；不是file_id分组。原rank/score保留，display_rank单独表示后置顺序。
- 独立读取278个获胜原unit，重放16个旧V3实际Top20：16/16逐行与保存e06_results一致，80个原Top5 unit/rank/score/显示text保持一致；未重新裁定旧/新增位置的有用性。
- finalize_e06限定3个实际待阅读位置和80唯一位置，正向判断必须有逐字实际显示/来源quote；结果是模型探索判断，未伪称真人金标或全库事件Recall。e06_execution的pending为历史控制阶段，e06_metrics才是后续完成态。

### 本轮发现的[P2]：语义判断复用缺少查询/packet/source防漂移守卫（已解决）

历史e06.py按query_id选择旧packet/judgment，再仅按file_id/unit_id/display text找assessment；没有在复用前比较parent.text、packet.input_text/input SHA、judgment input/packet SHA，也没有将packet与当前原Top5/当前source重建绑定。只读内存探针拦截write_new、不写文件：同query ID但输入从old query改成different query，保留相同命中，仍复用了旧assessment。该探针是合成守卫测试，不是实验成绩。

root新增validate_parent_binding并在每query复用前执行：核query ID/text/SHA、judgment.packet SHA，使用demo.make_packet按实际原Top5和当前源重建整个packet并比较，核assessment file/unit/rank及human_approved=false。原代码留档为e06_initial_binding.py。

独立复验修复后的6项E06测试，6/6通过、0失败；root红/绿日志记录缺少守卫时失败和补齐后通过。真实16查询的新守卫全部通过；另为每条输入在内存中变更query text，16/16均拒绝。按修复后纯函数重放16 Top20仍与保存结果完全一致，e06_results SHA仍为 `e128411c683df29f7dae12987ec0f3bd710aa5c6829b8df2020007d35e84850e`，没有改变本轮结果。原真实80个packet source SHA也与当前源一致。

## E05节点作者与三次真实聚类：PASS

- 真实簇输出明确来自本地BGE/cuda/float16、batch16/max512，三次cache_events都hit=false；同一旧backend/adapter/model/runtime绑定。没有重放模拟向量来冒充实际BGE编码。
- 21叶→4簇实际成员数为8/8/4/1；4摘要→2簇为1/3；2父摘要→1根簇为2。三次seed17、2轮收敛、空簇修复0；方法注明numpy硬球面KMeans、不是UMAP/GMM软聚类。
- 三个freeze的所有条目、每次cluster.inputs、输出与run SHA、NPY SHA、token侧车SHA均重新核对通过。L2执行freeze纳入author_nodes/L1摘要/目录/前次聚类；L3纳入author_upper/L2摘要/前两次聚类链。
- 规范化向量形状实际为21×512、4×512、2×512，与各自元数据和输入数相等；全部有限，L2 norm最大误差分别1.19e-7、5.96e-8、5.96e-8。没有假定未经读取的模型维度。
- 实际最大输入token分别501、197、138，均≤512、truncated_inputs=0；每次preflight/audit无拒绝或截断。根摘要尚未在这三次cluster中编码，本审查不推断其正式检索token或得分。
- author_nodes/author_upper仅序列化会话明确写出的文本与claim。L1 claims来源集合等于实际簇叶集合，upper claims来源集合等于实际cluster descendants；child_node_ids与真实member_node_ids一致，cluster_input_sha256指向实际簇输出。7节点tree恰等于4+2+1三层保存节点。
- 13个节点（7摘要/6目录）的全部实际text与27条claims已阅读；21叶的32段完整source segments共3833字符已阅读并逐字、源SHA核对。84个claim supports的file/node/unit/sourceSHA/segments与对应叶一致，均在声明后代内；每层保留全部21叶，无丢失或跨簇重分配。
- 两个大混合簇明确为混合机制。上层只抽象列举历史事实，不增加相同主体/事件、条件满足、一般违法或当前规范结论。F004155两表行保持独立；F008940/F008944不因遮蔽保单号认定同次销售；F003638保留“本机构”原归属未知；F002890不把全部4020万元改称截留；管理责任不升级为亲自行为。
- F008852仅案由叶在每层仍声明原因、流程、主体未知，不能用其他赔付案例为它补条件。目录由源机制组织，author明确非聚类目录，human_approved=false；摘要和目录只提供导航，不能替代最终原文证据。

## 证据与当前限制

已读tests_root_green.log的24项绿灯、修复新增e06_binding_red/green日志，并独立运行当前E06 6项测试。来源/绑定、数组和纯函数重放为本次只读CPU验证，没有新模型分数。本人未读取E05 B0/DIR/TREE正式成绩，因此本PASS不评价检索收益、聚类纯度、统一Top5判断或最终采用结论。

当前审查绑定SHA256：

- e07.py：`34026cc455961b2e40f4c8548553ba173c91e564340211ac03df32b95f4e5fd7`
- e06.py（防漂移修复后）：`44f2a7748662c521347f3c9a221e55aed6646a82fcd1ad1aa0d344be84b86f3c`
- test_e06.py：`ac6ac1fcbf8a744c97f811edf5ec90af5a46b8c2de5b18c6d7dd3c3fcf051d16`
- finalize_e06.py：`6021b7e90efa6e6548ab5eb57db8eb60d9001d5854b88c4daa7c49f4e8ec75e5`
- author_nodes.py：`461523bf243f1e5a35bac22f01fe253295059967874b2258b65053888eec5430`
- author_upper.py：`304e4f4c1c6fa4a8019c0ea33cc78132a2f95b50bcc30c8c8434d7d2f1551cdb`
- clusters_level1.json：`1533f6c6c84bcdb6407f5d1a350cd019af722ee6bb2e9be2feb0460ebe62014c`
- clusters_level2.json：`b1e198014916815180c15fa69292eb4f588781c0c0560c6e2a7a0f10f895ca3d`
- clusters_level3.json：`66f2e9f67980ba9b10bc2b6ee74df38e41fbf589d5caa416535d775e030a709b`

审查者为当前模型、human_approved=false。独立核查确认本轮契约与保存依据一致，不意味着真人批准、独立gold、全库GraphRAG/RAPTOR复现或统计准确率改善。
