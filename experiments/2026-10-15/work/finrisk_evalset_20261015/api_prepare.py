"""复用原请求器，仅将固定1200总数改为本轮去重后的实际配对数。"""
from common import *
freeze_check();freeze_check('candidate_freeze.json')
prior=ROOT/'work/finrisk_deepseek_rerank_20261014'
original=(prior/'run.py').read_text(encoding='utf-8')
prefix,body=original.split('def run(pilot):',1)
prefix=prefix.split('def prepare():')[0]
body=body.split("if __name__=='__main__':")[0]
assert body.count('1200')==4
engine=prefix+'\nEXPECTED_PAIRS=0\n\ndef run(pilot):'+body.replace('1200','EXPECTED_PAIRS')
(WORK/'request_engine.py').write_text(engine,encoding='utf-8')
(OUT/'重排规则.md').write_bytes((ROOT/'outputs/FinRisk_DeepSeek重排对照_20261014/重排规则.md').read_bytes())
packets=rows(OUT/'score_inputs.jsonl');maps=rows(OUT/'candidate_map.jsonl')
assert len(maps)==4000 and len({p['pair_id'] for p in packets})==len(packets)
assert {m['pair_id'] for m in maps}=={p['pair_id'] for p in packets}
save('api_design.json',{'model':'deepseek-flash','thinking':'disabled','temperature':0,'max_tokens':512,
 'endpoint':'https://api.deepseek.com/chat/completions','concurrency':8,'budget_peak_bound_usd':2,
 'unique_pairs':len(packets),'mapped_pairs':4000,'deduplication':'identical query_id/unit_id/text hash across two scopes',
 'rules_unchanged':True,'original_adapter_unchanged':True,'only_engine_fixed_total_changed':True,
 'labels_answers_not_sent':True,'production_switched':False})
save('export_authorization.json',{'explicit_authorized':True,'persistent_prior_user_request':'好的，还是用deepseek，我批准你使用。用官方数据集跑一次看看结果',
 'current_user_request':'依据现有案例和知识库，构建一份可用的测试集，用于计算指标，规模不用太大。五小时内完成',
 'scope_user_selected':'封闭小测试集＋全库补充检索（推荐）','scope':'20新业务输入及原已授权知识库的实际候选索引片段，不发送任何参考标注',
 'endpoint':'https://api.deepseek.com/chat/completions','budget_peak_bound_usd':2})
save('api_freeze.json',{'utc':datetime.now(timezone.utc).isoformat(),'before_API':True,
 'sha256':{str(p):sha(p) for p in [WORK/'api_prepare.py',WORK/'api_run.py',WORK/'request_engine.py',prior/'api_adapter.py',prior/'run.py',
  ROOT/'work/finrisk_official_only_20261015/citation.py',OUT/'score_inputs.jsonl',OUT/'candidate_map.jsonl',
  OUT/'api_design.json',OUT/'export_authorization.json',OUT/'重排规则.md']}})
print(json.dumps({'status':'API_prepared','unique_pairs':len(packets),'reuse_saved_pairs':4000-len(packets),'budget_peak_bound_usd':2},ensure_ascii=False))
