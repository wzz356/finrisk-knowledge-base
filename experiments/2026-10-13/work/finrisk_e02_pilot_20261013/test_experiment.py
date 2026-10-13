"""E02 logic tests: no source population scan, model load, or GPU inference."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import io
import json
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
experiment = None
if (HERE / "experiment.py").exists():
    spec = importlib.util.spec_from_file_location("e02_experiment_tested", HERE / "experiment.py")
    experiment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(experiment)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fixtures():
    source = "甲保险公司。销售人员宣传收益。原片段。另一个片段。"
    def unit(uid, text):
        return dict(unit_id=uid, file_id="F1", case_id="C1", case_ids=["C1"],
                    text=text, source_text=text, source_sha256=sha(source),
                    source_spans=[dict(start=source.index(text), end=source.index(text)+len(text))],
                    context_text="原片段。另一个片段。", context_source_text="原片段。另一个片段。",
                    context_spans=[dict(start=source.index("原片段。"), end=len(source))],
                    context_segments=[dict(text="原片段。另一个片段。")])
    units = [unit("U1", "原片段。"), unit("U2", "另一个片段。")]
    quote = "甲保险公司"
    row = dict(unit_id="U1", file_id="F1", source_sha256=sha(source),
               base_unit_text_sha256=sha(units[0]["text"]),
               claims=[dict(label="文书主体", quote=quote, span=dict(start=0, end=len(quote)),
                            link_reason="文书主体，未声称个人实施。")],
               prefix_text="文书主体："+quote, notes="候选")
    review = dict(unit_id="U1", status="approved_model_review", prefix_sha256=sha(row["prefix_text"]),
                  source_sha256=sha(source), reason="审核通过")
    cohort = dict(rows=[{k: row[k] for k in ("unit_id", "file_id", "source_sha256", "base_unit_text_sha256")}])
    return units, row, review, cohort, {"F1": source}


class E02Tests(unittest.TestCase):
    def setUp(self):
        if experiment is None:
            self.fail("E02 experiment implementation is missing")
        self.units, self.row, self.review, self.cohort, self.sources = fixtures()
        self.unit_map = {u["unit_id"]: u for u in self.units}

    def validate(self, rows=None, reviews=None):
        return experiment.validate_prefixes(rows if rows is not None else [self.row],
                    reviews if reviews is not None else [self.review], self.cohort, self.unit_map, self.sources)

    def test_approved_exact_extract_is_allowed(self):
        self.assertEqual(self.validate(), {"U1": self.row})

    def test_rejected_prefix_does_not_change_dose(self):
        self.review["status"] = "rejected"
        self.assertEqual(self.validate(), {})

    def test_missing_semantic_review_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "review"):
            self.validate(reviews=[])

    def test_review_prefix_bytes_are_bound(self):
        self.review["prefix_sha256"] = sha("不同前缀")
        with self.assertRaisesRegex(ValueError, "review"):
            self.validate()

    def test_source_sha_and_base_text_sha_are_bound(self):
        for field in ("source_sha256", "base_unit_text_sha256"):
            bad = copy.deepcopy(self.row)
            bad[field] = sha("改过")
            with self.assertRaises(ValueError):
                self.validate(rows=[bad])

    def test_quote_must_match_precise_interval(self):
        self.row["claims"][0]["span"]["start"] = 1
        with self.assertRaisesRegex(ValueError, "span|quote"):
            self.validate()

    def test_boolean_and_outside_span_rejected(self):
        for start, end in ((True, 6), (-1, 6), (0, 999)):
            bad = copy.deepcopy(self.row)
            bad["claims"][0]["span"] = dict(start=start, end=end)
            with self.assertRaises(ValueError):
                self.validate(rows=[bad])

    def test_unknown_label_or_unquoted_prefix_rejected(self):
        for change in ("label", "prefix"):
            bad = copy.deepcopy(self.row)
            if change == "label":
                bad["claims"][0]["label"] = "处罚日期"
            else:
                bad["prefix_text"] += "\n自行推断事实"
            with self.assertRaises(ValueError):
                self.validate(rows=[bad])

    def test_duplicate_prefix_or_review_rejected(self):
        with self.assertRaises(ValueError):
            self.validate(rows=[self.row, self.row])
        with self.assertRaises(ValueError):
            self.validate(reviews=[self.review, self.review])

    def test_prefix_over_180_chars_rejected(self):
        self.row["prefix_text"] = "甲"*181
        with self.assertRaises(ValueError):
            self.validate()

    def test_quality_binds_whole_candidate_files_including_spans_and_link_reason(self):
        self.assertTrue(callable(getattr(experiment,"validate_quality",None)),"full prefix/review artifact binding is missing")
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            temp = Path(directory)
            prefixes,reviews,quality = temp/"prefixes.jsonl",temp/"prefix_review.jsonl",temp/"prefix_quality.json"
            original = json.dumps(self.row,ensure_ascii=False)+"\n"
            prefixes.write_text(original,encoding="utf-8")
            reviews.write_text(json.dumps(self.review,ensure_ascii=False)+"\n",encoding="utf-8")
            experiment.save_json(quality,dict(files_sha256={"prefixes.jsonl":experiment.sha_file(prefixes),
                                      "prefix_review.jsonl":experiment.sha_file(reviews)}))
            experiment.validate_quality(prefixes,reviews,quality)
            for change in ("span","link_reason"):
                bad = copy.deepcopy(self.row)
                if change == "span":
                    bad["claims"][0]["span"] = dict(start=10,end=16)
                else:
                    bad["claims"][0]["link_reason"] = "改为其他行为关联"
                self.assertEqual(bad["prefix_text"],self.row["prefix_text"])
                self.assertEqual(bad["source_sha256"],self.row["source_sha256"])
                prefixes.write_text(json.dumps(bad,ensure_ascii=False)+"\n",encoding="utf-8")
                with self.assertRaisesRegex(ValueError,"SHA256"):
                    experiment.validate_quality(prefixes,reviews,quality)
            prefixes.write_text(original,encoding="utf-8")
            reviews.write_text("{}\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"SHA256"):
                experiment.validate_quality(prefixes,reviews,quality)

    def test_overlay_changes_only_selected_text_and_preserves_originals(self):
        before = copy.deepcopy(self.units)
        overlay = experiment.make_overlay(self.units, self.validate())
        self.assertEqual(self.units, before)
        self.assertEqual(overlay[0]["text"], self.row["prefix_text"]+"\n"+before[0]["text"])
        self.assertEqual({k:v for k,v in overlay[0].items() if k != "text"},
                         {k:v for k,v in before[0].items() if k != "text"})
        self.assertIs(overlay[1], self.units[1])

    def test_overlay_vectors_replace_only_selected_positions(self):
        import numpy as np
        base = np.array([[1, 2], [3, 4]], dtype="float32")
        original = base.copy()
        changed = np.array([[5, 6]], dtype="float32")
        result, rows = experiment.overlay_vectors(base, self.units, [self.units[0]], changed, np)
        np.testing.assert_array_equal(base, original)
        np.testing.assert_array_equal(result, [[5, 6], [3, 4]])
        self.assertEqual(rows, [0])
        with self.assertRaises(ValueError):
            experiment.overlay_vectors(base, self.units, [self.units[0], self.units[0]], changed, np)

    def hit(self, uid="U1"):
        unit = self.unit_map[uid]
        return dict(unit_id=uid, file_id="F1", case_id="C1", case_ids=["C1"], rank=1, score=7.0,
                    text=unit["context_text"], prefix="", source_text=unit["context_source_text"],
                    source_spans=unit["context_spans"], source_segments=unit["context_segments"],
                    indexed_text=unit["text"], indexed_source_text=unit["source_text"],
                    indexed_source_spans=unit["source_spans"])

    def test_p1_return_preserves_body_and_has_actual_index_payload(self):
        hit = self.hit()
        returned = experiment.decorate_hit(hit, self.unit_map, self.validate(), "P1")
        self.assertEqual(returned["text"], "【背景说明（原文摘录，候选）】\n"+self.row["prefix_text"]+
                         "\n\n【原文片段】\n"+hit["text"])
        self.assertEqual(returned["indexed_text"], self.row["prefix_text"]+"\n"+self.units[0]["text"])
        for key in ("source_text", "source_spans", "source_segments", "indexed_source_text", "indexed_source_spans"):
            self.assertEqual(returned[key], hit[key])
        self.assertEqual(returned["base_context_text"], hit["text"])
        self.assertEqual(returned["original_unit_text"], self.units[0]["text"])
        self.assertEqual(returned.get("prefix_review_status"), "approved_model_review")
        self.assertEqual(hit, self.hit())

    def test_p2_preserves_index_and_no_prefix_bleeds_to_other_winner_unit(self):
        hit = self.hit()
        returned = experiment.decorate_hit(hit, self.unit_map, self.validate(), "P2")
        self.assertEqual(returned["indexed_text"], hit["indexed_text"])
        other = self.hit("U2")
        self.assertEqual(experiment.decorate_hit(other, self.unit_map, self.validate(), "P1"), other)

    def test_p0_full_stage_reproduction_is_strict(self):
        record = dict(query_id="Q1", text="输入", files=[self.hit()], cases=[self.hit()],
                      stages=dict(rerank_candidates=[dict(unit_id="U1", score=1, rank=1)]))
        experiment.assert_baseline_reproduction(record, copy.deepcopy(record))
        bad = copy.deepcopy(record)
        bad["stages"]["rerank_candidates"][0]["score"] += 1
        with self.assertRaises(ValueError):
            experiment.assert_baseline_reproduction(bad, record)

    def test_replay_query_text_group_or_role_drift_rejected(self):
        old = dict(query_id="Q1", text="输入", group="边界", query_role="boundary")
        experiment.validate_replay_queries([old], {"Q1":old}, expected_count=1)
        for field in ("query_id", "text", "group", "query_role"):
            bad = dict(old, **{field:"changed"})
            with self.assertRaises(ValueError):
                experiment.validate_replay_queries([bad], {"Q1":old}, expected_count=1)

    def test_output_and_every_sidecar_refuse_overwrite(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            output = Path(directory)/"results.jsonl"
            for suffix in experiment.SIDECARS:
                path = Path(str(output)+suffix)
                path.write_text("existing", encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    experiment.assert_new_output(output)
                self.assertEqual(path.read_text(encoding="utf-8"), "existing")
                path.unlink()

    def test_cache_must_stay_under_e02_work(self):
        self.assertEqual(experiment.validate_cache_path(HERE/"vector_cache"), (HERE/"vector_cache").resolve())
        for path in (HERE.parent/"finrisk_e04_pilot_20261012/vector_cache", HERE, HERE/"../escape"):
            with self.assertRaises(ValueError):
                experiment.validate_cache_path(path)

    def test_real_tokenizer_preflight_rejects_overlimit_before_inference(self):
        class Tokenizer:
            def __call__(self, texts, pairs=None, **kwargs):
                self.kwargs = kwargs
                return {"input_ids": [[1]*(len(a)+(len(b) if pairs else 0)+2)
                        for a,b in zip(texts, pairs if pairs else [""]*len(texts))]}
        tokenizer, handle = Tokenizer(), io.StringIO()
        with self.assertRaisesRegex(ValueError, "token limit"):
            experiment.audit_inputs(tokenizer, ["long input"], ["U1"], 5, handle, stage="embedding")
        self.assertFalse(tokenizer.kwargs["truncation"])
        row = json.loads(handle.getvalue())
        self.assertTrue(row["rejected"])
        self.assertEqual(row["id"], "U1")

    def test_rerank_scores_require_exact_candidate_ids_and_finite_values(self):
        candidates = [dict(unit_id="U1")]
        for rows in ([], [dict(unit_id="U2", score=2)], [dict(unit_id="U1", score=float("nan"))]):
            with self.assertRaises(ValueError):
                experiment.validate_computed_scores(candidates, rows)
        self.assertEqual(experiment.validate_computed_scores(candidates, [dict(unit_id="U1", score=3)]), {"U1":3.0})

    def test_frozen_seed_copies_only_bound_pair_and_leaves_old_cache_unchanged(self):
        import numpy as np
        e04 = experiment.frozen_e04()
        backend, _ = e04.frozen_modules()
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            root, units = Path(directory), self.units
            old, new = root/"old", root/"new"
            old.mkdir()
            class Tokenizer:
                pass
            models = SimpleNamespace(np=np,embed_tokenizer=Tokenizer(),embedding_info=dict(sha="test-model"),
                args=SimpleNamespace(cache=new,max_length=512,precision="float32"),log=dict(torch="test",transformers="test"))
            binding = e04.document_encoding_binding(models)
            text_sha = backend.ordered_text_sha(units)
            key = backend.cache_key(text_sha,binding)
            np.save(old/(key+".npy"),np.ones((len(units),2),dtype="float32"),allow_pickle=False)
            metadata = dict(key=key,binding=binding,ordered_unit_text_sha256=text_sha,shape=[len(units),2],
                npy_sha256=experiment.sha_file(old/(key+".npy")),token_audit=[dict(id=u["unit_id"],input_tokens=10,used_tokens=10,truncated=False) for u in units])
            experiment.save_json(old/(key+".json"),metadata)
            (old/"unrelated.npy").write_bytes(b"protected")
            snapshot = {p.name:experiment.sha_file(p) for p in old.iterdir()}
            old_log = dict(models=dict(cache_events=[dict(kind="document",corpus="structured",key=key)]))
            manifest = dict(corpora=dict(structured=dict(count=len(units),ordered_unit_text_sha256=text_sha)))
            seeded = e04.seed_document_cache(old_log,manifest,units,models,backend,legacy_cache=old)
            self.assertEqual(set(p.name for p in new.iterdir()),{key+".json",key+".npy"})
            self.assertEqual(snapshot,{p.name:experiment.sha_file(p) for p in old.iterdir()})
            self.assertEqual(seeded["legacy_cache_access"],"read_only")
            (new/(key+".json")).write_text("different",encoding="utf-8")
            with self.assertRaises(FileExistsError):
                e04.seed_document_cache(old_log,manifest,units,models,backend,legacy_cache=old)

    def test_all_66_records_use_real_interface_and_p2_frozen_ranking(self):
        """Synthetic model values test orchestration only; never efficacy or GPU."""
        import numpy as np
        e04 = experiment.frozen_e04()
        backend, adapter = e04.frozen_modules()
        base = [dict(self.units[i % 2],unit_id=f"U{i:03d}",file_id=f"F{i:03d}",
                     case_id=f"C{i:03d}",case_ids=[f"C{i:03d}"]) for i in range(100)]
        unit_map = {u["unit_id"]:u for u in base}
        approved = {u["unit_id"]:dict(self.row,unit_id=u["unit_id"],file_id=u["file_id"],
                      base_unit_text_sha256=sha(u["text"])) for u in base[:24]}
        queries = [dict(query_id=f"Q{i:02d}",text="测试查询",group="risk",query_role="risk") for i in range(22)]
        route = [dict(unit_id=u["unit_id"],score=float(100-i),rank=i+1) for i,u in enumerate(base)]
        baseline = {q["query_id"]:e04.build_record(q,"A0",[route,route],
                    {u["unit_id"]:float(100-i) for i,u in enumerate(base)},unit_map,adapter,timing={},provenance={}) for q in queries}
        origins = {q["query_id"]:dict(path="synthetic",sha256="synthetic",phase="dev") for q in queries}
        real_calls, encode_calls = [], []
        class Tokenizer:
            def __call__(self,texts,pairs=None,**kwargs):
                return {"input_ids":[[1]*10 for _ in texts]}
        class Models:
            def __init__(self,args):
                self.args,self.np = args,np
                self.embed_tokenizer,self.rerank_tokenizer = Tokenizer(),Tokenizer()
                self.token_handle = Path(str(args.output)+".token_audit.jsonl").open("x",encoding="utf-8")
                self.log = dict(cache_events=[],truncation=[],torch="synthetic",transformers="synthetic")
            def encode(self,rows,kind,corpus):
                encode_calls.append((kind,corpus,[r["text"] for r in rows]))
                hit = corpus == "structured"
                self.log["cache_events"].append(dict(hit=hit,key="base" if hit else corpus))
                return np.tile(np.array([1,0] if hit else [2,0],dtype="float32"),(len(rows),1))
            def rerank(self,query,candidates,mapping,corpus,query_id):
                real_calls.append((query_id,[r["unit_id"] for r in candidates],{r["unit_id"]:mapping[r["unit_id"]]["text"] for r in candidates}))
                return [dict(unit_id=r["unit_id"],score=float(1000-i)) for i,r in enumerate(candidates)]
        class RetrievalDocument:
            def __init__(self,**fields):
                self.__dict__.update(fields)
        class SparseIndex:
            def __init__(self,docs,**kwargs):
                self.docs = docs
                self.assertions = [d.text == (approved[d.unit_id]["prefix_text"]+"\n"+unit_map[d.unit_id]["text"] if d.unit_id in approved else unit_map[d.unit_id]["text"]) for d in docs]
                if not all(self.assertions):
                    raise AssertionError("BM25 corpus text overlay differs")
            def search(self,text,top_k):
                return [SimpleNamespace(document=d,score=float(100-i),rank=i+1) for i,d in enumerate(self.docs[:top_k])]
        sparse_module = types.ModuleType("retrieval.sparse")
        sparse_module.RetrievalDocument,sparse_module.SparseRetrievalIndex = RetrievalDocument,SparseIndex
        backend_proxy = SimpleNamespace(LocalModels=Models,QUERY_INSTRUCTION=backend.QUERY_INSTRUCTION,ordered_text_sha=backend.ordered_text_sha)
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            temp = Path(directory)
            for name in ("queries.jsonl","prefixes.jsonl","reviews.jsonl","cohort.json","input_freeze.json","prefix_inputs_p1.jsonl","prefix_inputs_p2.jsonl","prefix_quality.json"):
                (temp/name).write_text("{}\n",encoding="utf-8")
            args = SimpleNamespace(queries=temp/"queries.jsonl",prefixes=temp/"prefixes.jsonl",reviews=temp/"reviews.jsonl",
                                   output=temp/"results.jsonl",cache=temp/"cache")
            def seed(old_log,manifest,units,models,unused):
                models.args.cache.mkdir()
                experiment.save_json(models.args.cache/"base.json",dict(token_audit=[dict(truncated=False)]))
                return dict(key="base")
            prepared = (queries,baseline,origins,backend_proxy,adapter,{}, {},base,unit_map,approved,{})
            with patch.object(experiment,"OUT",temp),patch.object(experiment,"load_replay",return_value=prepared),\
                 patch.object(e04,"make_model_args",side_effect=lambda output,old:SimpleNamespace(output=output,cache=args.cache,max_length=512,project_src=temp)),\
                 patch.object(e04,"validate_models"),patch.object(e04,"runtime_binding",return_value={}),\
                 patch.object(e04,"seed_document_cache",side_effect=seed),patch.dict("sys.modules",{"retrieval.sparse":sparse_module}):
                log = experiment.run(args)
            records = experiment.read_jsonl(args.output)
            self.assertEqual(log["status"],"complete")
            self.assertEqual(len(records),66)
            self.assertEqual(len(real_calls),22)
            self.assertTrue(all(len(ids)==100 for _,ids,_ in real_calls))
            self.assertEqual([(kind,corpus,len(texts)) for kind,corpus,texts in encode_calls],
                [("document","structured",100),("query","E02_shared_queries",22),("document","E02_overlay",24)])
            self.assertTrue(all(texts["U000"]==approved["U000"]["prefix_text"]+"\n"+base[0]["text"] for _,_,texts in real_calls))
            for i in range(0,len(records),3):
                p0,p1,p2 = records[i:i+3]
                experiment.assert_baseline_reproduction(p0,baseline[p0["query_id"]])
                self.assertEqual(p0["stages"],p2["stages"])
                self.assertEqual([(h["file_id"],h["unit_id"],h["score"],h["rank"]) for h in p0["files"]],
                                 [(h["file_id"],h["unit_id"],h["score"],h["rank"]) for h in p2["files"]])
                self.assertTrue(p1["files"][0]["indexed_text"].startswith(approved["U000"]["prefix_text"]))
                self.assertEqual(p2["files"][0]["indexed_text"],base[0]["text"])
            pool = experiment.read_jsonl(Path(str(args.output)+".score_pool.jsonl"))
            self.assertEqual(len(pool),4400)
            self.assertEqual({r["provenance"]["kind"] for r in pool},{"frozen_E04_A0_real_rerank","actual_local_gpu_rerank100"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
