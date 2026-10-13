"""Synthetic E04 logic tests; no model load, source corpus scan or GPU use."""
from __future__ import annotations

import copy
import importlib.util
import json
import math
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("e04_experiment_tested", HERE / "experiment.py")
experiment = None
if (HERE / "experiment.py").exists():
    experiment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(experiment)


def route(*ids):
    return [dict(unit_id=uid, score=999999 - i, rank=i + 1) for i, uid in enumerate(ids)]


def unit(uid, fid="F000001", cases=("case1",), text="索引短原文"):
    return dict(unit_id=uid, file_id=fid, case_id=cases[0] if cases else fid + ":SOURCE",
                case_ids=list(cases), behavior_id="behavior1", behavior_ids=["behavior1"],
                associations=[], qualifier_source_links=[], text=text, source_text=text,
                source_spans=[dict(start=0, end=len(text))], source_sha256="source-sha",
                context_text="完整上下文\n" + text, context_source_text="完整上下文\n" + text,
                context_spans=[dict(start=0, end=10)], context_segments=[dict(text="完整上下文")])


class SyntheticTokenizer:
    def __call__(self, texts, *, return_tensors=None, **kwargs):
        if return_tensors is None:
            return {"input_ids": [[1] for _ in texts]}
        import torch
        return {"input_ids": torch.ones((len(texts), 1), dtype=torch.long),
                "attention_mask": torch.ones((len(texts), 1), dtype=torch.long)}


def cache_fixture(tmp):
    import numpy as np
    from types import SimpleNamespace
    backend, _ = experiment.frozen_modules()
    legacy, new = Path(tmp) / "legacy", Path(tmp) / "new"
    legacy.mkdir()
    units = [unit("x")]
    models = SimpleNamespace(embedding_info=dict(cache_sha256="synthetic-embedding"),
                             np=np,
                             embed_tokenizer=SyntheticTokenizer(),
                             args=SimpleNamespace(cache=new, max_length=512, precision="float32", device="cpu", batch_size=16),
                             log=dict(torch="synthetic", transformers="synthetic", cache_events=[], truncation=[]))
    binding = dict(model=models.embedding_info, tokenizer_class="SyntheticTokenizer", token_audit_schema_version=2,
                   max_length=512, query_instruction="", pooling="CLS", normalization="L2",
                   torch="synthetic", transformers="synthetic", precision="float32", kind="document")
    text_sha = backend.ordered_text_sha(units)
    key = backend.cache_key(text_sha, binding)
    npy = legacy / (key + ".npy")
    np.save(npy, np.array([[1.0, 0.0]], dtype="float32"), allow_pickle=False)
    metadata = dict(key=key, binding=binding, ordered_unit_text_sha256=text_sha,
                    npy_sha256=experiment.sha_file(npy), shape=[1, 2],
                    token_summary=dict(stage="embedding", kind="document", inputs=1, truncated_inputs=0,
                                       max_input_tokens=1, max_length=512),
                    token_audit=[dict(id="x", input_tokens=1, used_tokens=1, truncated=False)])
    experiment.save_json(legacy / (key + ".json"), metadata)
    (legacy / "unrelated-cache.npy").write_bytes(b"do not copy")
    old_log = dict(models=dict(cache_events=[dict(corpus="structured", kind="document", key=key, hit=False)]))
    manifest = dict(corpora=dict(structured=dict(ordered_unit_text_sha256=text_sha, count=1)))
    return backend, old_log, manifest, units, models, legacy, new, key


