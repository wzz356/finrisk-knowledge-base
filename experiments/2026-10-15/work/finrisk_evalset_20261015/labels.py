"""拒绝缺评、假引文和伪人审；显式展开完整语义判断矩阵。"""
def validate_decisions(decisions,corpus,queries):
 cm={d['file_id']:d for d in corpus};qids=[q['query_id'] for q in queries]
 if len(cm)!=len(corpus) or len(qids)!=len(set(qids)):raise ValueError('语料或查询ID重复')
 dm={d['file_id']:d for d in decisions}
 if len(dm)!=len(decisions) or set(dm)!=set(cm):raise ValueError('文书缺评或重复')
 flat=[]
 for fid,d in dm.items():
  gg=d.get('grades')
  if not isinstance(gg,list) or len(gg)!=len(qids) or any(type(g) is not int or g not in [0,1,2,3] for g in gg):raise ValueError('没有全部明确等级')
  if d.get('all20_queries_reviewed') is not True or d.get('human_approved') is not False:raise ValueError('未完整评阅或伪人审')
  summary=d.get('document_mechanism_summary')
  if not isinstance(summary,str) or not summary.strip():raise ValueError('缺文书事实摘要')
  ev=d.get('evidence',{})
  for qid,g in zip(qids,gg):
   item=ev.get(qid,{})
   if g>=2:
    if any(not isinstance(item.get(k),str) or not item[k].strip() for k in ['source_quote','reason','limitation']):raise ValueError('缺正例证据或限制')
    if item['source_quote'] not in cm[fid]['text']:raise ValueError('引文不在原文')
   flat.append({'query_id':qid,'file_id':fid,'grade':g,'source_quote':item.get('source_quote',''),
    'reason':item.get('reason','全文事实为：'+summary+'；与本题关注机制未形成直接支撑。'),
    'limitation':item.get('limitation','0/1为该文书全文比较判断，不代表其他文书不存在证据。'),
    'document_mechanism_summary':summary,'source_text_sha256':cm[fid]['text_sha256'],
    'origin':'model_source_review','reviewer_id':d.get('reviewer_id','unspecified'),
    'human_approved':False,'explicit_matrix_decision':True})
 return sorted(flat,key=lambda x:(x['query_id'],x['file_id']))
