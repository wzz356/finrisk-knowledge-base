import copy
import unittest
try:
    from rebind_coverage import add_missing_bindings
except ImportError:
    add_missing_bindings=None

class CoverageBindings(unittest.TestCase):
    def test_add_exact_finding_without_changing_facts_or_other_rows(self):
        draft={'behaviors':[{'local_key':'b1','case_key':'c1','finding_quote':'机构虚列费用。'}],
               'cases':[{'local_key':'c1','party_name':'机构'}],
               'coverage':[{'quote':'其他背景。','classification':'context','case_keys':[],'behavior_keys':[]}]}
        base=copy.deepcopy(draft)
        self.assertIsNotNone(add_missing_bindings)
        updated,changes=add_missing_bindings(draft,'机构虚列费用。其他背景。')
        self.assertEqual(draft,base)
        self.assertEqual(updated['cases'],draft['cases']);self.assertEqual(updated['behaviors'],draft['behaviors'])
        self.assertEqual(updated['coverage'][0],draft['coverage'][0]);self.assertEqual(len(changes),1)
        self.assertEqual(updated['coverage'][1]['behavior_keys'],['b1'])
        again,changes2=add_missing_bindings(updated,'机构虚列费用。其他背景。')
        self.assertEqual(again,updated);self.assertEqual(changes2,[])

    def test_source_mismatch_is_blocked_and_shared_findings_keep_own_links(self):
        self.assertIsNotNone(add_missing_bindings)
        d={'behaviors':[{'local_key':'b1','case_key':'c1','finding_quote':'机构虚列费用。'},
                        {'local_key':'b2','case_key':'c2','finding_quote':'机构虚列费用。'}],
           'cases':[{'local_key':'c1'},{'local_key':'c2'}],'coverage':[]}
        with self.assertRaises(ValueError):add_missing_bindings(d,'另一件事')
        out,_=add_missing_bindings(d,'机构虚列费用。')
        self.assertEqual([x['behavior_keys'] for x in out['coverage']],[['b1'],['b2']])

if __name__=='__main__':unittest.main()
