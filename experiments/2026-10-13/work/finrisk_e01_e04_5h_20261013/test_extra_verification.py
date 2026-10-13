"""Cache bookkeeping differences must not mask altered source/context data."""
import copy
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("extra_tested", HERE / "verify_extra.py")
V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)


class ExtraVerificationTests(unittest.TestCase):
    def fixture(self):
        fresh = {"J1": {"full_source_text": "甲原文", "contexts": [{"context_id": "C1", "text": "实际片段"}],
                        "file_judgment_from_cache": False, "needs_file_judgment": True}}
        saved = copy.deepcopy(fresh)
        saved["J1"].update(file_judgment_from_cache=True, needs_file_judgment=False)
        return fresh, saved

    def test_only_verified_reuse_bookkeeping_can_differ(self):
        fn = getattr(V, "verify_reused_pool", None)
        self.assertTrue(callable(fn), "verified reuse comparison not implemented")
        fresh, saved = self.fixture()
        fn(fresh, saved)
        self.assertFalse(fresh["J1"]["file_judgment_from_cache"])

    def test_source_or_display_mutation_still_fails(self):
        fn = getattr(V, "verify_reused_pool", None)
        self.assertTrue(callable(fn), "verified reuse comparison not implemented")
        for mutation in ("source", "context"):
            fresh, saved = self.fixture()
            if mutation == "source": saved["J1"]["full_source_text"] = "改原文"
            else: saved["J1"]["contexts"][0]["text"] = "改展示"
            with self.assertRaises(ValueError): fn(fresh, saved)


if __name__ == "__main__":
    unittest.main()
