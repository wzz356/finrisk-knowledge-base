"""封闭测试集四指标评分。只依赖Python标准库，无模型/API依赖。"""
import argparse,json
from pathlib import Path
from evaluator_metrics import score,aggregate

def rows(p):
 return [json.loads(line) for line in Path(p).read_text(encoding="utf-8-sig").splitlines() if line.strip()]

def evaluate(dataset,rankings):
 dataset=Path(dataset);queries=rows(dataset/"queries.jsonl");corpus=rows(dataset/"corpus.jsonl");qrels=rows(dataset/"qrels.jsonl")
 qids={q["query_id"] for q in queries};fids={d["file_id"] for d in corpus}
 if not qids or not fids or len(qids)!=len(queries) or len(fids)!=len(corpus):raise ValueError("查询或语料ID重复/为空")
 expected={(q,f) for q in qids for f in fids};actual={(r["query_id"],r["file_id"]) for r in qrels}
 if len(actual)!=len(qrels) or actual!=expected:raise ValueError("参考集不是完整问题×封闭语料矩阵，不能计算穷尽Recall")
 if any(type(r["grade"]) is not int or r["grade"] not in [0,1,2,3] for r in qrels):raise ValueError("参考等级非法")
 if len(rankings)!=len(qids) or {r["query_id"] for r in rankings}!=qids:raise ValueError("排名必须逐题精确覆盖，不得漏题或重复")
 per=[];graded=[]
 for r in rankings:
  ids=r.get("file_ids")
  if not isinstance(ids,list) or len(ids)!=len(set(ids)) or any(f not in fids for f in ids):raise ValueError("排名必须是不重复的封闭库file_ids，库外文书不能默认0")
  gg={g["file_id"]:g["grade"] for g in qrels if g["query_id"]==r["query_id"]}
  direct={f:2 if g==3 else 0 for f,g in gg.items()}
  levels={f:2 if g==3 else 1 if g==2 else 0 for f,g in gg.items()}
  per.append({"query_id":r["query_id"],**score(ids,direct)})
  graded.append({"query_id":r["query_id"],**score(ids,levels)})
 return {"scope":"closed_corpus","documents":len(fids),"queries":len(qids),
  "primary_relevant":"grade=3 only","primary_summary":aggregate(per),"primary_per_query":per,
  "auxiliary_graded_summary":aggregate(graded),"auxiliary_graded_per_query":graded,
  "auxiliary_mapping":"3->effective2;2->effective1;1/0->0;graded NDCG only supplementary",
  "zero_direct_positive_queries":[r["query_id"] for r in per if r["positive_reference_count"]==0]}

if __name__=="__main__":
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--dataset",type=Path,default=Path(__file__).resolve().parent)
 p.add_argument("--rankings",type=Path,required=True,help="JSONL，每行query_id和按名次排序的file_ids")
 p.add_argument("--output",type=Path,required=True)
 a=p.parse_args();result=evaluate(a.dataset,rows(a.rankings))
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open("x",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,indent=2)
 print(json.dumps({"status":"scored","queries":result["queries"],"scope":result["scope"],"output":str(a.output)},ensure_ascii=False))
