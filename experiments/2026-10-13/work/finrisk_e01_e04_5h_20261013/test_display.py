"""Display-only controls must preserve every model input, score and rank."""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
E = None
if (HERE / "display_experiment.py").exists():
    spec = importlib.util.spec_from_file_location("display_tested", HERE / "display_experiment.py")
    E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)


class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(E, "display control implementation missing")

    def test_guard_rejects_score_or_index_or_rank_change(self):
        old = {"file_id": "F", "unit_id": "U", "rank": 1, "score": .5, "indexed_text": "旧输入"}
        for key, value in (("score", .6), ("indexed_text", "新输入"), ("rank", 2)):
            changed = dict(old, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError): E.check_model_hit(old, changed)

    def test_display_metadata_keeps_original_model_input(self):
        old = {"file_id": "F", "unit_id": "U", "rank": 1, "score": .5, "indexed_text": "旧输入"}
        expanded = dict(old, scope_profile="5h-scoped-v1", indexed_text="显示范围", representation_id="new", indexed_source_text="范围", indexed_source_spans=[{"start": 1, "end": 3}], text="源显示")
        result = E.restore_model_fields(old, expanded)
        self.assertEqual(result["indexed_text"], old["indexed_text"])
        self.assertEqual(result["display_scoped_index_text"], "显示范围")
        self.assertNotIn("representation_id", result)
        self.assertNotIn("indexed_source_text", result)
        self.assertEqual(result["text"], "源显示")


if __name__ == "__main__":
    unittest.main()
