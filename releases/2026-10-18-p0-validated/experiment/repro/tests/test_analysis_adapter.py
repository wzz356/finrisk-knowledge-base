import unittest
from analysis_adapter import normalize_prediction,group_bootstrap

class AdapterTests(unittest.TestCase):
    def job(self):
        return {'pair_id':'J','data':{'current_text':'本人签署','case_unit_ids':['U'],'article_ids':['A']}}
    def test_missing_remains_failure_with_real_displayed_inputs(self):
        p=normalize_prediction(self.job(),None,'Q','old')
        self.assertFalse(p['valid']);self.assertEqual(p['displayed_case_ids'],['U'])
        self.assertEqual(p['current_text'],'本人签署')
    def test_model_fields_cannot_override_scoring_identity_or_displays(self):
        r={'parsed':{'state':'risk','mechanism_ids':['M'],'predicates':{'p':{'status':'met','quote':'本人'}},'case_unit_ids':['U'],'legal_article_ids':['A'],'query_id':'FAKE','arm':'new','displayed_article_ids':['FAKE']}}
        p=normalize_prediction(self.job(),r,'Q','old')
        self.assertTrue(p['valid']);self.assertEqual((p['query_id'],p['arm']),('Q','old'))
        self.assertEqual(p['displayed_article_ids'],['A'])
    def test_group_bootstrap_is_seeded_paired_and_retains_group_members(self):
        points=[{'group_id':'a','old_correct':False,'new_correct':True},{'group_id':'a','old_correct':False,'new_correct':True},{'group_id':'b','old_correct':False,'new_correct':True}]
        a=group_bootstrap(points,iterations=100,seed=1)
        self.assertEqual(a,group_bootstrap(points,iterations=100,seed=1))
        self.assertEqual((a['point_delta'],a['lower'],a['upper']),(1.,1.,1.))
        self.assertEqual(a['group_count'],2)
    def test_empty_bootstrap_is_undefined(self):
        self.assertIsNone(group_bootstrap([])['point_delta'])
    def test_malformed_prediction_cannot_count_as_correct_in_bootstrap(self):
        r={'parsed':{'state':'risk','mechanism_ids':None,'predicates':{}}}
        p=normalize_prediction(self.job(),r,'Q','old')
        self.assertFalse(p['valid']);self.assertTrue(p['validation_errors'])

if __name__=='__main__':unittest.main()
