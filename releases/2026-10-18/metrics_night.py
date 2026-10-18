"""Small deterministic source-file metrics; no unjudged = negative shortcut."""
import math


def metrics(ranking, grades, ks=(1,5,10,20)):
    if len(ranking)!=len(set(ranking)):raise ValueError('duplicate source file')
    if any(fid not in grades for fid in ranking[:max(20,max(ks))]):raise ValueError('unjudged evaluated document')
    direct=[i+1 for i,fid in enumerate(ranking[:20]) if grades[fid]==3]
    result={'Top1':int(bool(ranking) and grades[ranking[0]]==3),'MRR@20':1/direct[0] if direct else 0.,'pool_size':len(grades),'pool_direct':sum(g==3 for g in grades.values())}
    ideal=sorted(grades.values(),reverse=True)
    for k in ks:
        relevant=sum(grades[fid]==3 for fid in ranking[:k])
        dcg=sum((2**grades[fid]-1)/math.log2(i+2) for i,fid in enumerate(ranking[:k]))
        idcg=sum((2**g-1)/math.log2(i+2) for i,g in enumerate(ideal[:k]))
        result.update({f'P@{k}':relevant/k,f'Success@{k}':int(relevant>0),f'pool_NDCG@{k}':dcg/idcg if idcg else None})
    return result
