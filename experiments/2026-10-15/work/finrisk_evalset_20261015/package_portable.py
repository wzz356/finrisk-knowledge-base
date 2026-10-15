"""可移植核心包；异目录解压后以实际CLI复算、核对哈希。"""
import zipfile,subprocess
from common import *
assert read(OUT/'final_verification.json')['status']=='passed'
names=['README.md','指标报告.md','人工验收样例.md','queries.jsonl','corpus.jsonl','query_specs.jsonl','qrels.jsonl',
 'qrels_direct.txt','qrels_graded_levels.txt','qrels_graded_gain.txt','closed_index_units.jsonl','标注规则.md','重排规则.md',
 'evaluator_metrics.py','evaluate.py','reference_summary.json','adjudication_log.jsonl','blind_review_summary.json',
 'closed_metrics_summary.json','closed_miss_diagnostics.json','full_known_reference_coverage.json','full_ND_actual_helpfulness.json',
 'supplement_qrels.jsonl','supplement_corpus.jsonl','supplement_annotation_summary.json','api_cost_audit.json',
 'retrieval_config.json','retrieval_completion.json','core_verification.json','retrieval_verification.json','final_verification.json']
names +=[str(p.relative_to(OUT)).replace('\\','/') for p in sorted((OUT/'rankings').glob('*.jsonl'))]
names +=[str(p.relative_to(OUT)).replace('\\','/') for p in sorted((OUT/'metrics').glob('*.json'))]
assert len(names)==len(set(names)) and all((OUT/n).is_file() for n in names)
save('dataset_manifest.json',{'schema_version':1,'dataset':'FinRisk可用测试集v1','queries':20,'closed_documents':100,'closed_qrels':2000,
 'primary_relevance':'grade3 only','human_approved':False,'full_global_recall_available':False,
 'files':[{'path':n,'bytes':(OUT/n).stat().st_size,'sha256':sha(OUT/n)} for n in names]})
zip_path=OUT/'FinRisk_测试集_v1_可移植包.zip'
with zipfile.ZipFile(zip_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for n in names+['dataset_manifest.json']:z.write(OUT/n,arcname=n)
destination=WORK/'portable_verification';assert not destination.exists();destination.mkdir()
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None and len(z.namelist())==len(names)+1
 assert all(not n.startswith(('/', '\\')) and '..' not in Path(n).parts for n in z.namelist())
 z.extractall(destination)
manifest=read(destination/'dataset_manifest.json')
for f in manifest['files']:
 p=destination/f['path'];assert p.stat().st_size==f['bytes'] and sha(p)==f['sha256']
verified=[]
for stage in ['BM25','BGE','RRF','N0','ND']:
 result=subprocess.run([sys.executable,str(destination/'evaluate.py'),'--dataset',str(destination),'--rankings',str(destination/f'rankings/closed100_{stage}.jsonl'),'--output',str(destination/f'replay_{stage}.json')],cwd=destination,capture_output=True,text=True,encoding='utf-8')
 assert result.returncode==0,(stage,result.stderr)
 assert read(destination/f'replay_{stage}.json')==read(OUT/f'metrics/closed100_{stage}.json');verified.append(stage)
save('portable_verification.json',{'status':'passed','zip_path':str(zip_path),'zip_sha256':sha(zip_path),'zip_bytes':zip_path.stat().st_size,
 'packaged_files':len(names)+1,'all_member_hashes_verified':True,'separate_directory_real_CLI_stages':verified,
 'all_5_exact_metric_payloads_equal':True,'dependency':'Python standard library only','model_or_API_requests':0})
print(json.dumps(read(OUT/'portable_verification.json'),ensure_ascii=False))
