import importlib
import importlib.util
import unittest

class CoverageTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('risk_coverage'),'coverage analyzer not implemented')
        return importlib.import_module('risk_coverage')

    def cards(self):
        return {f'M{i:02}':dict(mechanism_id=f'M{i:02}',adjacent_mechanism_ids=[]) for i in range(1,13)}

    def test_three_mechanisms_are_not_truncated_to_two(self):
        text='签名确认由销售替客户完成。回访电话我冒充客户接听。合同之外再给客户返还两千元。'
        got=self.module().analyze_coverage(text,self.cards(),read_ids=['M11','M02'])
        self.assertTrue({'M11','M02','M04'}<=set(got['candidate_mechanism_ids']))
        self.assertIn('M04',got['not_read_candidate_ids']);self.assertFalse(got['whole_input_risk_free_supported'])
        for span in got['trigger_spans']:self.assertEqual(text[span['start']:span['end']],span['text'])

    def test_reading_is_not_checking_and_caller_checks_are_unverified(self):
        text='这次回访由客户本人回答。';m=self.module();cards=self.cards()
        got=m.analyze_coverage(text,cards,read_ids=['M01','M02'])
        self.assertEqual(got['caller_reported_checked_ids'],[]);self.assertTrue(got['unchecked_candidate_ids'])
        got=m.analyze_coverage(text,cards,read_ids=['M01','M02'],checked_ids=['M01','M02'])
        self.assertFalse(got['current_input_facts_verified']);self.assertFalse(got['whole_input_risk_free_supported'])

    def test_negated_behavior_is_a_candidate_not_a_violation_verdict(self):
        got=self.module().analyze_coverage('不得冒充客户回访，不得替客户签名。',self.cards())
        self.assertIn('M02',got['candidate_mechanism_ids']);self.assertIn('M11',got['candidate_mechanism_ids'])
        self.assertFalse(got['risk_determined']);self.assertTrue(got['negation_not_resolved'])

    def test_no_trigger_is_explicitly_unmapped_not_safe(self):
        got=self.module().analyze_coverage('今天下雨，会议改到下午。',self.cards())
        self.assertEqual(got['coverage_status'],'unmapped')
        self.assertFalse(got['whole_input_risk_free_supported']);self.assertFalse(got['all_official_labels_covered'])

    def test_unknown_ids_and_invalid_input_refused(self):
        m=self.module()
        for text,readids in [('',[]),('回访',['M99']),('回访',[{}])]:
            with self.assertRaises(ValueError):m.analyze_coverage(text,self.cards(),read_ids=readids)

if __name__=='__main__':unittest.main()
