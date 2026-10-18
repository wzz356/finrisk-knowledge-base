import importlib
import importlib.util
import unittest

class ProtocolTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('protocol'),'protocol validators not implemented')
        return importlib.import_module('protocol')
    def test_reference_and_split_fields_cannot_enter_request(self):
        m=self.module();job=m.job('P1','scope',{'pair_id':'P1','current_text':'保险公司介绍万能型保险。'},m.SCOPE_SYSTEM,512)
        self.assertTrue(m.validate_job(job))
        import json
        for field in ['query_id','opaque_id','expected_state','split','arm','reference_grade']:
            bad={**job,'body':{**job['body'],'messages':[job['body']['messages'][0],dict(role='user',content=json.dumps({'nested':{field:'secret'}}))]}}
            with self.subTest(field=field),self.assertRaises(ValueError):m.validate_job(bad)
    def test_scope_requires_exact_current_quote_and_unknown_stays_unknown(self):
        m=self.module();j=m.job('P1','scope',{'pair_id':'P1','current_text':'保险公司介绍万能型保险。'},m.SCOPE_SYSTEM,512)
        value=dict(pair_id='P1',actor={'value':'insurer','quote':'保险公司','reason':'明示主体'},product={'value':'universal_life','quote':'万能型保险','reason':'明示产品'},stage={'value':'unknown','quote':'','reason':'环节未明'},human_approved=False)
        got=m.validate_result(j,value);self.assertEqual(got['scope_facts']['actor']['start'],0);self.assertEqual(got['scope_facts']['stage']['value'],'unknown')
        value['product']['quote']='不存在的产品'
        with self.assertRaises(ValueError):m.validate_result(j,value)
    def test_invalid_rerank_quote_is_retained_not_semantically_retried(self):
        m=self.module();j=m.job('P2','rerank',dict(pair_id='P2',query_text='回访',unit_text='有人冒充客户。'),m.expected_system('rerank'),384)
        r=m.validate_result(j,dict(pair_id='P2',score=90,level='specific_direct',source_quote='虚构原句',reason='对应',limitation='只按片段',human_approved=False))
        self.assertEqual(r['score'],90);self.assertFalse(r['quotation_valid'])
        self.assertEqual(m.validate_result(j,r),r)
    def test_judgment_checks_condition_ids_current_quotes_and_displayed_citations(self):
        m=self.module();data=dict(pair_id='P3',current_text='销售人员代签。',mechanism_ids=['M11'],predicate_ids=['M11.p'],required_by_mechanism={'M11':['M11.p']},case_unit_ids=['U'],article_ids=['A'])
        j=m.job('P3','judgment',data,m.JUDGMENT_SYSTEM,2048)
        value=dict(pair_id='P3',state='risk',mechanism_ids=['M11'],predicates={'M11.p':['met','代签']},case_unit_ids=['U'],legal_article_ids=['A'],reason='筛查风险',limitations=['仅所列机制'],human_approved=False)
        self.assertEqual(m.validate_result(j,value)['predicates']['M11.p']['status'],'met')
        for change in [dict(legal_article_ids=['B']),dict(predicates={'M11.p':['met','历史事实']}),dict(predicates={}),dict(predicates={'M11.p':['unknown','']})]:
            with self.subTest(change=change),self.assertRaises(ValueError):m.validate_result(j,{**value,**change})
    def test_kind_output_budget_system_and_json_format_are_fixed(self):
        m=self.module();j=m.job('P1','scope',{'pair_id':'P1','current_text':'保险公司。'},m.SCOPE_SYSTEM,512)
        for key,value in [('max_tokens',2048),('response_format',{'type':'text'}),('tools',[])]:
            with self.subTest(key=key),self.assertRaises(ValueError):m.validate_job({**j,'body':{**j['body'],key:value}})
        bad={**j,'body':{**j['body'],'messages':[dict(role='system',content='changed'),j['body']['messages'][1]]}}
        with self.assertRaises(ValueError):m.validate_job(bad)
    def test_nonfinite_json_is_rejected_before_record_serialization(self):
        m=self.module()
        for raw in ['{"x":NaN}','{"x":Infinity}','{"x":-Infinity}']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):m.strict_json(raw)

if __name__=='__main__':unittest.main()
