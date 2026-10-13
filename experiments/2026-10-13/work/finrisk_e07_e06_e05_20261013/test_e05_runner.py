"""Focused algorithm/guard tests; these are not GPU experiment results."""
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def runner():
    path = HERE / "e05_runner.py"
    assert path.exists(), "E05 runner has not been implemented"
    spec = importlib.util.spec_from_file_location("tested_e05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def node(nid="N", descendants=None, text="navigation", level=1):
    return dict(node_id=nid, text=text, level=level,
                descendant_unit_ids=["u1"] if descendants is None else descendants)


class E05Tests(unittest.TestCase):
    def test_spherical_seed_coverage_and_centroid_norm(self):
        e = runner()
        vectors = np.random.default_rng(8).normal(size=(21, 8)).astype("float32")
        a, centers, meta = e.spherical_kmeans(vectors, 4)
        b, _, _ = e.spherical_kmeans(vectors, 4)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(set(a), {0, 1, 2, 3})
        np.testing.assert_allclose(np.linalg.norm(centers, axis=1), 1, atol=1e-6)
        self.assertEqual(meta["seed"], 17)
        self.assertEqual(len(a), 21)

    def test_empty_cluster_repair_covers_identical_vectors(self):
        e = runner()
        labels, _, meta = e.spherical_kmeans(np.ones((6, 3)), 4)
        self.assertEqual(set(labels), {0, 1, 2, 3})
        self.assertGreater(meta["empty_cluster_repairs"], 0)

    def test_kmeans_rejects_invalid_vectors(self):
        e = runner()
        for value, k in [(np.zeros((2, 3)), 1), (np.ones((2, 3)), 3),
                         (np.array([[np.nan, 1]]), 1)]:
            with self.assertRaises(ValueError):
                e.spherical_kmeans(value, k)

    def test_node_whitelist_rejects_empty_unknown_duplicate(self):
        e = runner()
        for nodes in [[node(descendants=[])], [node(descendants=["u2"])],
                      [node(), node()], [node(descendants=["u1", "u1"])]]:
            with self.assertRaises(ValueError):
                e.validate_nodes(nodes, {"u1"})

    def test_leaf_source_binding_and_ambiguity_guard(self):
        e = runner()
        unit = dict(unit_id="u1", file_id="F1", source_sha256="source", text="short")
        leaf = dict(node("L", text="reviewed", level=0), unit_id="u1", file_id="F1",
                    source_sha256="source", segments=[dict(text="reviewed", span=dict(start=0, end=8))])
        approved = {"u1": dict(indexed_text="reviewed", segments=leaf["segments"])}
        e.validate_leaves([leaf], {"u1": unit}, approved, expected_count=1)
        bad = dict(leaf, source_sha256="different")
        with self.assertRaises(ValueError):
            e.validate_leaves([bad], {"u1": unit}, approved, expected_count=1)
        with self.assertRaises(ValueError):
            e.validate_leaves([leaf], {"u1": unit}, {"u1": dict(approved["u1"], scope_status="ambiguous_unchanged")}, expected_count=1)

    def test_reviewed_scope_preserves_old_short_index_ambiguity(self):
        e = runner()
        unit = dict(unit_id="u1", file_id="F1", source_sha256="source", text="short", evidence_ambiguous=True)
        leaf = dict(node("L", text="source-scoped", level=0), unit_id="u1", file_id="F1",
                    source_sha256="source", segments=[])
        approved = {"u1": dict(indexed_text="source-scoped", segments=[], scope_status="scoped")}
        self.assertEqual(e.validate_leaves([leaf], {"u1": unit}, approved, expected_count=1), {"u1"})

    def test_base_dense_keeps_original_row_ties_and_array(self):
        e = runner()
        units = [dict(unit_id=uid) for uid in ["z", "a", "b"]]
        scores = np.array([.9, .9, .2], dtype="float32")
        before = scores.copy()
        dense, hits, expansion = e.navigation_route(units, scores, [], np.array([]), set(), top_k=3)
        self.assertEqual([x["unit_id"] for x in dense], ["z", "a", "b"])
        self.assertEqual(hits, [])
        self.assertEqual(expansion, [])
        np.testing.assert_array_equal(scores, before)

    def test_navigation_top_k_competes_then_expands_and_deduplicates(self):
        e = runner()
        units = [dict(unit_id=x) for x in ["u3", "u2", "u1", "u4"]]
        scores = np.array([.8, .6, .2, .1])
        nodes = [node("N1", ["u2", "u1"]), node("N2", ["u1"])]
        route, hits, expansion = e.navigation_route(units, scores, nodes, np.array([.95, .9]), {"u1", "u2"}, top_k=3)
        self.assertEqual([x["unit_id"] for x in route], ["u1", "u2", "u3"])
        self.assertEqual([x["node_id"] for x in hits], ["N1", "N2"])
        self.assertEqual(route[0]["score"], .95)
        self.assertEqual(route[0]["score_origin"], "navigation_node_cosine_not_leaf_cosine")
        self.assertEqual([x["accepted"] for x in expansion], [True, True, False])
        self.assertEqual(expansion[2]["reason"], "already_emitted")

    def test_navigation_descendants_must_exist_in_full_population(self):
        e = runner()
        with self.assertRaises(ValueError):
            e.navigation_route([dict(unit_id="u3")], np.array([.8]), [node()], np.array([.9]), {"u1"}, top_k=1)

    def test_cluster_input_layer_must_partition_all_leaves(self):
        e = runner()
        self.assertTrue(hasattr(e, "validate_layer"), "cluster input partition guard missing")
        valid = [node("a", ["u1"]), node("b", ["u2"])]
        e.validate_layer(valid, {"u1", "u2"})
        for invalid in [[node("a", ["u1"])], [node("a", ["u1"]), node("b", ["u1", "u2"])]]:
            with self.assertRaises(ValueError):
                e.validate_layer(invalid, {"u1", "u2"})

    def test_tree_requires_hierarchy_and_child_union(self):
        e = runner()
        leaves = [node("L"+str(i), ["u"+str(i)], level=0) for i in range(4)]
        level1 = [dict(node("A"+str(i), ["u"+str(i)]), child_node_ids=["L"+str(i)]) for i in range(4)]
        level2 = [dict(node("B"+str(i), ["u"+str(i*2), "u"+str(i*2+1)], level=2),
                       child_node_ids=["A"+str(i*2), "A"+str(i*2+1)]) for i in range(2)]
        root = dict(node("R", ["u0", "u1", "u2", "u3"], level=3), child_node_ids=["B0", "B1"])
        tree = level1 + level2 + [root]
        e.validate_tree(tree, leaves)
        bad = copy.deepcopy(tree); bad[-1]["descendant_unit_ids"] = ["u0"]
        with self.assertRaises(ValueError):
            e.validate_tree(bad, leaves)
        bad = copy.deepcopy(tree); bad[1]["child_node_ids"] = ["L0"]
        with self.assertRaises(ValueError):
            e.validate_tree(bad, leaves)

    def test_score_binding_forbids_wrong_text_source_runtime_and_run(self):
        e = runner()
        query = dict(query_id="q", text="query")
        unit = dict(unit_id="u1", file_id="F1", text="original", source_sha256="source")
        args = ("manifest", {"model": "m"}, {"node_input": "n"}, "run1")
        expected = e.score_binding(query, unit, *args)
        for changed in [dict(unit, text="wrong"), dict(unit, source_sha256="wrong")]:
            with self.assertRaises(ValueError):
                e.validate_score_binding(e.score_binding(query, changed, *args), expected)
        for runtime, rid in [({"model": "other"}, "run1"), ({"model": "m"}, "run2")]:
            with self.assertRaises(ValueError):
                e.validate_score_binding(e.score_binding(query, unit, "manifest", runtime, args[2], rid), expected)

    def test_same_round_pool_reuses_only_exact_inputs(self):
        e = runner()
        class Model:
            calls = 0
            def rerank(self, query, candidates, units, corpus, query_id):
                self.calls += len(candidates)
                return [dict(unit_id=r["unit_id"], score=2.5) for r in candidates]
        models = Model()
        q = dict(query_id="q", text="text")
        units = {"u1": dict(unit_id="u1", file_id="F1", text="source", source_sha256="s")}
        pool = {}
        kwargs = dict(manifest_sha="m", runtime={}, inputs={}, run_id="one", pool=pool, pool_handle=io.StringIO())
        _, first = e.score_candidates(models, q, [dict(unit_id="u1")], units, "B0", **kwargs)
        _, second = e.score_candidates(models, q, [dict(unit_id="u1")], units, "DIR", **kwargs)
        self.assertEqual((first["newly_scored_units"], second["reused_units"], models.calls), (1, 1, 1))
        changed = {"u1": dict(units["u1"], text="different")}
        e.score_candidates(models, q, [dict(unit_id="u1")], changed, "TREE", **kwargs)
        self.assertEqual(models.calls, 2)

    def test_new_cache_and_output_refuse_overwrite_and_escape(self):
        e = runner()
        with tempfile.TemporaryDirectory(dir=HERE) as d:
            path = Path(d)
            e.validate_new_cache(path / "new")
            (path / "existing").mkdir()
            with self.assertRaises(FileExistsError):
                e.validate_new_cache(path / "existing")
            with self.assertRaises(ValueError):
                e.validate_new_cache(HERE.parent / "outside")
            out = path / "out.json"
            e.assert_new_output(out)
            Path(str(out) + ".partial").write_text("partial")
            with self.assertRaises(FileExistsError):
                e.assert_new_output(out)

    def test_freeze_rejects_drift_and_missing_dependency(self):
        e = runner()
        with tempfile.TemporaryDirectory(dir=HERE) as d:
            path = Path(d)
            dep = path / "input"; dep.write_text("one")
            freeze = path / "freeze.json"
            freeze.write_text(json.dumps({"files_sha256": {str(dep.resolve()): e.sha_file(dep)}}))
            e.validate_freeze(freeze, [dep])
            with self.assertRaises(ValueError):
                e.validate_freeze(freeze, [path / "other"])
            dep.write_text("changed")
            with self.assertRaises(ValueError):
                e.validate_freeze(freeze, [dep])


if __name__ == "__main__":
    unittest.main()
