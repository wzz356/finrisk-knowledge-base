"""输入与标注任务在任何检索前冻结；分层原文候选＋固定随机干扰。"""
import random,re
from common import *
docs=rows(SOURCE);dm={d['official_file_id']:d for d in docs};assert len(dm)==9639
explore=read(OUT/'source_exploration.json')
exclude={r['file_id'] for r in rows(ROOT/'outputs/FinRisk_纯官方案例库DeepSeek试跑_20261015/official_reference_cases.jsonl')}
seed_ids=['F001265','F001928','F002237','F002241','F000822','F000819','F001354','F000495','F000301','F001926','F008984','F001965','F001803','F001748','F001948','F000699']
selected={fid:{'stratum':'source_grounded_seed'} for fid in seed_ids}
for key,entry in explore.items():
 for c in entry['candidates']:
  if c['file_id'] not in selected:selected[c['file_id']]={'stratum':'mechanism_neighbor','group':key}
rng=random.Random(2026101503)
neighbors=[d for d in docs if d['official_file_id'] not in selected and d['official_file_id'] not in exclude and len(d['full_text'])<=4500 and any(w in d['full_text'] for w in ['合同约定以外','欺骗投保人','回访','保险责任','风险提示','代理资格'])]
rng.shuffle(neighbors)
while len(selected)<75:
 d=neighbors.pop();selected[d['official_file_id']]={'stratum':'risk_adjacent_distractor'}
other=[d for d in docs if d['official_file_id'] not in selected and d['official_file_id'] not in exclude and 100<=len(d['full_text'])<=4500]
rng.shuffle(other)
while len(selected)<100:
 d=other.pop();selected[d['official_file_id']]={'stratum':'fixed_random_distractor'}
assert len(selected)==100 and not set(selected)&exclude
corpus=[]
for fid in sorted(selected):
 d=dm[fid];assert tsha(d['full_text'])==d['text_sha256']
 corpus.append({'file_id':fid,'text':d['full_text'],'text_sha256':d['text_sha256'],
  'text_id':d['text_id'],'source_id':d['source_id'],'origin':str(SOURCE),'source_quality_flags':d.get('text_quality_flags',[])})
spec=read(WORK/'query_spec.json');assert len(spec)==len({q['query_id'] for q in spec})==20
queries=[{'query_id':q['query_id'],'text':q['text'],'text_sha256':tsha(q['text'])} for q in spec]
prior=[q['text'] for q in rows(ROOT/'outputs/FinRisk_纯官方案例库DeepSeek试跑_20261015/queries_frozen.jsonl')]
assert not {q['text'] for q in queries}&set(prior)
assert all(not re.search(r'F\d{6}|C\d{3}|KBT\d{3}',q['text']) for q in queries)
save('corpus.jsonl',corpus,True);save('queries.jsonl',queries,True);save('query_specs.jsonl',spec,True)
save('selection_audit.json',{'seed':2026101503,'before_retrieval':True,'selected':selected,
 'excluded_previous12_reference_files':sorted(exclude),'cases':100,'queries':20,
 'source_grounded_synthetic':True,'not_all27_tags_covered':True})
rules='''# 全文相关性标注规则

目标：输入一段业务文字，召回处罚案例帮助判断风险或明确合规边界。以整份源文书F编号为单位；一份文书有多主体/行为时，只要其中一个事实完整支撑当前关注机制可相关，但必须在引文/理由说明责任角色。

每份文书逐一判断全部20题，给0/1/2/3，不允许因没评就填0。程序只能序列化人工（本会话模型）已明确作出的矩阵，不能关键词自动分配语义分数。标注者只看全文、题目及关注机制，不看种子角色、检索排名或其他标注。

- 3：同一关键风险机制或操作在事实部分明示，能够直接支撑当前判断/对照边界；不要求金额、机构、产品完全相同。必须有原文引文、机制对应理由、适用限制/主体责任说明。明确的合同外利益、虚构限售、扩大保险责任等机制可以是简短事实；仅泛称欺骗/销售误导不够。
- 2：仅部分、宽泛相邻帮助，关键操作/条件不明或对应不完整；不能据此直接支持当前具体机制。保留原文引文和缺失点。
- 1：只有主题/渠道/产品相同，事实机制不同。
- 0：无关、只在法律依据/复议程序出现词语，或不能提供当前边界帮助。

boundary题当前未必违规：同机制违法案若明示与当下合规操作的关键条件差异，能够直接说明边界，可以为3；理由必须写明对照差异，不能把当前输入强行判违法。

不从监管通用法条、摘要标签、罚款账户等推断销售事实；原文过于概括不能补充未披露细节。对泛称回访违规、财务不真实、销售误导等，需要核查它实际是否包含题目所关注的具体操作。对利益的对象、责任人员/机构、同业/本公司、真实停售/虚构停售等进行区分。

输出每个file_id的20个明确等级，并对每个>=2配对保存连续原文source_quote、reason、limitation。对0/1给该文书实际机制摘要用于说明负例判断。任何评分human_approved=false，来源model_source_review。不得读query seed/检索结果或其他分片。

主四指标：只用grade=3作为相关，Recall分母为100份封闭语料的全部3分文书；MRR/Top1同一门槛，主NDCG二值。附分级NDCG用3→有效等级2、2→1、1/0→0。库外结果不得自动记0，必须补标或只报告已知参考覆盖。
'''
(OUT/'标注规则.md').write_text(rules,encoding='utf-8')
shuffle=corpus.copy();rng.shuffle(shuffle)
for i in range(3):
 shard=shuffle[i::3]
 save(f'annotation_inputs/part_{i+1}.jsonl',shard,True)
save('input_freeze.json',{'utc':datetime.now(timezone.utc).isoformat(),'before_any_retrieval':True,
 'sha256':{str(p):sha(p) for p in [SOURCE,INDEX,V2/'indexes/all9639_final/manifest.json',WORK/'common.py',WORK/'query_spec.json',WORK/'build_inputs.py',
  OUT/'corpus.jsonl',OUT/'queries.jsonl',OUT/'query_specs.jsonl',OUT/'selection_audit.json',OUT/'标注规则.md',
  *[OUT/f'annotation_inputs/part_{i}.jsonl' for i in [1,2,3]]]}})
print(json.dumps({'status':'frozen','source_files':100,'queries':20,'source_chars':sum(len(d['text']) for d in corpus),
 'shards':[len(shuffle[i::3]) for i in range(3)],'boundary_queries':sum(q['input_type']=='boundary' for q in spec)},ensure_ascii=False))
for fid in seed_ids:print(json.dumps({'seed_file':fid,'full_text':dm[fid]['full_text']},ensure_ascii=False))
if __name__=='__main__':pass
