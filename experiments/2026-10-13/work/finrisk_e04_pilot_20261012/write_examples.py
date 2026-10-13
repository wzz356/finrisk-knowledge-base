"""Render selected actual contexts and existing grades; never assigns grades."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E04小批量实验_20261012"
DATA = {}
for phase in ("dev", "confirmation"):
    for line in (OUT / (phase + "_evaluation") / "per_query_metrics.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        DATA[(row["query_id"], row["arm"])] = row


def quoted(text):
    return "\n".join("> " + s for s in text.splitlines())


def example(qid, arm, fid):
    row = DATA[(qid, arm)]
    hit = next(h for h in row["top5"] if h["file_id"] == fid)
    return f"**{arm}第{hit['rank']}位，{fid}；片段{hit['context_help_grade']}分、全文{hit['help_grade']}分。**\n\n实际返回片段：\n\n{quoted(hit['returned_hit']['text'])}\n\n模型判断：{hit['context_reason']}\n"


parts = ["""# E04失败与边界样例

完成于2026-10-13。以下原话直接从本轮实际Top5输出提取，不是重新生成的证据；0–3分为模型判断，≥2分算对当前输入有用。文书ID可以在对应阶段的`per_query_metrics.jsonl`中查询完整原文指纹、原文区间、证据引用和判断限制。这里没有核定现行法律适用。

## 1. Q009：提高BM25权重获得条件核查材料，仍不是直接同机制案例
"""]
parts += ["输入：" + DATA[("Q009", "A0")]["query_text"] + "\n", example("Q009", "A0", "F008841"),
          "A0只有主题相近或无关材料，有用片段0/5。A1变为2/5，但新增材料的作用主要是核查给付条件和疾病范围：\n",
          example("Q009", "A1", "F001323"), example("Q009", "A1", "F009934"),
          "解释：F001323涉及不同保险产品，只能说明需要检查触发条件、给付标准和限制；F009934有疾病范围错误表述，但没有“诊断后立即支付”的事实。不能把2/5解释为直接匹配的重疾险承诺已经解决。\n",
          "## 2. Q012：候选已经入池，扩大池仍未找到有用支撑\n",
          "输入：" + DATA[("Q012", "A0")]["query_text"] + "\n",
          example("Q012", "A3", "F001375"), example("Q012", "A3", "F008940"),
          "F008944在A3第5位返回与F008940完全相同的文本，也仅1分；两个位置没有增加独立判断信息。四配置本题均0/5。已知锚点早已进入RRF第23及rerank第23，单纯扩大候选池没有解决对服务便利、速度承诺的机制辨别。可以研究具体事实背景和证据去重，但不能未经事件/主体核查删除两份原文。\n",
          "## 3. C001：直接证据有用，另一片段缺主体且机制不同\n",
          "输入：" + DATA[("C001", "A0")]["query_text"] + "\n",
          example("C001", "A0", "F000292"), example("C001", "A0", "F006493"),
          "解释：前者直接对应投保车险赠送合同外洗车券；后者是“不实优惠/中奖”及个人责任条目，输入没有说赠券虚假。F006493全文没有同样的主体缺失警示，实际片段有1处模型警示。警示表示可能误用，尚非人工确认错误。A0/A3本题均2/5。\n",
          "## 4. C002：已有强证据，Top5余项仍缺具体判断帮助\n",
          "输入：" + DATA[("C002", "A0")]["query_text"] + "\n",
          example("C002", "A0", "F000248"), example("C002", "A0", "F001943"),
          "解释：首位清楚保留三项组合事实；笼统的误导课件/代抄提示语不能代替领取式文案、稀缺催单和健康告知缺失的具体机制。A0/A3仍只有1/5有用。扩大池还引入了一项0分结果，平均片段分从1.2降到1.0。\n",
          "## 5. C007：全文有条件细节，返回片段只剩标题\n",
          "输入：" + DATA[("C007", "A0")]["query_text"] + "\n",
          example("C007", "A0", "F003464"), example("C007", "A0", "F009488"),
          "解释：F003464全文记载套打批单、提前给本金等事实，因此全文2分；实际只有标题，片段1分。F009488与第2位F009491的实际文本相同，均能作合同内/外利益的边界对照，但占了两个位置。不能因为反面案例处罚过就把当前合同内兑现认定违规。A0/A3均2/5。\n",
          "## 6. C008：条件相反也可以有帮助，须明确只作边界对照\n",
          "输入：" + DATA[("C008", "A0")]["query_text"] + "\n",
          example("C008", "A0", "F001950"),
          "解释：返回片段保留“人员证件过期、机构无许可证”等关键条件，帮助核实实际参与对象、资格范围和有效期间。输入已经核验机构合法资格，不能据此直接按无资格销售认定；这类条件说明也属于检索支撑。A0/A3均5/5有用，但不代表当前输入的最终风险判断已完成。\n",
          "## 评分局限\n\n以上评分均非人工金标。确认评分者部分接触过查询作者的机制/条件说明，开发又复用了同输入旧评分，存在共同偏差与尺度差异。完整限制见实验报告第8节，具体接触记录见`confirmation_judgments/notes_p1.md`、`notes_p2.md`、`notes_p3.md`。\n"]
(OUT / "失败样例.md").write_text("\n".join(parts), encoding="utf-8")
print("rendered 6 evidence examples from existing actual contexts")
