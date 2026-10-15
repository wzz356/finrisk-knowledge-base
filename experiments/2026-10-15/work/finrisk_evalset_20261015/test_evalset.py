import unittest
from labels import validate_decisions
from scoring import direct_score
from retrieval_case_ids import retrieval_case_ids

CORPUS=[{'file_id':'F1','text':'原文明确赠送购物卡','text_sha256':'unused'},
 {'file_id':'F2','text':'原文明确虚列会议费','text_sha256':'unused'}]
QUERIES=[{'query_id':'Q1'},{'query_id':'Q2'}]
def decisions():return [
 {'file_id':'F1','grades':[3,0],'document_mechanism_summary':'购险赠礼','all20_queries_reviewed':True,'human_approved':False,
  'evidence':{'Q1':{'source_quote':'赠送购物卡','reason':'合同外赠礼','limitation':'无具体金额'}}},
 {'file_id':'F2','grades':[2,3],'document_mechanism_summary':'虚列会议费用','all20_queries_reviewed':True,'human_approved':False,
  'evidence':{'Q1':{'source_quote':'虚列会议费','reason':'仅资金用途相邻','limitation':'没有客户赠礼'},
              'Q2':{'source_quote':'虚列会议费','reason':'同一虚列机制','limitation':'用途未载'}}}]

class DatasetTests(unittest.TestCase):
 def test_raw_source_unit_keeps_existing_fallback_identity(self):
  self.assertEqual(retrieval_case_ids({'case_ids':[],'case_id':'F1:SOURCE'}),('F1:SOURCE',))
 def test_missing_document_not_defaulted_to_zero(self):
  with self.assertRaises(ValueError):validate_decisions(decisions()[:1],CORPUS,QUERIES)
 def test_invented_source_quote_rejected(self):
  d=decisions();d[0]['evidence']['Q1']['source_quote']='原文不存在的礼品'
  with self.assertRaises(ValueError):validate_decisions(d,CORPUS,QUERIES)
 def test_partial_help_does_not_count_as_direct(self):
  s=direct_score(['F2','F1'],{'F1':3,'F2':2})
  self.assertFalse(s['top1_hit']);self.assertEqual(s['reciprocal_rank']['value'],.5)
  self.assertEqual(s['positive_reference_count'],1)
 def test_unjudged_file_not_silently_scored_zero(self):
  with self.assertRaises(ValueError):direct_score(['F3','F1'],{'F1':3,'F2':0})
if __name__=='__main__':unittest.main()
