import importlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

WORK=Path(__file__).resolve().parents[1]

class ApiRunnerTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('api_runner'),'new scoped runner not implemented')
        return importlib.import_module('api_runner')
    def test_unknown_charge_keeps_full_reservation_and_cap_survives_restart(self):
        m=self.module()
        with tempfile.TemporaryDirectory(dir=WORK) as d:
            p=Path(d)/'ledger.jsonl';l=m.Ledger(p,.1);rid=l.reserve('phase','P',.06);l.settle(rid,None)
            self.assertAlmostEqual(l.booked(),.06)
            l2=m.Ledger(p,.1)
            with self.assertRaises(ValueError):l2.reserve('other','Q',.05)
            self.assertAlmostEqual(l2.booked(),.06)
    def test_actual_usage_releases_unused_reservation_without_double_settlement(self):
        m=self.module()
        with tempfile.TemporaryDirectory(dir=WORK) as d:
            l=m.Ledger(Path(d)/'ledger.jsonl',.1);rid=l.reserve('a','P',.08);l.settle(rid,.01)
            self.assertAlmostEqual(l.booked(),.01)
            with self.assertRaises(ValueError):l.settle(rid,0)
            l.reserve('b','Q',.08);self.assertAlmostEqual(l.booked(),.09)
    def test_key_gate_requires_exact_new_scope_plan_and_explicit_budget(self):
        m=self.module();auth=dict(authorized=True,scope='wrong',model='deepseek-flash',hard_cap_usd=2,human_authorization_reference='user said yes',request_plan_sha256='h')
        with self.assertRaises(ValueError):m.validate_authorization(auth,{'scope':'right','proposed_hard_cap_usd':2},'h')
        auth['scope']='right';self.assertTrue(m.validate_authorization(auth,{'scope':'right','proposed_hard_cap_usd':2},'h'))
        with self.assertRaises(ValueError):m.validate_authorization(auth,{'scope':'right','proposed_hard_cap_usd':2},'changed')
    def test_usage_bound_validates_counts_and_uses_pinned_peak_prices(self):
        m=self.module();self.assertAlmostEqual(m.usage_bound(dict(prompt_tokens=1000,completion_tokens=100,prompt_cache_hit_tokens=200)),(.3*800+.006*200+1.2*100)/1e6)
        for u in [dict(prompt_tokens=True,completion_tokens=1),dict(prompt_tokens=1,completion_tokens=1,prompt_cache_hit_tokens=2)]:
            with self.assertRaises(ValueError):m.usage_bound(u)
    def test_incomplete_phase_checkpoint_can_be_resumed_without_overwriting_history(self):
        m=self.module()
        with tempfile.TemporaryDirectory(dir=WORK) as d:
            folder=Path(d);m.save_phase(folder,[{'pair_id':'A'}],dict(complete=False,accepted=1),1)
            self.assertFalse((folder/'accepted.jsonl').exists())
            m.save_phase(folder,[{'pair_id':'A'},{'pair_id':'B'}],dict(complete=True,accepted=2),2)
            self.assertTrue((folder/'accepted.jsonl').exists());self.assertTrue((folder/'completion.json').exists())
            self.assertTrue((folder/'checkpoint_000001.json').exists())
    def test_terminal_invalid_judgment_has_a_completion_but_is_not_success(self):
        m=self.module()
        with tempfile.TemporaryDirectory(dir=WORK) as d:
            p=Path(d);m.save_phase(p,[],dict(complete=False,terminal=True,accepted=0,missing=['P']),3)
            self.assertTrue((p/'completion.json').exists());self.assertEqual((p/'accepted.jsonl').read_text(encoding='utf-8'),'')
    def test_nonobject_http200_and_nullable_usage_details_are_safe(self):
        m=self.module()
        with self.assertRaises(ValueError):m.decode_response('[]')
        self.assertIsInstance(m.decode_response('{"model":"deepseek-flash"}'),dict)
        self.assertAlmostEqual(m.usage_bound(dict(prompt_tokens=10,completion_tokens=1,prompt_cache_hit_tokens=1,prompt_tokens_details=None)),(.3*9+.006+1.2)/1e6)
        self.assertAlmostEqual(m.usage_bound(dict(prompt_tokens=10,completion_tokens=1,prompt_tokens_details=None)),(.3*10+1.2)/1e6)

if __name__=='__main__':unittest.main()
