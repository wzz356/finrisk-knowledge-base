import copy
import tempfile
import unittest
from pathlib import Path
import demo


class ParentBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.query = Path(self.temp.name) / "query.jsonl"
        self.result = Path(self.temp.name) / "result.jsonl"
        self.query.write_text("query", encoding="utf-8")
        self.result.write_text("result", encoding="utf-8")
        self.log = {"status": "complete", "queries_sha256": demo.sha_file(self.query),
                    "output_sha256": demo.sha_file(self.result), "parameters": {"arms": ["rrf_rerank"]},
                    "rrf": {"k": 60, "ranks_start": 1, "equal_weights": True, "route_top_k": 100,
                            "union_max": 200, "rerank_top_k": 100}}

    def test_valid_bound_parent(self):
        demo.check_parent_run(self.log, self.query, self.result)

    def test_tampered_output_binding_rejected(self):
        broken = copy.deepcopy(self.log)
        broken["output_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            demo.check_parent_run(broken, self.query, self.result)

    def test_changed_fusion_parameters_rejected(self):
        broken = copy.deepcopy(self.log)
        broken["rrf"].update(k=999, route_top_k=1, rerank_top_k=1)
        with self.assertRaises(ValueError):
            demo.check_parent_run(broken, self.query, self.result)


if __name__ == "__main__":
    unittest.main()
