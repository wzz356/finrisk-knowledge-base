"""主指标统一仅3分，分级NDCG另报；未知文书拒绝自动补0。"""
from common import ROOT,module
base=module(ROOT/'work/finrisk_four_metric_evaluation_20261014/scoring.py','benchmark_base_scoring')
def direct_score(files,grades):
 if any(type(g) is not int or g not in [0,1,2,3] for g in grades.values()):raise ValueError('非法等级')
 return base.score(files,{f:2 if g==3 else 0 for f,g in grades.items()})
def graded_score(files,grades):return base.score(files,{f:2 if g==3 else 1 if g==2 else 0 for f,g in grades.items()})
