"""Render the final measured outcome without changing inputs or judgments."""
from effect_common import *

def pct(x):return '—' if x is None else f'{100*x:.1f}%'
def rate(x):return f"{x['correct']}/{x['total']}（{pct(x['rate'])}）"

def main():
    m=read(OUT/'results/metrics.json');d=read(OUT/'results/diagnostics.json');c=list(rows(OUT/'results/per_query_comparison.jsonl'));f=d['fee']
    h=m['strata']['holdout']['main'];delta=h['paired']['accuracy_delta_new_minus_old'];b=h['group_bootstrap_accuracy_delta']
    if delta>0:conclusion='新版在留出主集的三分类点估计更高；样本量仍不足以据此证明稳定收益。'
    elif delta<0:conclusion='新版在留出主集的三分类点估计下降，不能以本轮结果宣称效果提升。'
    else:conclusion='新版与旧版在留出主集的三分类准确率相同，本轮没有观察到该指标的增益。'
    lines=['# P0修复效果验证报告','',conclusion,'',
      '## 1. 实验回答什么问题','',
      '本轮隔离比较旧版与新版的法规证据装配。两组共用全库召回、DeepSeek排序、案例文本、候选机制、必要条件定义、范围提取及判断提示词；改变的是法规范围筛选、完整条文和上下文的装配顺序。完整读取器与取消两机制上限已在两组共同启用，其工程修复不能由本次对照单独归因于准确率增益。','',
      '36条全新合成业务输入按故事组划分为18开发、18留出；各含12主分析、6边界挑战。主分析为已有独立模型复核的银标，边界参考待裁决。配置在首次调用前冻结，未按结果调参、改参考或重跑择优。最终评分在全部推理终止后才打开参考。','',
      '## 2. 主要结果','',
      '| 分层 | 题数 | 旧版三分类准确率 | 新版三分类准确率 | 旧/新 macro-F1 | 仅旧正确 / 仅新正确 |','|---|---:|---:|---:|---:|---:|']
    names={'development':'开发','holdout':'留出'};anames={'main':'主分析','boundary':'边界挑战（暂定）'}
    for split in ('development','holdout'):
        for aset in ('main','boundary'):
            s=m['strata'][split][aset];o=s['arms']['old'];n=s['arms']['new'];p=s['paired']
            lines.append(f"| {names[split]}·{anames[aset]} | {s['n']} | {rate(o['classification']['accuracy'])} | {rate(n['classification']['accuracy'])} | {o['classification']['macro_f1']:.3f} / {n['classification']['macro_f1']:.3f} | {p['old_only_correct']} / {p['new_only_correct']} |")
    lines+=['',f"主要确认口径为留出12题主分析：新版减旧版准确率 {100*delta:+.1f} 个百分点；故事组配对bootstrap的95%描述区间为 [{100*b['lower']:.1f}, {100*b['upper']:.1f}] 个百分点。留出主集只有{h['group_count']}个故事组，区间不能作为充分的泛化证据。",'',
      '## 3. 判断质量细分','',
      '| 分层/版本 | 机制集合全对 | 必要条件整题全对 | 逐条件状态准确率 | unknown条件准确率 | 正常题误报数/分母 | 无效输出 |','|---|---:|---:|---:|---:|---:|---:|']
    for split in ('development','holdout'):
        for aset in ('main','boundary'):
            s=m['strata'][split][aset]
            for arm in ('old','new'):
                a=s['arms'][arm];p=a['predicates'];fa=a['false_alarms']['normal'];status=a['output_status']
                lines.append(f"| {names[split]}·{anames[aset]}·{'旧' if arm=='old' else '新'} | {rate(a['mechanisms']['exact_match'])} | {rate(p['reference_condition_states_exact'])} | {rate(p['status_accuracy'])} | {rate(p['unknown_status_accuracy'])} | {fa['risk_predictions']}/{fa['denominator']} | {status['missing']+status['invalid']} |")
    lines+=['','机制micro P/R/F1、完整混淆矩阵、Wilson区间、按题配对McNemar检验等见 results/metrics.json。条件指标只评预登记条件；额外候选条件单列未评分，风险机制多报照常计误报。unknown处理必须结合缺失条件与整题三分类读取。','',
      '## 4. 实际检索与证据预算','',
      '9639份文书、65475个结构检索单元；BM25与BGE各取100，1:1 RRF、c=60融合100。DeepSeek对每题100个候选逐对重排，按源文件去重取Top20；再以完整案例块装入4000字符预算。法规/解释另限4000字符。条件定义、范围信息和输出schema属于额外提示字段，两臂一致，不把它们隐去后宣称整次请求仅8000字符。','',
      '| 版本 | 案例字符均值 | 法规字符均值 | 累计展示法条项 | 累计展示案例项 | 累计待补读知识项 |','|---|---:|---:|---:|---:|---:|']
    for arm in ('old','new'):
        a=d['assembly'][arm];lines.append(f"| {'旧' if arm=='old' else '新'} | {a['case_chars']['mean']:.1f} | {a['legal_chars']['mean']:.1f} | {a['displayed_articles']} | {a['cases_shown']} | {a['omitted_knowledge_items']} |")
    lines+=['','表内累计项含跨题重复，不是独立文书数；法条数量更多不等于更有帮助。所有36对的案例文本哈希及展示ID一致。1504个去重RRF候选均经全量读取器回读，其中1151个在旧便携快照之外；这只证明读取覆盖得到扩展。',
      f"重排引用字面不匹配为 {d['rerank_quote_invalid_pairs']}/{d['rerank_total_pairs']} 对；保留原分数并单列该问题，没有按语义好坏重排重试。判断环节的字面引用与展示ID有效性仅为机械校验，不能当作证据充分率或法律适用准确率。",'',
      '## 5. 调用、费用及可复现性','',
      f"总任务 {f['unique_tasks']}，实际尝试 {f['attempts']} 次；状态分布 {f['by_status']}。保守峰值费用记账 {f['booked_peak_bound_usd']:.6f} 美元，授权硬上限2美元，未知计费次数 {f['unknown_usage_count']}；该金额不是供应商账单。输入token {f['prompt_tokens']:,}，输出token {f['completion_tokens']:,}。返回模型名与次数：{f['returned_models']}。",'',
      '协议、题面、提示、参数、知识资产及源程序在首次调用前以944项SHA-256绑定；动态判断任务另有内容哈希。所有尝试、结构修正重试、用量、原始回复与接受结果保留。失败按固定分母计错，不从指标中删除。官方费率证据及链接见 contracts/price_snapshot.json。','',
      '## 6. 如何使用结论','',
      '本轮结果用于决定是否继续采用新版法规装配，并定位必要条件、范围筛选和证据预算的问题。工程修复已经通过的部分与模型实测收益分开报告。银标及小样本不能替代金融专家评审；边界挑战只作诊断。此处没有为新36题建立全库相关案例集合，因此没有报告真实全库Recall、MRR或NDCG；机制标签的recall也不能冒充文书召回率。','',
      '## 7. 验收文件','',
      '- results/metrics.json：四分层完整指标。','- results/per_query_comparison.jsonl：36题新旧配对结果与参考身份。','- results/normalized_predictions.jsonl：72条评分输入。','- results/diagnostics.json：预算、有效性、费用与引用诊断。','- api_jobs/、api/：冻结请求、原始尝试、接受结果和共用账本。','- audit/：每题装配、范围决策、展示ID、未装入项与覆盖诊断。','- contracts/pre_inference_freeze.json：首次调用前输入指纹。','',
      '本轮结果尚未自动上传GitHub。']
    text='\n'.join(lines)+'\n'
    text=text.replace('## 4. 实际检索与证据预算','''## 3.1 不能被总分类分数掩盖的问题

1. **导航候选在判断阶段成了限制。** 所有12条多机制题均有预登记条件没有进入判断：开发主集6题漏17项，留出边界6题漏25项。其中8题漏掉参考阳性或待核机制，共13个机制项（5阳性、8待核）。候选没有截为两个，并不代表覆盖完整；问题不是已证明的初召回失败。两臂共享该限制，法规装配无法补回未提供的机制。
2. **总分类正确仍可能漏报或多报风险。** 025仅报M01/M02漏M11，028仅报M05/M06漏M04；031报M09漏M07/M08，034报M03/M12漏M10。留出主集003总分类正确，但把M02冒名多报为M01+M02，机制集合实际仅11/12全对。
3. **明确语义错误尚存。** 开发主集026明示“如实说没明白”，两臂均反向解释为“谎称未明白”，导致误报；开发边界024的外呼目的尚不明确且未拨号，两臂补成“仍准备营销”而误报。引用逐字存在没有防住语义反转与补事实。
4. **范围标记不能充当法律正确性标注。** 旧版2个被模型范围侧表标记不匹配的引用均为L002-A0035，新版为0。该条规定保险公司回访；输入同时包含代理人和公司回访背景，是否引用为背景、是否错误外推主体须分开核查，不能把2→0宣称为法律误引率下降。
5. **下一步价值最高的是完整机制核查与事实三态约束。** 将导航只作阅读顺序，增加未触发机制的轻量兜底核查；重点保护如实/不实、本人/他人、已发生/拟安排、确定/缺失事实。此建议由本轮结果产生，尚未改代码或追加推理验证，不能写成已解决。

留出12题全对的Wilson 95%区间约75.8%—100%。配对bootstrap的[0,0]只是本样本所有差值为零导致的退化结果，不表示总体差值已确定为零、也不证明两方案等效。小样本和参考身份须与分数一起展示。

## 4. 实际检索与证据预算''')
    (OUT/'效果验证报告.md').write_text(text,encoding='utf-8')
    print(json.dumps(dict(report=str(OUT/'效果验证报告.md'),conclusion=conclusion),ensure_ascii=False))

if __name__=='__main__':main()
