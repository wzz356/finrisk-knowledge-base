import importlib.util
import os
import unittest
from pathlib import Path
from runtime_common import read,sha

WORK=Path(__file__).resolve().parents[1]
OUT=Path(os.environ['FINRISK_RUNTIME_TEST_ROOT']).resolve() if os.environ.get('FINRISK_RUNTIME_TEST_ROOT') else WORK.parents[1]/'outputs/FinRisk_知识库P0修复_20261018'

class EvidenceRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec('evidence_runtime') is None:raise AssertionError('evidence runtime not implemented')
        from evidence_runtime import EvidenceRuntime
        cls.runtime=EvidenceRuntime(OUT,sha(OUT/'contracts/runtime_manifest.json'))
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'runtime'):cls.runtime.close()
    def test_full_source_unavailable_in_old_snapshot_is_readable(self):
        r=self.runtime
        old=set(read(OUT/'contracts/legacy_snapshot_unit_ids.json')['unit_ids'])
        self.assertEqual(len(old),732)
        uid=next(u for u in r.reader.units if u not in old and r.reader.units[u]['file_id']=='F000001')
        got=r.read_case(uid)
        self.assertNotIn(uid,old)
        self.assertEqual(got['file_id'],'F000001');self.assertTrue(got['segments'])
        self.assertEqual(len(r.reader.units),110878);self.assertEqual(len(r.reader.sources),9639)
    def test_investment_linked_excludes_universal_specific_context(self):
        text='本公司为保险公司，此产品是投资连结型保险。合同订立后开展回访。'
        scope={}
        for axis,value,q in [('actor','insurer','保险公司'),('product','investment_linked','投资连结型保险'),('stage','post_sale_review','合同订立后')]:
            scope[axis]=dict(value=value,origin='current_input',quote=q,start=text.index(q),end=text.index(q)+len(q))
        result=self.runtime.get_evidence_bundle(['M02'],[],current_text=text,scope_facts=scope)
        law=result['legal_assembly']
        self.assertIn('L005-A0016',law['scope_excluded_article_ids'])
        self.assertNotIn('L005-A0016',law['included_article_ids'])
        self.assertIn('L002-A0035',law['included_article_ids'])
        self.assertIn('合理简化回访要求',law['text'])
        self.assertFalse(result['current_business_facts_verified'])
    def test_agent_and_insurer_scope_and_unknown(self):
        text='我们是保险专业代理机构，承诺合同外返还现金。';q='保险专业代理机构'
        scope={'actor':dict(value='insurance_agent',origin='current_input',quote=q,start=text.index(q),end=text.index(q)+len(q))}
        result=self.runtime.get_evidence_bundle(['M04'],[],current_text=text,scope_facts=scope)
        self.assertIn('L001-A0116',result['legal_assembly']['scope_excluded_article_ids'])
        self.assertIn('L001-A0131',result['legal_assembly']['included_article_ids'])
        unknown=self.runtime.get_evidence_bundle(['M04'],[])
        self.assertEqual(unknown['legal_assembly']['scope_excluded_article_ids'],[])
    def test_multirisk_keeps_more_than_two_and_read_is_not_checked(self):
        text='万能保险保证收益，合同外赠送现金，回访由销售冒充客户回答，签名由销售替客户确认。'
        report=self.runtime.get_input_coverage(text,read_ids=['M02'])
        self.assertGreaterEqual(len(report['candidate_mechanism_ids']),4)
        self.assertIn('M02',report['unchecked_candidate_ids'])
        self.assertFalse(report['whole_input_risk_free_supported'])
    def test_budget_omits_whole_items_and_bad_inputs_refused(self):
        uid=next(iter(self.runtime.reader.units))
        got=self.runtime.get_evidence_bundle(['M02'],[uid],budget_chars=2)
        self.assertLessEqual(len(got['case_text'])+len(got['legal_assembly']['text']),2)
        self.assertEqual(got['case_records'],[]);self.assertTrue(got['omitted_case_unit_ids'])
        self.assertTrue(got['legal_assembly']['next_read_article_ids'])
        for kwargs in [dict(budget_chars=True),dict(budget_chars=8001),dict(case_budget=7000,law_budget=7000)]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.runtime.get_evidence_bundle(['M02'],[],**kwargs)
        with self.assertRaises(ValueError):self.runtime.read_case('invented-unit')
        with self.assertRaises(ValueError):self.runtime.get_evidence_bundle(['M99'],[])

    def test_live_worker_rejects_bad_parameter_and_keeps_serving(self):
        from runtime_cli import handle_line,dispatch
        bad=handle_line(self.runtime,'{"operation":"read_case","arguments":{"unit_id":[]}}')
        self.assertFalse(bad['ok'])
        got=dispatch(self.runtime,read(OUT/'contracts/example_request.json'))
        self.assertTrue(got['case_records']);self.assertEqual(got['law_and_guide_text'],got['legal_assembly']['text'])
        self.assertEqual(self.runtime.coverage('M02'),self.runtime.get_coverage('M02'))
    def test_wrong_runtime_pin_refused_before_index_start(self):
        from evidence_runtime import EvidenceRuntime
        with self.assertRaises(ValueError):EvidenceRuntime(OUT,'0'*64)

if __name__=='__main__':unittest.main()
