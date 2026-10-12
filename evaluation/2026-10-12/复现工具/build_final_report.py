"""Build reviewable reports from frozen experiment outputs; never change scores."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/finrisk_retrieval_20261012'
OUT = ROOT / 'outputs/FinRisk_召回实验_20261012'
TASKS = ROOT / 'outputs/FinRisk_剩余全量准备_20261011/tasks'


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def write(name, text):
    (OUT / name).write_text(text.rstrip() + '\n', encoding='utf-8')


def dump(name, value):
    write(name, json.dumps(value, ensure_ascii=False, indent=2))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percent(value):
    return f'{100 * value:.1f}%'


def esc(value):
    return str(value).replace('|', '／').replace('\n', ' ').replace('\r', '')


def block(value):
    return '\n'.join('> ' + line for line in value.splitlines())


ARMS = [('raw', 'bm25'), ('raw', 'rrf_rerank'), ('structured', 'bm25'),
        ('structured', 'dense'), ('structured', 'rrf'), ('structured', 'rrf_rerank')]
NAMES = {('raw', 'bm25'): '原文 BM25', ('raw', 'rrf_rerank'): '原文双路→RRF→重排',
         ('structured', 'bm25'): '结构化 BM25', ('structured', 'dense'): '结构化 BGE',
         ('structured', 'rrf'): '结构化双路→RRF',
         ('structured', 'rrf_rerank'): '结构化双路→RRF→重排'}
GROUPS = {'marketing_sales': '营销销售', 'other_insurance_operations': '其他保险经营',
          'boundary_condition_change': '条件改变与边界'}


def main():
    queries = {x['query_id']: x for x in lines(OUT / 'queries.jsonl')}
    per = {(x['query_id'], x['corpus'], x['arm']): x for x in lines(OUT / '指标/per_query_metrics.jsonl')}
    metric = json.loads((OUT / '指标/metrics.json').read_text(encoding='utf-8'))
    aggregate = {(x['corpus'], x['arm']): x for x in metric['metrics']}
    results = {(x['query_id'], x['corpus'], x['arm']): x for x in lines(OUT / 'retrieval_results.jsonl')}
    judgments = {x['pair_id']: x for x in lines(OUT / '指标/validated_judgments.jsonl')}
    pool = {x['pair_id']: x for x in lines(OUT / '评估标注/blind_judgment_pool.jsonl')}
    pool_qf = {(x['query_id'], x['file_id']): x for x in pool.values()}
    provenance = lines(OUT / '评估标注/judgment_provenance.jsonl')
    provenance_c = collections.defaultdict(list)
    for x in provenance:
        provenance_c[(x['pair_id'], x['context_id'])].append(x)
    independent = lines(OUT / '评估标注/independent_audit_judgments.jsonl')
    independent_pool = {x['pair_id']: x for x in lines(OUT / '评估标注/independent_audit_pool.jsonl')}
    audit = json.loads((OUT / '运行完整性检查.json').read_text(encoding='utf-8'))
    run = json.loads((OUT / 'retrieval_results.jsonl.run.json').read_text(encoding='utf-8'))
    assert metric['status'] == 'complete' and audit['status'] == 'passed' and run['status'] == 'complete'
    assert len(queries) == 50 and len(per) == 300 and len(pool) == len(judgments) == 671
    assert len(independent) == len(independent_pool) == 24

    agreement = {'status': 'complete', 'evaluation': 'fresh_context_model_assisted_algorithm_blind_rescoring',
                 'human_approved': False, 'pairs': 24, 'contexts': 0,
                 'file_exact_grade_agreements': 0, 'file_useful_threshold_agreements': 0,
                 'file_misleading_flag_agreements': 0, 'context_exact_grade_agreements': 0,
                 'context_useful_threshold_agreements': 0, 'context_misleading_flag_agreements': 0,
                 'exact_positive_quote_checks': 0, 'disagreements': [],
                 'initial_judgments_preserved': True,
                 'sampling_note': '每组8个不同查询、每查询随机1个合并池文件；固定种子2026101224。样本不是总体比例抽样。'}
    for second in independent:
        first = judgments[second['pair_id']]
        source = independent_pool[second['pair_id']]
        assert sha_text(source['full_source_text']) == source['source_sha256']
        assert source == pool[second['pair_id']]
        assert second['help_grade'] in range(4)
        if second['help_grade'] >= 2:
            assert second['source_quote']
        if second['source_quote']:
            assert second['source_quote'] in source['full_source_text']
            agreement['exact_positive_quote_checks'] += 1
        agreement['file_exact_grade_agreements'] += first['help_grade'] == second['help_grade']
        agreement['file_useful_threshold_agreements'] += (first['help_grade'] >= 2) == (second['help_grade'] >= 2)
        agreement['file_misleading_flag_agreements'] += first['misleading_risk'] == second['misleading_risk']
        source_contexts = {x['context_id']: x for x in source['contexts']}
        first_contexts = {x['context_id']: x for x in first['contexts']}
        assert {x['context_id'] for x in second['contexts']} == set(source_contexts)
        context_diffs = []
        for s in second['contexts']:
            f = first_contexts[s['context_id']]
            sc = source_contexts[s['context_id']]
            assert s['help_grade'] in range(4)
            if s['help_grade'] >= 2:
                assert s['evidence_quote']
            if s['evidence_quote']:
                assert s['evidence_quote'] in sc['text'] and s['evidence_quote'] in source['full_source_text']
                agreement['exact_positive_quote_checks'] += 1
            agreement['contexts'] += 1
            agreement['context_exact_grade_agreements'] += f['help_grade'] == s['help_grade']
            agreement['context_useful_threshold_agreements'] += (f['help_grade'] >= 2) == (s['help_grade'] >= 2)
            agreement['context_misleading_flag_agreements'] += f['misleading_risk'] == s['misleading_risk']
            if f['help_grade'] != s['help_grade'] or f['misleading_risk'] != s['misleading_risk']:
                context_diffs.append({'context_id': s['context_id'], 'first_grade': f['help_grade'],
                                      'second_grade': s['help_grade'], 'first_misleading': f['misleading_risk'],
                                      'second_misleading': s['misleading_risk'],
                                      'first_reason': f['reason'], 'second_reason': s['reason']})
        if first['help_grade'] != second['help_grade'] or context_diffs:
            agreement['disagreements'].append({'pair_id': second['pair_id'], 'query_id': source['query_id'],
                                               'file_id': source['file_id'], 'first_grade': first['help_grade'],
                                               'second_grade': second['help_grade'], 'first_reason': first['reason'],
                                               'second_reason': second['reason'], 'contexts': context_diffs})
    assert agreement['contexts'] == 38
    dump('指标/独立复标一致性.json', agreement)
    am = ['# 独立复标一致性', '', '这是隐藏算法和原分值的模型复标，不是人工验收。两个判读过程来自同一模型体系，不能当作不同人类或不同模型的可靠性证明。', '',
          '| 比较项 | 一致数/总数 | 一致率 |', '|---|---:|---:|']
    for key, label, n in [('file_exact_grade_agreements', '文件0—3分完全一致', 24),
                           ('file_useful_threshold_agreements', '文件是否有用（≥2分）', 24),
                           ('file_misleading_flag_agreements', '文件误导风险标记', 24),
                           ('context_exact_grade_agreements', '片段0—3分完全一致', 38),
                           ('context_useful_threshold_agreements', '片段是否有用（≥2分）', 38),
                           ('context_misleading_flag_agreements', '片段误导风险标记', 38)]:
        am.append(f'| {label} | {agreement[key]}/{n} | {percent(agreement[key]/n)} |')
    am += ['', '两次评分没有跨越“有用/无用”阈值的分歧，因此本次抽样不会改变主指标中的有用数量。2/3分及误导标记存在分歧，强支持覆盖和风险标记仍需人工核定。初评分未覆盖、未修改；总表继续使用冻结初评。', '',
           '抽样：营销、其他经营、边界各8个查询，每查询从合并候选池随机取一个文件，种子2026101224。共24份query-file、38种返回上下文。它是小样本一致性核验，不代表671份配对或全部8509份候选的验收。', '',
           '## 全部分歧', '', '| 查询/文件 | 文件初评→复标 | 文件理由差别 |', '|---|---|---|']
    for d in agreement['disagreements']:
        am.append(f"| {d['query_id']} / {d['file_id']} | {d['first_grade']}→{d['second_grade']} | {esc(d['first_reason'])}；复标：{esc(d['second_reason'])} |")
    am += ['', '| 查询/文件 | 片段ID | 分数初评→复标 | 风险标记初评→复标 | 理由差别 |', '|---|---|---|---|---|']
    for d in agreement['disagreements']:
        for c in d['contexts']:
            am.append(f"| {d['query_id']} / {d['file_id']} | {c['context_id']} | {c['first_grade']}→{c['second_grade']} | {c['first_misleading']}→{c['second_misleading']} | {esc(c['first_reason'])}；复标：{esc(c['second_reason'])} |")
    am += ['', '尤其应核定Q039的日期截断、Q044的行为背景与正文归属、Q050的机构费用机制截断；纯不相关本身不等于误导。', '',
           '[复标原始判断](评估标注/independent_audit_judgments.jsonl) · [抽样清单](评估标注/independent_audit_manifest.json) · [机器可读一致性](指标/独立复标一致性.json)']
    write('独立复标记录.md', '\n'.join(am))

    pairs = []
    for left, right in [(('structured','rrf'), ('structured','bm25')),
                        (('structured','rrf_rerank'), ('structured','rrf')),
                        (('structured','rrf_rerank'), ('raw','rrf_rerank')),
                        (('raw','rrf_rerank'), ('raw','bm25'))]:
        d = {'left': list(left), 'right': list(right), 'queries': 50}
        for field in ['useful_at5', 'context_useful_at5']:
            values = [round(per[(q,*left)][field] - per[(q,*right)][field], 8) for q in sorted(queries)]
            d[field] = {'mean_difference': sum(values)/50,
                        'better_queries': sum(v>0 for v in values), 'tied_queries': sum(v==0 for v in values),
                        'worse_queries': sum(v<0 for v in values)}
        pairs.append(d)
    dump('指标/同查询成对差异.json', {'status':'complete', 'comparisons':pairs,
                                      'note':'描述同一50条开发查询的改进/持平/退步；没有做显著性或总体外推。'})

    qmd = ['# 50条查询逐项对照', '', '单元格为“有用文件数/5；有用片段数/5”，帮助度≥2算有用。文件看完整原文，片段只看实际返回内容；缺失位计0。所有数字来自冻结初评，不是人类验收。', '',
           '| 查询 | 分组 | 输入 | ' + ' | '.join(NAMES[a] for a in ARMS) + ' |',
           '|---|---|---|' + '---:|'*len(ARMS)]
    for q, query in sorted(queries.items()):
        values = []
        for c, a in ARMS:
            r = per[(q,c,a)]
            values.append(f"{round(r['useful_at5']*5)}/5；{round(r['context_useful_at5']*5)}/5")
        qmd.append(f"| {q} | {GROUPS[query['group']]} | {esc(query['text'])} | " + ' | '.join(values) + ' |')
    qmd += ['', '[完整来源、机制与条件](查询清单.md) · [逐查询文件排名与评分](指标/per_query_metrics.jsonl) · [完整Top20和各阶段Top100](retrieval_results.jsonl)']
    write('逐查询对照.md', '\n'.join(qmd))

    examples = [
        ('Q004', '利率比较：重排有改善，也存在比较对象被切断的片段', [('F004440','Cbfb137ee5d16'), ('F002283','C6b0d4c8aa548')],
         '重排在本题将有用文件从RRF的2/5提升到5/5；简表直接点明片面比较也可以有用。另一文书的返回片段在“银行”前切断，不能把全文帮助度自动赋给片段。'),
        ('Q009', '确诊即赔：可替代来源命中，重排却提升了相邻机制', [('F009411','C2abf4b085c0c'), ('F007481','C6fc40acdfd8f')],
         '已知来源F009587没有进入结构化RRF的Top20，F009411等其他文件仍提供直接依据。RRF有用4/5，重排后1/5。F009408、F009411、F009412涉及同一2022-05-12产说会，不是三件独立事件。'),
        ('Q012', '服务时效夸大：所有方法Top5均未找到有用支持', [],
         '六组均0/5。F000699实际有理赔手续、时效被夸大宣传的事实，结构化BM25文书排名8、RRF排名15、重排排名9，均在Top5之外。这是排序与选取失败，不是原文缺失。'),
        ('Q014', '交强险入口限制：机制可见，完整监管理由仍被切断', [('F000852','Ce99b81ad1d15')],
         '文件3分、片段2分，仍算有用；检查片段结尾“限制了消费者通”及全文中的反驳理由，区分不完整支持与完全无帮助。'),
        ('Q017', '无资质银行网点：同类人员文书也能直接支持', [('F001197','Cd05388176d53')],
         '已知来源为F001198，但F001197完整记载3家无兼业许可证网点、借款人意外险与手续费，文件和片段均3分。不要只凭命中指定文件评判检索。'),
        ('Q022', '虚列费用：全文有类比价值，返回正文串到了另一行为', [('F002401','C286bed84d7da')],
         '全文虚列会议费的渠道资金用途有类比帮助，片段却只显示该背景与未发展业证处罚。原文引文位置正确仍不足以证明行为与片段关联正确。'),
        ('Q032', '准备金压低：重复单元挤占候选，另有申辩片段风险', [('F001369','Cdbd1dad37814')],
         '结构化BM25的100个候选只有3个文件、10种正文，Top5实际只返回3份。重排中的F001369片段仅呈当事人申辩，缺少完整监管回应，不能把申辩当结论。'),
        ('Q039', '职业责任险：限额不足不能替代期间断档事实', [('F002377','Cbc5d9b183a34')],
         '全文具体事实是赔偿限额不足；监管泛称有效性与连续性，不能据此补出两张保单之间的断档日期。此文件1分，宽泛主题接近而具体机制不同。'),
        ('Q046', '真实代理服务：相反事实可帮助识别条件边界', [('F003387','C67e3a72736ca'), ('F003387','Cab0f6fc2a5ba')],
         '原案无资格来源、挂名代理、代开发票套费，能提示真实服务输入应核对哪些差异；它不能证明输入违法或合规。保留全链条的片段3分，切断链条的原文片段1分。'),
        ('Q049', '公估报告：相邻否定条件不排除另一独立风险', [('F000398','C92ed1f85c04a')],
         '没有从保险公司领款不等于公估报告已说明条款依据。初评片段2分、独立复标3分，两者都认为有用；这是强度差异，不是有用与否分歧。'),
        ('Q050', '来源企业返利：受益身份和机构资质不能混用', [('F005645','C98fed9b5f288'), ('F005645','Cf00ea1f4361d')],
         '两个片段均提供身份核对线索；第一个截断机构销售费机制，独立复标额外标记风险。来源企业是否投保人、是否具代理资质需要分别核实。')
    ]
    packet = ['# 人工验收样例', '', '共11条查询，覆盖支持成功、Top5失败、重排退步、片段截断、行为串联及相反条件。它是定向诊断样例，不是随机质量抽样。另有独立复标24个随机样本供补充验收。', '',
              '每个文件分数只表示对该查询的帮助度：0无帮助，1宽泛线索，2明确机制或边界帮助，3较完整事实与条件支持。≥2算有用。请分别判断完整文书和实际返回片段，并检查主体、否定、申辩/监管认定和适用条件。', '',
              '所有现有分数由模型辅助判读；以下复核栏留空，等待你的人工验收。先看输入与返回内容，给出自己的判定，再参考模型理由会更有利于发现分歧。', '',
              '[总报告](实验报告.md) · [全部查询对照](逐查询对照.md) · [独立复标记录](独立复标记录.md)']
    source_dir = OUT / '人工验收原文'
    source_dir.mkdir(exist_ok=True)
    exported = {}

    def export_source(fid):
        if fid not in exported:
            source = json.loads((TASKS / (fid + '.json')).read_text(encoding='utf-8'))
            raw = source['full_text']
            assert sha_text(raw) == source['text_sha256']
            target = source_dir / (fid + '.txt')
            target.write_bytes(raw.encode('utf-8'))
            assert sha(target) == source['text_sha256']
            exported[fid] = {'file': str(target.relative_to(OUT)).replace('\\','/'),
                             'text_sha256': source['text_sha256']}
        return f'[完整原文 {fid}](人工验收原文/{fid}.txt)'

    for qid, title, targets, commentary in examples:
        q = queries[qid]
        packet += ['', f'## {qid} {title}', '', q['text'], '', commentary, '',
                   '| 检索方案 | 有用文件 | 有用返回片段 |', '|---|---:|---:|']
        for c,a in ARMS:
            r = per[(qid,c,a)]
            packet.append(f"| {NAMES[(c,a)]} | {round(r['useful_at5']*5)}/5 | {round(r['context_useful_at5']*5)}/5 |")
        for fid,cid in targets:
            source = pool_qf[(qid,fid)]
            j = judgments[source['pair_id']]
            ctxt = next(c for c in source['contexts'] if c['context_id']==cid)
            cj = next(c for c in j['contexts'] if c['context_id']==cid)
            methods = '；'.join(f"{NAMES[(x['corpus'],x['arm'])]}第{x['rank']}位" for x in provenance_c[(source['pair_id'],cid)])
            packet += ['', f"### {fid} / {cid}", '', export_source(fid), '',
                       f"配对ID：`{source['pair_id']}`。出现位置：{methods}。", '',
                       f"模型初评：文件{j['help_grade']}分，片段{cj['help_grade']}分；片段误导风险标记：{'是' if cj['misleading_risk'] else '否'}。", '',
                       '实际返回片段（含检索前缀，完整展示该片段）：', '', block(ctxt['text']), '',
                       f"全文理由：{j['reason']}。片段理由：{cj['reason']}。", '',
                       '适用限制：' + '；'.join(j['limitations']) if j['limitations'] else '适用限制：初评未额外列出；仍须核对输入条件。', '',
                       '人工复核：文件分数____；片段分数____；是否有用____；是否误导____；需要补充的条件/不同意见____。']
        if qid == 'Q012':
            fid='F000699'
            hit=next(x for x in results[(qid,'structured','rrf_rerank')]['files'] if x['file_id']==fid)
            packet += ['', export_source(fid), '', f"诊断：结构化重排实际第{hit['rank']}位（不在评分Top5中，未擅自补进主评分）。返回单元 `{hit['unit_id']}`：", '',
                       block(hit['text']), '', '人工复核：该文书是否确有本题帮助____；Top5泛称销售误导是否只能算1分____；排序失败的原因____。']
        if qid == 'Q009':
            packet += ['', '同一事件的机构与人员文书：' + ' · '.join(export_source(fid) for fid in ['F009408','F009411','F009412']) + '。请确认事件相同，并区分不同当事人的责任。']
        if qid == 'Q032':
            packet += ['', '[100个单元的来源分布](Q032拥挤诊断.json)。人工复核：重复归属是否应合并检索、保留多主体链接____。']
    write('人工验收样例.md', '\n'.join(packet))
    dump('人工验收原文/manifest.json', {'status':'complete', 'files':exported, 'human_approved':False,
                                        'note':'原始full_text原样另存，UTF-8字节SHA与任务text_sha256完全一致。'})

    table = ['| 方案 | 有用文件@5 | 有用片段@5 | 至少1份有用文件 | 至少1份3分文件 | 片段误导风险标记 |',
             '|---|---:|---:|---:|---:|---:|']
    for key in ARMS:
        m=aggregate[key]
        table.append(f"| {NAMES[key]} | {percent(m['useful_at5'])} | {percent(m['context_useful_at5'])} | {percent(m['support_coverage_at5'])} | {percent(m['strong_coverage_at5'])} | {percent(m['context_misleading_at5'])} |")
    grouped = ['| 查询组 | 原文BM25：文件/片段 | 原文全链路：文件/片段 | 结构化BM25：文件/片段 | 结构化BGE：文件/片段 | 结构化RRF：文件/片段 | 结构化全链路：文件/片段 |',
               '|---|---:|---:|---:|---:|---:|---:|']
    for group,label in GROUPS.items():
        values=[]
        for key in ARMS:
            m=aggregate[key]['by_group'][group]
            values.append(percent(m['useful_at5'])+'/'+percent(m['context_useful_at5']))
        grouped.append(f'| {label}（{20 if group != "boundary_condition_change" else 10}题） | '+' | '.join(values)+' |')
    paired_md=['| 同查询比较（左方案相对右方案） | 文件平均差值 | 文件提升/持平/退步题数 | 片段平均差值 | 片段提升/持平/退步题数 |',
               '|---|---:|---:|---:|---:|']
    for d in pairs:
        f=d['useful_at5'];c=d['context_useful_at5']
        paired_md.append(f"| {NAMES[tuple(d['left'])]} 相对 {NAMES[tuple(d['right'])]} | {f['mean_difference']*100:+.1f}个百分点 | {f['better_queries']}/{f['tied_queries']}/{f['worse_queries']} | {c['mean_difference']*100:+.1f}个百分点 | {c['better_queries']}/{c['tied_queries']}/{c['worse_queries']} |")
    aux=['| 方案 | 合并已判读池内nDCG@5 | 已知来源Hit@5 | 已知来源Hit@10 | 已知来源Hit@20 |',
         '|---|---:|---:|---:|---:|']
    for key in ARMS:
        m=aggregate[key]
        aux.append(f"| {NAMES[key]} | {m['pool_ndcg_at5']:.3f} | {percent(m['known_source_hit_at5'])} | {percent(m['known_source_hit_at10'])} | {percent(m['known_source_hit_at20'])} |")
    report = f'''# FinRisk 知识库召回实验报告

日期：2026-10-12。状态：六组离线检索、帮助度初评、独立复标和完整性审计已完成；人工验收尚未进行。

## 实验结论

在8509份最新候选文书、50条冻结业务风险查询上，按你提出的 **BM25+BGE→RRF→rerank** 实际运行，结构化全链路Top5的**有用文件率为81.6%（204/250），有用返回片段率为76.0%（190/250）**。49/50条查询至少找到一份有用文件；这衡量对风险判断的帮助，不等于49条风险判断正确。

结构化RRF直接聚合的对应结果为**82.0%（205/250）和79.6%（199/250）**。本轮重排没有带来整体提升；文件差别仅1个Top5位置，不能据此宣称RRF普遍优于所有reranker。片段帮助度下降、部分营销查询明显退步，更值得处理。

同范围原文全链路为80.0%/72.0%；结构化全链路仅提升1.6/4.0个百分点。这是本开发集上的有限改善，**不是已经证明新库全面优于旧正式知识库**。原文基线取同一8509份文书，并未运行旧线上索引。

建议先把“证据单元去重、关键上下文完整、行为与证据正确关联”做扎实，保留RRF作为可复现的对照，再校准重排。现在的候选可以召回许多有用依据，也有可复核的失败，尚不能视作全库通过质量验收。

## 实际做了什么

1. 冻结50条查询后才运行检索：20条营销销售、20条其他保险经营、10条条件改变与边界。查询正文不带文件ID、原文标题或处罚结论。
2. 从8509份最新候选构建64109个结构化证据单元；同批原文切为20148个片段。结构化投影含20148个原文兜底单元。使用原文证据与保守的主体角色前缀，没有把推测摘要、风险标签值写进索引，也没有用标签硬过滤。
3. 执行六组对照，保留每题Top20文件、案例聚合结果、各阶段Top100单元、排名、分数及耗时。主指标在文件Top5上计算。
4. 合并六组Top5，隐藏算法、排名、检索分数和已知来源，对671个查询—文件配对、945种实际返回上下文分别评分。同一配对只判一次，同一上下文只判一次，避免每个算法自己打分。
5. 另取24个随机配对、38种上下文，由不知道初评分的独立模型上下文复标；保存全部分歧，未覆盖初评。
6. 核验源文件SHA、5692个原文位置、94307条模型输入记录、向量归一化、RRF计算与max聚合；完整性审计通过。检索规则15项测试通过。查询、模型版本、代码、配置和原始结果均已存档。

新增实验与报告保存在本工作区。桌面项目没有改写，正式审批状态与账本没有更新；未读取360份盲验正文或比赛题答案，未调用付费API，没有部署或上传本轮实验。

## 检索配置与公平比较范围

| 项目 | 实际配置 |
|---|---|
| BM25 | 复用项目实现与分词器；k1=1.5，b=0.75，权重1 |
| BGE | bge-small-zh-v1.5，512维；CLS向量、float32 L2归一化、余弦相似度精确检索 |
| 双路召回 | BM25 Top100 + BGE Top100，合并最多200个单元 |
| RRF | 两路等权，排名从1开始，分数为各路1/(60+rank)之和；取Top100 |
| rerank | bge-reranker-base 对查询—单元对重排；原始logit作为排序分数 |
| 聚合 | 单元→案例取max；案例/单元→文件取max；按文件输出Top20，评估Top5 |
| 切片 | 约300字符、40字符重叠，按标点边界处理；保留原文位置及歧义记录 |
| 运行 | RTX4060 Laptop 8GB，CUDA12.4，float16，batch16，max_length512 |

实际使用本机完整缓存的small/base模型，不是前次建议的BGE-M3。模型来源：[BGE模型卡](https://huggingface.co/BAAI/bge-small-zh-v1.5)、[reranker模型卡](https://huggingface.co/BAAI/bge-reranker-base)。固定snapshot与权重SHA见[运行与复现说明](运行与复现说明.md)。RRF公式可对照[官方说明](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)。检索分数不是违法概率。

六组为：原文BM25、原文双路融合重排、结构化BM25、结构化BGE、结构化双路RRF、结构化双路RRF重排。原文组复用同一来源集合、同一批查询和模型；结构化组共享同一投影。未做标签软召回、查询改写或多查询扩展，本次不评价这些技巧的额外收益。

结构化证据单元的前缀只有原文主体、角色元数据和原文行为背景，不能把原文位置正确等同于语义归属正确。原文兜底、重复归属及不同主体前缀也使两类索引的单元数量不同，因此差异不全可归因于“抽取更好”。

## 如何衡量“对判断有帮助”

| 分数 | 含义 |
|---|---|
| 0 | 没有相关风险机制或边界帮助 |
| 1 | 只有宽泛类别、近邻主题或不足以核对关键机制的线索 |
| 2 | 明确提供机制、条件或相反事实的对照帮助；简表也可以得2分 |
| 3 | 较完整的事实、条件与判别支撑 |

**≥2分算有用，不要求先充分证明输入违法。** 同类可疑机制及相反条件案例都可以帮助判断；后者用于提示边界，不能证明输入合规。泛称“销售误导”不能自动替代“确诊即赔”或“理赔速度夸大”等具体机制。

“有用文件率”看完整文书；“有用片段率”只看实际送给下游的返回单元。两者必须分开：全文有依据而返回片段切掉关键事实，实际RAG仍可能拿不到帮助。片段评分不会借用未返回的全文。

每题分母固定为5，缺失位置记0；结构化BM25的Q032只返回3份文件，另外2位记0。至少一份有用文件覆盖率按50条查询计算。误导风险标记表示片段有主体混淆、否定/关键条件遗漏或只呈申辩等风险，**不是实际下游误判率**。详情见[帮助度标注规范](帮助度标注规范.md)。

## 六组主结果

{chr(10).join(table)}

六组都在Q012失败，其余49题均有至少一份有用文件；覆盖率不能区分Top5的整体帮助质量。结构化RRF的误导风险标记为6/250，重排后16/250。这项标记存在复标分歧，需人工确认后再用作正式门槛。

### 按场景拆分

{chr(10).join(grouped)}

重排对“其他经营”组的文件帮助率由84%提高到87%，同时片段帮助率从82%下降到79%；对营销组则由78%/78%下降到75%/71%。边界组样本只有10题，比例变化尤其容易受单个位置影响，不宜外推。

### 同查询变化

{chr(10).join(paired_md)}

这是同50题的描述性差异，没有声称统计显著或总体优势。全部题目和六组有用数量见[逐查询对照](逐查询对照.md)。

## 问题主要在哪里

| 问题 | 实际证据 | 对RAG的影响 |
|---|---|---|
| 重排偏向近邻主题而非同一机制 | Q009：RRF有用4/5，重排后1/5；无行为能力人死亡保障、医生渠道等文书提升，确诊即赔直接证据退后 | 主题相近仍可能无法支撑当前风险判别 |
| 存在支持但排在Top5外 | Q012：F000699含理赔手续、时效夸大事实，结构化BM25第8、RRF第15、重排第9 | Top5均泛称销售误导，不能因库中有全文就认为实际召回成功 |
| 同文同正文重复进入召回池 | 64109个结构化单元只有39728种同文件精确正文；额外重复24381个，最多同正文182次。Q032的BM25 Top100只有10种正文、3个文件 | 在最终文件去重以前就占满候选，后续重排无法凭空补回没进入池的案例 |
| 片段缺少完整事实链与回应 | Q004比较对象切断；Q014监管理由半句；Q032的F001369只返当事人申辩 | 全文有用而片段不足；下游可能遗漏否定、条件或把申辩当认定 |
| 行为背景与正文关联错误 | Q022的F002401前缀是渠道费用背景，正文却是未发展业证处罚 | 子串和原文位置正确，语义证据仍可能接错 |
| 泛称案由不等于具体机制 | Q039的F002377事实是职业责任险限额不足，不能补出保险期间断档 | 同标签/同制度不保证对当前机制有帮助 |
| 不同文书其实同一事件 | Q009的F009408、F009411、F009412是同一产说会的机构/人员处罚 | 文件数可能看起来丰富，却不是独立案例多样性；须保留不同责任主体但识别事件关联 |

重复正文可能为了保留不同主体或归属，不直接等同于抽取错误；改进应合并检索文本、保留多案例/多主体链接，避免直接删除候选。截断问题包括切片边界和模型token截断两类，不能只归因于模型长度。

本次模型输入截断：结构化embedding544/64109（0.85%）、结构化重排20/5000（0.40%）；原文embedding与原文重排均0，查询也0。所有实际模型输入≤512 token。即使没有token截断，也可能早已在300字符切片时丢失后半句。

## 独立复标与可信度

24个随机配对中文件0—3分完全一致18/24（75.0%），**文件有用/无用一致24/24**；38种片段的分数完全一致32/38（84.2%），**有用/无用一致38/38**。本抽样没有改变有用数量的阈值分歧，2/3分强度和误导风险标记仍有差异。片段误导标记一致35/38，分歧全部保留在[独立复标记录](独立复标记录.md)。

复标为同模型体系的独立上下文判读；不是人类验收、不是独立专家一致性，也不能覆盖全池。初评与复标的所有2/3分判定均有通过连续原文核验的引文；0/1分不强制非空引文。没有静默覆盖初评分，也没有把人工审批改成通过。

查询由已阅读的100份定向审计材料中的27份来源构造，采用场景改写、条件改变和部分对照。虽然查询文字没有来源ID或标题，仍是**开发集**，存在来源选择偏差；不少查询附带审核意图，不能代表自然广告/业务文本的全部分布。当前不能证明官方27标签全部达到同样质量，也没有完整相关文书集合，因此不能给出全库真正的Recall@5。

已知来源只有43题可用，命中率仅作诊断：Q009没有命中指定来源仍召回同机制好案例，Q017的人员文书可替代机构来源。因此没有用“必须命中原文件”作为主评分。

### 辅助指标

{chr(10).join(aux)}

nDCG只在六组Top5合并后已判读的候选池内计算，0—3分转增益；不是全库完整相关集合的nDCG，不能充当真正召回率。Q012虽没有≥2分文书，但池内仍有1分近邻线索，因此该池内nDCG不必为0。

## 运行耗时与复现

真实六组GPU检索主运行用时{run['elapsed_seconds']:.1f}秒（约{run['elapsed_seconds']/60:.1f}分钟），包含模型加载、首次建向量、BM25建索引和50题检索重排。环境安装、材料准备及模型辅助评分不包含在这7.5分钟内。

模型加载22.3秒；50条查询向量批编码1.17秒；结构化/原文首次向量编码113.5/50.4秒；BM25建索引33.7/27.9秒。向量准备后，结构化BM25平均约1.944秒、dense约0.031秒、RRF约0.001秒、重排约0.697秒；这些是本机离线批实验阶段均值，不能宣称为线上端到端响应时间。

[运行与复现说明](运行与复现说明.md)含命令、依赖、GPU、固定模型快照与输入SHA；[运行完整性检查](运行完整性检查.json)含原文位置、向量和计算检查。15项检索规则测试、300行结果完整性与评分引文检查均通过，验证结论是实现及来源可追溯，不等于全部候选语义正确。

## 后续基础任务顺序

1. **合并重复检索单元并保留归属。** 同文件同正文先共享索引单元，case_id、behavior_id、主体和原文位置保留多值；对同事件不同处罚文书增加事件关联，控制Top5重复事件。验收时同时看有用率与独立事件覆盖。先做投影层，不删除原始候选。
2. **补齐关键父段与行为证据关联。** 召回精短事实后携带完整父段，重点保留“但/除外/未/申辩/复核认为”、日期区间和主体责任。抽检前缀与正文是否属于同一行为，优先修Q022/Q032/Q039类问题。控制token长度时拆单元或按父段回填，而非硬截掉事实结尾。
3. **用当前固定50题复测上述两项。** 当前RRF及全链路保留为基线；重新输出Top5并对新增配对判帮助度，确认去重/上下文回填没有牺牲机制召回。尚未执行这些改进，报告没有声称它们的收益已被测出。
4. **校准reranker再决定正式配置。** 收集Q009等机制近邻负例，输入真正的风险句及必要条件，比较重排输入形式和模型；检查是否能提高片段帮助度、减少退步。现阶段不应因为采用了rerank就默认它更好，也不据本轮直接删除该阶段。
5. **人工验收并扩展评估集。** 先核定[11条诊断样例](人工验收样例.md)和24个独立复标样本，形成可复用帮助度标准；随后覆盖自然风险文本、27类标签和更广来源，另留测试集。后续将风险标签作为软线索的效果单独做消融，不用标签硬过滤掩盖漏召回。

这些是后续改进清单，本轮完成的是离线投影、检索对照、帮助度初评和问题定位；没有完成全库人工验收、正式知识库索引切换、线上Agent或下游风险判别准确率评估。

## 保存的材料

- [人工验收样例](人工验收样例.md)：11条诊断查询、实际片段、完整原文链接与留空验收栏。
- [逐查询对照](逐查询对照.md)、[全部查询与条件](查询清单.md)、[实验设计](实验设计.md)。
- [主指标JSON](指标/metrics.json)、[每题排名与评分](指标/per_query_metrics.jsonl)、[独立复标记录](独立复标记录.md)。
- [原始检索结果](retrieval_results.jsonl)、[冻结评分](指标/validated_judgments.jsonl)、[运行与复现说明](运行与复现说明.md)。
- [结果完整性](运行完整性检查.json)、[重复诊断](单位重复诊断.json)、[Q032候选分布](Q032拥挤诊断.json)。

各文件的SHA-256和最终验证见“交付完整性.json”；模型/向量/源材料的大文件缓存留在本工作区，不混入人工验收文本。
'''
    write('实验报告.md', report)
    print(json.dumps({'status':'complete','queries':len(queries),'results':len(results),
                      'paired_comparisons':pairs, 'independent_pairs':len(independent),
                      'independent_contexts':agreement['contexts'], 'source_exports':len(exported)},ensure_ascii=False))


def sha_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


if __name__ == '__main__':
    main()
