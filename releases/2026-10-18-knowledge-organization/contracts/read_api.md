# 知识组织增强读取接口

本组件提供离线只读接口，不包含Agent循环。基础检索仍面对9639份文书、65475个结构化单元；59份材料属于本轮知识组织范围，不能用来过滤全库检索。

## 载入

`code/kb_facade.py`是公开导入入口。调用方从可信的交付版本锁取得清单SHA，显式传入，不在加载时现场计算“期望SHA”。基础五项版本、法规67条清单、增强层清单和案例读取快照分别核验；版本不一致拒绝。

```python
from kb_facade import KnowledgeFacade
from common import read

root = ...  # 解压后的交付根目录，Path类型
case_lock = read(root / 'case_reader/pilot_lock.json')
knowledge_lock = read(root / 'expanded/contracts/knowledge_lock.json')
kb = KnowledgeFacade(
    root, case_lock, profile='expanded',
    expected_knowledge_manifest_sha256=knowledge_lock['manifest_sha256'],
)
```

`pilot`为四机制实验配置；`expanded`为12机制阅读配置，须显式选择及使用对应锁。扩展阅读配置没有自动启用任何检索前缀或辅助候选路。案例快照只覆盖交付中登记的单元，实际服务可由全库检索结果另行构建并固定快照。

## 六个公开接口

| 接口 | 用途及重要限制 |
| --- | --- |
| `list_mechanisms()` | 读取L0目录、状态和L1/L2入口。机制是检索与核查候选，不是当前输入的确定风险。 |
| `read_mechanism(mechanism_id, level='L0')` | L0名称/概览；L1条件/范围；L2返回登记案例原句及法规。没有检索单元的引文仍可通过L2读取，unit_id保持空。 |
| `read_article(article_id, include_dependencies=True, as_of=None)` | 读取67条中的条文、依赖和完整来源版本信息。包括实际效力证据截止日、待核状态和原件缺口；as_of不自动证明历史适用。 |
| `read_case(unit_id, layer='hit')` | hit为命中原句，extended为登记上下文；supplement仅向完成细分审核的单元开放。保留机构/个人/责任归属及unknown。 |
| `get_evidence_bundle(mechanism_id, unit_ids, budget_chars=8000)` | 分别最多4000字符案例、4000字符法规/指引；也接受多机制列表和明确分项预算。只装配调用方给定案例，不自动把机制卡的其他案例混入。 |
| `coverage(mechanism_id)` | 分别说明本轮材料范围、依赖阅读、规范适用未知项和预算状态；不代表全库相关性完整。 |

额外辅助函数`get_dependencies(article_ids, limit=32)`供离线维护与审计使用。

## 证据使用

- 原文引文保留file_id、Unicode字符半开区间、正文SHA和来源SHA。处罚文书原句、法规快照、助手解释分别标识。
- 历史案例及规范不能自动补齐当前输入事实。证据包返回`current_input_facts_assessed=false`，核查条件为`not_assessed`；外部判别环节负责结合当前输入判断。
- 超预算只省略完整证据块，同时返回省略ID和`partial`；不会截去例外条款后宣称阅读完整。依赖可完整读取，不等于每次8000字符包均能容纳全部依赖。
- 候选主体/行为关联只用于定位，不构成独立归责证明；`unknown`、`None`和歧义标记不自动转为否定。
- 返回深拷贝。未知ID、任意未登记span、错误版本/SHA和不允许的阅读层会被拒绝。

所有本轮审核均为助手模型审核，`human_approved=false`；法规研究参考与生产准入分开，当前未自动启用生产。