class E04Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(experiment, "E04 implementation does not exist yet")

    def test_weighted_rrf_changes_priority_without_using_raw_scores(self):
        routes = [route("z", "a"), route("a", "z")]
        equal = experiment.weighted_rrf(routes, [1, 1])
        weighted = experiment.weighted_rrf(routes, [2, 1])
        self.assertEqual([r["unit_id"] for r in equal], ["a", "z"])
        self.assertEqual(weighted[0]["unit_id"], "z")
        self.assertAlmostEqual(weighted[0]["score"], 2 / 61 + 1 / 62)
        routes[0][0]["score"] = -math.inf
        routes[1][0]["score"] = math.inf
        self.assertEqual(experiment.weighted_rrf(routes, [2, 1]), weighted)

    def test_route_duplicate_does_not_add_score_or_consume_rank(self):
        actual = experiment.weighted_rrf([route("x", "x", "y"), []], [1, 1])
        self.assertEqual(actual, experiment.weighted_rrf([route("x", "y"), []], [1, 1]))
        self.assertEqual(actual[1]["score"], 1 / 62)

    def test_missing_route_keeps_available_route(self):
        self.assertEqual(experiment.weighted_rrf([None, route("x")], [2, 1]),
                         [dict(unit_id="x", score=1 / 61, rank=1)])

    def test_empty_routes_return_no_candidates(self):
        self.assertEqual(experiment.weighted_rrf([[], []], [1, 1]), [])

    def test_rrf_stable_ties_and_depth(self):
        actual = experiment.weighted_rrf([route("z"), route("a")], [1, 1], top_k=1)
        self.assertEqual(actual, [dict(unit_id="a", score=1 / 61, rank=1)])

    def test_rrf_rejects_invalid_k_weights_depth(self):
        for options in [dict(k=0), dict(k=-1), dict(k=float("nan")), dict(k=True),
                        dict(top_k=0), dict(top_k=1.5), dict(top_k=True)]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                experiment.weighted_rrf([route("x"), []], [1, 1], **options)
        for weights in [[], [1], [1, 0], [-1, 1], [math.inf, 1], [math.nan, 1], [True, 1]]:
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                experiment.weighted_rrf([route("x"), []], weights)

    def test_arm_100_200_candidate_difference_is_real_union(self):
        routes = [route(*[f"b{i:03}" for i in range(100)]),
                  route(*[f"d{i:03}" for i in range(100)])]
        shallow = experiment.candidates_for_arm(routes, "A0")
        deep = experiment.candidates_for_arm(routes, "A2")
        self.assertEqual(len(shallow), 100)
        self.assertEqual(len(deep), 200)
        self.assertEqual(len(experiment.missing_candidates(deep, {r["unit_id"]: 0 for r in shallow})), 100)
        self.assertEqual({r["unit_id"] for r in deep}, {r["unit_id"] for route_ in routes for r in route_})

    def test_arm_truncates_routes_to_top100(self):
        rows = route(*[f"x{i:03}" for i in range(105)])
        self.assertEqual(len(experiment.candidates_for_arm([rows, []], "A3")), 100)
        with self.assertRaises(ValueError):
            experiment.candidates_for_arm([rows, []], "A4")

    def test_score_binding_refuses_changed_source_query_or_indexed_text(self):
        query = dict(query_id="Q1", text="查询")
        binding = experiment.score_binding(query, unit("x"), "manifest", dict(precision="float16"))
        experiment.validate_score_binding(binding, copy.deepcopy(binding))
        for key in ["query_id", "query_text_sha256", "indexed_text_sha256", "source_sha256", "manifest_sha256", "runtime"]:
            stale = copy.deepcopy(binding)
            stale[key] = "changed"
            with self.subTest(key=key), self.assertRaises(ValueError):
                experiment.validate_score_binding(stale, binding)

    def test_dev_query_requires_exact_original_text(self):
        frozen = {"Q1": dict(query_id="Q1", text="原始查询")}
        experiment.validate_dev_query(dict(query_id="Q1", text="原始查询"), frozen)
        for query in [dict(query_id="Q2", text="原始查询"), dict(query_id="Q1", text=" 原始查询")]:
            with self.assertRaises(ValueError):
                experiment.validate_dev_query(query, frozen)

    def test_unit_source_binding_refuses_stale_or_unknown_source(self):
        bindings = {"F000001": dict(text_sha256="source-sha", effective_draft_json_sha256="draft")}
        row = unit("x") | dict(candidate_sha256="draft")
        experiment.validate_unit_binding(row, bindings)
        for key in ["source_sha256", "candidate_sha256", "file_id"]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                experiment.validate_unit_binding(row | {key: "stale"}, bindings)

    def test_a0_uses_frozen_v2_aggregate_and_full_context(self):
        _, adapter = experiment.frozen_modules()
        units = {"x": unit("x", cases=("case1", "case2")), "y": unit("y", "F000002", ())}
        scores = {"x": 4.0, "y": 3.0}
        routes = [route("x", "y"), []]
        record = experiment.build_record(dict(query_id="Q1", text="查询"), "A0", routes, scores, units, adapter,
                                         timing={}, provenance={})
        expected = adapter.aggregate(record["stages"]["rerank"], units)
        self.assertEqual((record["cases"], record["files"]), expected)
        self.assertEqual(record["files"][0]["text"], units["x"]["context_text"])
        self.assertEqual(record["files"][0]["indexed_text"], units["x"]["text"])
        self.assertEqual(record["files"][0]["case_ids"], ["case1", "case2"])
        self.assertEqual(record["stages"]["rerank_candidates"], record["stages"]["rrf_top100"])

    def test_build_record_refuses_missing_or_nonfinite_rerank_score(self):
        _, adapter = experiment.frozen_modules()
        for scores in [{}, {"x": math.nan}, {"x": math.inf}]:
            with self.assertRaises(ValueError):
                experiment.build_record(dict(query_id="Q1", text="查询"), "A0", [route("x"), []], scores,
                                        {"x": unit("x")}, adapter, timing={}, provenance={})

    def test_score_pool_calls_real_interface_once_for_only_missing_candidates(self):
        calls = []
        class ModelInterface:
            def rerank(self, query, candidates, unit_map, corpus, query_id):
                calls.append((query, copy.deepcopy(candidates), corpus, query_id))
                return [dict(unit_id=r["unit_id"], score=float(i + 2), rank=i + 1) for i, r in enumerate(candidates)]
        query = dict(query_id="Q1", text="查询")
        pool, measured = experiment.fill_score_pool(query, route("x", "y", "z"),
                                                  {u: unit(u) for u in ["x", "y", "z"]},
                                                  {"x": 1.0}, ModelInterface())
        self.assertEqual(len(calls), 1)
        self.assertEqual([r["unit_id"] for r in calls[0][1]], ["y", "z"])
        self.assertEqual(pool, {"x": 1.0, "y": 2.0, "z": 3.0})
        self.assertGreaterEqual(measured, 0)

    def test_score_pool_refuses_incomplete_model_scores(self):
        class ModelInterface:
            def rerank(self, *args):
                return []
        with self.assertRaises(ValueError):
            experiment.fill_score_pool(dict(query_id="Q1", text="查询"), route("x"), {"x": unit("x")}, {}, ModelInterface())

    def test_baseline_reproduction_checks_stages_and_aggregate(self):
        _, adapter = experiment.frozen_modules()
        units = {"x": unit("x")}
        record = experiment.build_record(dict(query_id="Q1", text="查询"), "A0", [route("x"), []], {"x": 1}, units,
                                         adapter, timing={}, provenance={})
        original = copy.deepcopy(record)
        experiment.assert_a0_reproduction(record, original)
        for key in ["files", "cases", "stages"]:
            stale = copy.deepcopy(original)
            stale[key] = {} if key == "stages" else []
            with self.subTest(key=key), self.assertRaises(ValueError):
                experiment.assert_a0_reproduction(record, stale)

    def test_confirmation_arms_must_match_frozen_selection_sha(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            path = Path(tmp) / "selection.json"
            path.write_text(json.dumps(dict(confirmation_arms=["A0", "A2"], selected_arm="A2")), encoding="utf-8")
            sha = experiment.sha_file(path)
            self.assertEqual(experiment.load_selection(path, sha, ["A0", "A2"])["sha256"], sha)
            with self.assertRaises(ValueError):
                experiment.load_selection(path, "0" * 64, ["A0", "A2"])
            with self.assertRaises(ValueError):
                experiment.load_selection(path, sha, ["A0", "A3"])

    def test_selection_accepts_chosen_arm_from_evaluation(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            path = Path(tmp) / "selection.json"
            path.write_text(json.dumps(dict(confirmation_arms=["A0", "A3"], chosen_arm="A0")), encoding="utf-8")
            try:
                selection = experiment.load_selection(path, experiment.sha_file(path), ["A0", "A3"])
            except ValueError:
                selection = {}
            self.assertEqual(selection.get("chosen_arm"), "A0")

    def test_historical_unused_normalization_change_does_not_invalidate_retest(self):
        manifest = experiment.read_json(experiment.PREPARED / "manifest.json")
        self.assertNotEqual(experiment.sha_file(experiment.ADAPTER.parent / "normalize_v2.py"), manifest["normalization_sha256"])
        try:
            provenance = experiment.validate_preparation_dependencies(manifest)
        except AttributeError:
            provenance = {}
        self.assertEqual(provenance.get("historical_normalization_sha256"), manifest["normalization_sha256"])
        self.assertFalse(provenance.get("normalization_executed_in_retrieval", True))

    def test_failed_preparation_produces_failure_log_without_final_output(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            query_path = Path(tmp) / "queries.jsonl"
            query_path.write_text(json.dumps(dict(query_id="Q1", text="查询")) + "\n", encoding="utf-8")
            output = Path(tmp) / "result.jsonl"
            args = SimpleNamespace(output=output, queries=query_path, mode="dev", arms=["A0"], selection=None, selection_sha256=None)
            with patch.object(experiment, "prepare_inputs", side_effect=ValueError("stale source")):
                with self.assertRaises(ValueError):
                    experiment.run(args)
            self.assertFalse(output.exists())
            self.assertEqual(experiment.read_json(Path(str(output) + ".run.json"))["status"], "failure")
            self.assertIn("stale source", experiment.read_json(Path(str(output) + ".failure.json"))["error"])

    def test_invalid_query_preflight_is_recorded_as_failure(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            query_path = Path(tmp) / "queries.jsonl"
            query_path.write_text(json.dumps(dict(query_id="Q1", text="")) + "\n", encoding="utf-8")
            output = Path(tmp) / "result.jsonl"
            args = SimpleNamespace(output=output, queries=query_path, mode="dev", arms=["A0"], selection=None, selection_sha256=None)
            with self.assertRaises(ValueError):
                experiment.run(args)
            log_path = Path(str(output) + ".run.json")
            self.assertTrue(log_path.exists(), "preflight failures need an explicit failure log")
            self.assertEqual(experiment.read_json(log_path)["status"], "failure")

    def test_dev_orchestration_uses_one_shared_pool_and_reproduces_a0(self):
        from types import SimpleNamespace
        _, adapter = experiment.frozen_modules()
        routes = [route(*[f"x{i:03}" for i in range(100)]), route(*[f"x{i:03}" for i in range(40, 140)])]
        units = {f"x{i:03}": unit(f"x{i:03}", f"F{i:06}", (f"case{i}",)) for i in range(140)}
        query = dict(query_id="Q1", text="查询")
        reused = {r["unit_id"]: float(200-i) for i, r in enumerate(experiment.candidates_for_arm(routes, "A0"))}
        original = experiment.build_record(query, "A0", routes, reused, units, adapter, timing=dict(bm25_seconds=1, dense_seconds=2), provenance={})
        calls = []
        old_models = dict(device="cuda", precision="float16", query_instruction="instruction", torch="frozen", transformers="frozen",
                          numpy="frozen", embedding=dict(cache_sha256="embed"), reranker=dict(cache_sha256="rerank"))
        old_log = dict(parameters=dict(embedding_model="embed", reranker_model="rerank", project_src="src", device="cuda",
                                      precision="float16", batch_size=16, max_length=512), models=old_models)
        class ModelInterface:
            def __init__(self, args):
                self.args = args
                self.log = copy.deepcopy(old_models) | dict(model_load_seconds=0, gpu="synthetic", truncation=[], cache_events=[])
                self.token_handle = Path(str(args.output) + ".token_audit.jsonl").open("w", encoding="utf-8")
            def rerank(self, text, candidates, unit_map, corpus, qid):
                calls.append([r["unit_id"] for r in candidates])
                return [dict(unit_id=r["unit_id"], score=0.5, rank=i) for i, r in enumerate(candidates, 1)]
        fake_backend = SimpleNamespace(LocalModels=ModelInterface)
        prepared = (fake_backend, adapter, old_log, dict(corpora=dict(structured=dict(sha256="structured"))),
                    list(units.values()), units, {"Q1": original}, dict(source_files=9639))
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            query_path, output = Path(tmp) / "queries.jsonl", Path(tmp) / "results.jsonl"
            query_path.write_text(json.dumps(query) + "\n", encoding="utf-8")
            args = SimpleNamespace(output=output, queries=query_path, mode="dev", arms=["A0", "A1", "A2", "A3"], selection=None, selection_sha256=None)
            with patch.object(experiment, "prepare_inputs", return_value=prepared):
                log = experiment.run(args)
            records = list(experiment.read_jsonl(output))
            pool = list(experiment.read_jsonl(Path(str(output) + ".score_pool.jsonl")))
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(calls[0]), 40)
            self.assertEqual(log["status"], "complete")
            self.assertEqual(len(records), 4)
            self.assertEqual(len(pool), 140)
            experiment.assert_a0_reproduction(records[0], original)
            self.assertEqual(records[2]["files"], records[3]["files"])
            self.assertEqual(sum(r["provenance"]["kind"] == "frozen_same_input_rerank" for r in pool), 100)
            self.assertEqual(sum(r["provenance"]["kind"] == "actual_local_gpu_rerank" for r in pool), 40)
            self.assertTrue(all(r["binding"]["indexed_text_sha256"] == experiment.sha_text(units[r["unit_id"]]["text"]) for r in pool))

    def test_output_guard_refuses_any_existing_sidecar(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            output = Path(tmp) / "results.jsonl"
            experiment.assert_new_output(output)
            for suffix in ["", ".partial", ".run.json", ".failure.json", ".token_audit.jsonl", ".score_pool.jsonl"]:
                target = Path(str(output) + suffix)
                target.touch()
                with self.subTest(suffix=suffix), self.assertRaises(FileExistsError):
                    experiment.assert_new_output(output)
                target.unlink()

    def test_model_args_use_new_e04_cache(self):
        from types import SimpleNamespace
        old_log = dict(parameters=dict(embedding_model="embed", reranker_model="rerank", project_src="src", device="cuda",
                                      precision="float16", batch_size=16, max_length=512))
        args = experiment.make_model_args(HERE / "synthetic-results.jsonl", old_log)
        self.assertEqual(args.cache, HERE / "vector_cache")
        self.assertNotEqual(args.cache, experiment.ROOT / "work/finrisk_retrieval_20261012/vector_cache")

    def test_only_document_cache_pair_is_copied_and_legacy_is_unchanged(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            backend, old_log, manifest, units, models, legacy, new, key = cache_fixture(tmp)
            before = {p.name: experiment.sha_file(p) for p in legacy.iterdir()}
            self.assertTrue(hasattr(experiment, "seed_document_cache"), "read-only document cache transplant is missing")
            result = experiment.seed_document_cache(old_log, manifest, units, models, backend, legacy_cache=legacy)
            self.assertEqual(result["key"], key)
            self.assertEqual({p.name for p in new.iterdir()}, {key + ".json", key + ".npy"})
            self.assertEqual({p.name: experiment.sha_file(p) for p in legacy.iterdir()}, before)
            for suffix in [".json", ".npy"]:
                self.assertEqual(experiment.sha_file(new / (key + suffix)), before[key + suffix])
            experiment.seed_document_cache(old_log, manifest, units, models, backend, legacy_cache=legacy)

    def test_document_cache_rejects_stale_binding_and_different_existing_files(self):
        self.assertTrue(hasattr(experiment, "seed_document_cache"), "read-only document cache transplant is missing")
        for changed in ["key", "npy_sha256", "ordered_unit_text_sha256", "binding", "token_audit", "shape", "destination"]:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory(dir=HERE) as tmp:
                backend, old_log, manifest, units, models, legacy, new, key = cache_fixture(tmp)
                metadata_path = legacy / (key + ".json")
                if changed == "destination":
                    new.mkdir()
                    (new / (key + ".npy")).write_bytes(b"different existing content")
                else:
                    metadata = experiment.read_json(metadata_path)
                    metadata[changed] = "stale"
                    experiment.save_json(metadata_path, metadata)
                before = {p.name: experiment.sha_file(p) for p in legacy.iterdir()}
                with self.assertRaises((ValueError, FileExistsError)):
                    experiment.seed_document_cache(old_log, manifest, units, models, backend, legacy_cache=legacy)
                self.assertEqual({p.name: experiment.sha_file(p) for p in legacy.iterdir()}, before)
                if changed == "destination":
                    self.assertEqual((new / (key + ".npy")).read_bytes(), b"different existing content")
                    self.assertFalse((new / (key + ".json")).exists())

    @unittest.skipUnless(importlib.util.find_spec("torch") and importlib.util.find_spec("numpy"), "original encode CPU synthetic test uses existing GPU Python packages")
    def test_original_encode_document_hit_and_new_query_miss_write_only_new_cache(self):
        import numpy as np
        import torch
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            backend, old_log, manifest, units, models, legacy, new, key = cache_fixture(tmp)
            before = {p.name: experiment.sha_file(p) for p in legacy.iterdir()}
            self.assertTrue(hasattr(experiment, "seed_document_cache"), "read-only document cache transplant is missing")
            experiment.seed_document_cache(old_log, manifest, units, models, backend, legacy_cache=legacy)
            original = backend.LocalModels.__new__(backend.LocalModels)
            original.__dict__.update(models.__dict__)
            original.np, original.torch = np, torch
            class SyntheticEmbedding:
                def __call__(self, **tokens):
                    return SimpleNamespace(last_hidden_state=torch.ones((tokens["input_ids"].shape[0], 1, 2)))
            original.embedding = SyntheticEmbedding()
            original.token_handle = (Path(tmp) / "new-token-audit.jsonl").open("w", encoding="utf-8")
            try:
                vectors = original.encode(units, "document", "structured")
                self.assertTrue(original.log["cache_events"][-1]["hit"])
                np.testing.assert_array_equal(vectors, np.array([[1.0, 0.0]], dtype="float32"))
                original.encode([dict(query_id="new-query", text="新的确认查询")], "query", "shared")
                self.assertFalse(original.log["cache_events"][-1]["hit"])
                query_key = original.log["cache_events"][-1]["key"]
                self.assertTrue((new / (query_key + ".json")).is_file())
                self.assertTrue((new / (query_key + ".npy")).is_file())
                self.assertFalse((legacy / (query_key + ".json")).exists())
                self.assertEqual({p.name: experiment.sha_file(p) for p in legacy.iterdir()}, before)
                self.assertNotIn("unrelated-cache.npy", {p.name for p in new.iterdir()})
            finally:
                original.token_handle.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
