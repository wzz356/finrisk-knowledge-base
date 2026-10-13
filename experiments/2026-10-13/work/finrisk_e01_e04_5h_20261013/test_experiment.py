"""Synthetic safety/contract tests. These are not real GPU experiment results."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
experiment = None
if (HERE / "experiment.py").exists():
    spec = importlib.util.spec_from_file_location("fiveh_tested", HERE / "experiment.py")
    experiment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(experiment)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def row_sha(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False))


def fixtures():
    source = "甲公司。甲销售误导。乙公司。乙销售违规。"
    def segment(text):
        start = source.index(text)
        return dict(text=text, span=dict(start=start, end=start+len(text)), role="behavior", reason="同一编号的主体与行为")
    unit = dict(unit_id="U1", file_id="F1", case_id="C1", case_ids=["C1"], text="甲销售误导。",
                source_text="甲销售误导。", source_sha256=sha(source), source_spans=[segment("甲销售误导。")["span"]],
                context_text=source, context_source_text=source, context_spans=[dict(start=0, end=len(source))],
                context_segments=[dict(text=source, span=dict(start=0, end=len(source)))])
    other_source = "丙公司。丙销售误导。"
    other = dict(unit, unit_id="U2", file_id="F2", case_id="C2", case_ids=["C2"], text="丙销售误导。",
                 source_text="丙销售误导。", source_sha256=sha(other_source), source_spans=[dict(start=4, end=len(other_source))])
    segments = [segment("甲公司。"), segment("甲销售误导。")]
    claim = dict(label="片段主体", quote="甲公司", span=dict(start=0, end=3), link_reason="第一个主体仅关联同编号行为")
    row = dict(unit_id="U1", file_id="F1", source_sha256=sha(source), base_unit_text_sha256=sha(unit["text"]),
               segments=segments, indexed_text="\n".join(s["text"] for s in segments), scope_status="scoped",
               scope_reason="按原文编号约束主体", prefix_claims=[claim], prefix_text="片段主体：甲公司", notes="候选")
    review = dict(unit_id="U1", status="approved_model_review", scope_units_sha256="a"*64,
                  row_sha256=row_sha(row), source_sha256=sha(source), reason="原文关联明确", human_approved=False)
    cohort = dict(rows=[{k:row[k] for k in ("unit_id", "file_id", "source_sha256", "base_unit_text_sha256")}])
    return [unit, other], row, review, cohort, {"F1":source, "F2":other_source}


class ContractTests(unittest.TestCase):
    def setUp(self):
        if experiment is None:
            self.fail("five-hour implementation missing")
        self.units, self.row, self.review, self.cohort, self.sources = fixtures()
        self.unit_map = {u["unit_id"]:u for u in self.units}

    def validate(self, row=None, review=None):
        return experiment.validate_scope_units([row or self.row], [review or self.review], self.cohort,
                                              self.unit_map, self.sources, "a"*64)

    def test_approved_source_quotes_create_sha_bound_view(self):
        approved = self.validate()
        views = experiment.make_views(self.units, approved)
        self.assertEqual(views["S1"][0]["text"], self.row["indexed_text"])
        self.assertEqual(views["C2"][0]["text"], self.row["prefix_text"]+"\n"+self.row["indexed_text"])
        self.assertEqual(views["B0"][0], self.units[0])
        self.assertIs(views["S1"][1], self.units[1])
        self.assertNotEqual(views["S1"][0]["representation_id"], views["C2"][0]["representation_id"])
        self.assertIn(sha(views["S1"][0]["text"]), views["S1"][0]["representation_id"])

    def test_source_sha_and_quote_span_tampering_are_rejected(self):
        for change in ("source_sha256", "span", "indexed_text"):
            row = copy.deepcopy(self.row)
            if change == "source_sha256": row[change] = "b"*64
            elif change == "span": row["segments"][0]["span"]["end"] -= 1
            else: row[change] += "无原文支持"
            review = dict(self.review, row_sha256=row_sha(row))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate(row, review)

    def test_review_binds_whole_input_and_semantic_reason(self):
        for change in ("scope_units_sha256", "row_sha256"):
            review = dict(self.review, **{change:"b"*64})
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "review"):
                self.validate(review=review)
        row = dict(self.row, scope_reason="改为另一主体")
        with self.assertRaisesRegex(ValueError, "review"):
            self.validate(row=row)

    def test_scope_must_include_original_unit_and_cannot_invent_background(self):
        row = copy.deepcopy(self.row)
        row["segments"] = row["segments"][:1]
        row["indexed_text"] = row["segments"][0]["text"]
        with self.assertRaisesRegex(ValueError, "original unit"):
            self.validate(row, dict(self.review, row_sha256=row_sha(row)))
        row = copy.deepcopy(self.row)
        row["prefix_text"] = "适用条件：肯定违规"
        with self.assertRaisesRegex(ValueError, "prefix"):
            self.validate(row, dict(self.review, row_sha256=row_sha(row)))

    def test_rejected_and_ambiguous_scope_do_not_change_any_view(self):
        self.assertEqual(self.validate(review=dict(self.review, status="rejected")), {})
        row = dict(self.row, scope_status="ambiguous_unchanged", indexed_text=self.units[0]["text"],
                   segments=[self.row["segments"][1]], prefix_claims=[], prefix_text="")
        review = dict(self.review, row_sha256=row_sha(row))
        approved = self.validate(row, review)
        self.assertEqual(approved, {})
        views = experiment.make_views(self.units, approved)
        self.assertEqual(views["S1"], self.units)
        self.assertEqual(views["C2"], self.units)

    def test_changed_context_renders_only_reviewed_subject_without_mixing_table(self):
        approved = self.validate()
        adapter = experiment.frozen_e04().frozen_modules()[1]
        hit = adapter.evidence_row(self.units[0], 1.0)
        actual = experiment.decorate_hit(hit, self.unit_map, approved, "S1", self.sources)
        body = "【命中原话】\n甲销售误导。\n\n【命中原话的对应原文（逐段独立，不合并主体）】\n甲公司。"+experiment.GAP+"甲销售误导。"
        self.assertEqual(actual["text"], body)
        self.assertNotIn("乙公司", actual["text"])
        self.assertEqual(actual["source_text"], "甲公司。甲销售误导。")
        self.assertEqual(actual["original_unit_spans"], self.units[0]["source_spans"])
        self.assertEqual(actual["scope_review_status"], "approved_model_review")
        prefixed = experiment.decorate_hit(hit, self.unit_map, approved, "C2", self.sources)
        self.assertEqual(prefixed["text"], experiment.PREFIX_HEADER+"\n"+self.row["prefix_text"]+"\n\n"+body)
        self.assertEqual(prefixed["prefix_claims"], self.row["prefix_claims"])
        self.assertEqual(experiment.decorate_hit(hit,self.unit_map,approved,"M3",self.sources),hit)

    def test_cache_must_be_new_isolated_child_and_output_cannot_overwrite(self):
        for path in (HERE, HERE.parent / "finrisk_e02_pilot_20261013/vector_cache", HERE / "../outside"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                experiment.validate_cache_path(path)
        with tempfile.TemporaryDirectory(dir=HERE) as name:
            cache = Path(name)/"cache"
            self.assertEqual(experiment.validate_cache_path(cache), cache.resolve())
            output = Path(name)/"results.jsonl"
            Path(str(output)+".score_pool.jsonl").write_text("existing",encoding="utf-8")
            with self.assertRaises(FileExistsError): experiment.assert_new_output(output)

    def test_score_binding_rejects_same_id_with_changed_text_or_runtime(self):
        query = dict(query_id="Q",text="销售误导")
        first = experiment.score_binding(query,self.units[0],"m"*64,{"precision":"float16"},{"input":"a"})
        for unit,runtime in ((dict(self.units[0],text="另一段"),{"precision":"float16"}),
                             (self.units[0],{"precision":"float32"})):
            expected = experiment.score_binding(query,unit,"m"*64,runtime,{"input":"a"})
            with self.assertRaisesRegex(ValueError,"score binding"):
                experiment.validate_score_binding(first,expected)

    def test_identical_text_view_keeps_exact_same_model_score_binding(self):
        query=dict(query_id="Q",text="误导")
        unit=self.units[0]
        identical=dict(unit,representation_id=experiment.representation_id(unit,unit["text"]))
        base=experiment.score_binding(query,unit,"m",{}, {})
        view=experiment.score_binding(query,identical,"m",{}, {})
        self.assertEqual(base,view)

    def test_two_occurrences_stay_separate_and_missing_second_occurrence_is_rejected(self):
        source="甲行。相同事实。乙行。相同事实。"
        text="相同事实。"
        matches=experiment.all_spans(source,text)
        unit=dict(self.units[0],text=text,source_text=text,source_sha256=sha(source),source_spans=matches)
        row=dict(self.row,source_sha256=sha(source),base_unit_text_sha256=sha(text),occurrence_ambiguity=True,
            indexed_text="甲行。相同事实。\n乙行。相同事实。",prefix_claims=[],prefix_text="",
            segments=[dict(text=source[:9],span=dict(start=0,end=9),role="parallel_row",reason="第一行"),
                      dict(text=source[9:],span=dict(start=9,end=len(source)),role="parallel_row",reason="第二行")])
        # Correct source offsets derived from the two complete rows.
        cut=source.index("乙行")
        row["segments"][0]=dict(text=source[:cut],span=dict(start=0,end=cut),role="parallel_row",reason="第一行")
        row["segments"][1]=dict(text=source[cut:],span=dict(start=cut,end=len(source)),role="parallel_row",reason="第二行")
        row["indexed_text"]="\n".join(s["text"] for s in row["segments"])
        review=dict(self.review,source_sha256=sha(source),row_sha256=row_sha(row))
        cohort=dict(rows=[{k:row[k] for k in ("unit_id","file_id","source_sha256","base_unit_text_sha256")}])
        valid=experiment.validate_scope_units([row],[review],cohort,{"U1":unit},{"F1":source},"a"*64)
        adapter=experiment.frozen_e04().frozen_modules()[1]
        hit=experiment.decorate_hit(adapter.evidence_row(unit,1.0),{"U1":unit},valid,"S1",{"F1":source})
        self.assertTrue(hit["occurrence_ambiguity"])
        self.assertEqual(hit["matched_occurrences"],matches)
        row["segments"]=row["segments"][:1];row["indexed_text"]=row["segments"][0]["text"]
        review["row_sha256"]=row_sha(row)
        with self.assertRaisesRegex(ValueError,"occurrences"):
            experiment.validate_scope_units([row],[review],cohort,{"U1":unit},{"F1":source},"a"*64)

    def test_vector_encoding_uses_one_query_batch_and_only_changed_view_rows(self):
        import numpy as np
        calls=[]
        class Tokenizer:
            def __call__(self,texts,pairs=None,**kwargs): return {"input_ids":[[1]*5 for _ in texts]}
        with tempfile.TemporaryDirectory(dir=HERE) as name:
            cache=Path(name)/"cache"
            model=SimpleNamespace(args=SimpleNamespace(cache=cache,max_length=512),np=np,
                embed_tokenizer=Tokenizer(),token_handle=io.StringIO(),log=dict(cache_events=[]))
            def encode(rows,kind,corpus):
                calls.append((kind,corpus,[r["unit_id"] if "unit_id" in r else r["query_id"] for r in rows]))
                model.log["cache_events"].append(dict(hit=corpus=="structured",key="base" if corpus=="structured" else corpus))
                value=1 if corpus=="structured" else 2
                return np.tile(np.array([value,0],dtype="float32"),(len(rows),1))
            model.encode=encode
            def seed(*args):
                cache.mkdir()
                experiment.save_json(cache/"base.json",dict(token_audit=[dict(truncated=False)]))
                return dict(key="base")
            helper=SimpleNamespace(seed_document_cache=seed)
            backend=SimpleNamespace(QUERY_INSTRUCTION="检索：",ordered_text_sha=lambda rows:row_sha([(r["unit_id"],r["text"]) for r in rows]))
            views=experiment.make_views(self.units,self.validate())
            queries=[dict(query_id="Q1",text="误导"),dict(query_id="Q2",text="违规")]
            cards=[dict(card_id="K1",retrieval_text="机制一"),dict(card_id="K2",retrieval_text="机制二")]
            log={}
            qv,dv,cv=experiment.encode_views(model,backend,helper,{}, {},self.units,views,queries,cards,log)
            self.assertEqual([(a,b,len(c)) for a,b,c in calls],[("document","structured",2),("query","5h_shared_42_queries",2),
                ("document","5h_unique_modified_views",2),("document","5h_mechanism_cards",2)])
            self.assertTrue(all(":5h-view:" in uid for uid in calls[2][2]))
            self.assertEqual(log["vector_operation"]["unchanged_document_reencoding_rows"],0)
            self.assertEqual(log["vector_operation"]["views"]["S1"].get("representation_rows"),1)
            self.assertEqual(dv["B0"].shape,dv["C2"].shape)
            np.testing.assert_array_equal(dv["S1"][1],dv["B0"][1])
            np.testing.assert_array_equal(dv["C2"][1],dv["B0"][1])

    def test_strict_token_audit_rejects_before_model_truncation(self):
        class Tokenizer:
            def __call__(self,texts,pairs=None,**kwargs): return {"input_ids":[[1]*513 for _ in texts]}
        output=io.StringIO()
        with self.assertRaisesRegex(ValueError,"token limit"):
            experiment.audit_inputs(Tokenizer(),["原文"],["U"],512,output,stage="test")
        self.assertTrue(json.loads(output.getvalue())["rejected"])
        self.assertFalse(json.loads(output.getvalue())["truncation_allowed"])

    def test_same_real_model_input_shared_across_arms_but_changed_text_rescored(self):
        class Scorer:
            def __init__(self): self.calls=[]
            def rerank(self,query,candidates,mapping,corpus,qid):
                self.calls.append([(r["unit_id"],mapping[r["unit_id"]]["text"]) for r in candidates])
                return [dict(unit_id=r["unit_id"],score=float(len(mapping[r["unit_id"]]["text"]))) for r in candidates]
        model, pool, ledger = Scorer(), {}, io.StringIO()
        query,candidates = dict(query_id="Q",text="误导"), [dict(unit_id="U1",rank=1,score=1.0)]
        kwargs = dict(manifest_sha="m",runtime={"model":"real-identical"},inputs={"sha":"a"},pool=pool,pool_handle=ledger)
        one,_ = experiment.score_candidates(model,query,candidates,self.unit_map,"B0",**kwargs)
        two,stats = experiment.score_candidates(model,query,candidates,self.unit_map,"W4",**kwargs)
        self.assertEqual(one,two)
        self.assertEqual(stats["reused_units"],1)
        changed = dict(self.unit_map,U1=dict(self.units[0],text="不同模型输入"))
        experiment.score_candidates(model,query,candidates,changed,"S1",**kwargs)
        self.assertEqual(len(model.calls),2)
        rows = [json.loads(line) for line in ledger.getvalue().splitlines()]
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[1]["provenance"]["kind"],"same_run_exact_model_input_shared")

    def test_cards_need_two_verified_sources_and_whole_review_binding(self):
        card = dict(card_id="K1",title="误导",mechanism="候选误导机制",conditions=["出现虚假表述"],boundary_notes="仍需核查",
                    limitations="两份来源",retrieval_text="销售误导候选机制",status="candidate_model",human_approved=False,
                    supports=[dict(file_id=u["file_id"],unit_id=u["unit_id"],source_sha256=u["source_sha256"],
                                   quote=u["text"],span=u["source_spans"][0],role="support") for u in self.units])
        review = dict(card_id="K1",status="approved_model_review",mechanism_cards_sha256="c"*64,
                      row_sha256=row_sha(card),reason="逐字源核验",human_approved=False)
        validate = lambda c,r: experiment.validate_mechanism_cards([c],[r],self.unit_map,self.sources,"c"*64,minimum=1)
        self.assertEqual(validate(card,review),[card])
        bad=copy.deepcopy(card);bad["supports"][1]["unit_id"]="ILLEGAL"
        with self.assertRaises(ValueError): validate(bad,dict(review,row_sha256=row_sha(bad)))
        with self.assertRaisesRegex(ValueError,"review"): validate(card,dict(review,mechanism_cards_sha256="d"*64))

    def test_support_quote_may_restore_truncated_parent_but_cannot_recall_disjoint_unit(self):
        supports=[dict(file_id=u["file_id"],unit_id=u["unit_id"],source_sha256=u["source_sha256"],
                       quote=u["text"],span=u["source_spans"][0],role="support") for u in self.units]
        source=self.sources["F1"]
        supports[0].update(quote=source[:8],span=dict(start=0,end=8))
        card=dict(card_id="K",title="误导",mechanism="核查机制",conditions="需要对照原文",boundary_notes="仅此原文",
                  limitations="局部片段",retrieval_text="误导",status="candidate_model",human_approved=False,supports=supports)
        review=dict(card_id="K",status="approved_model_review",mechanism_cards_sha256="c"*64,
                    row_sha256=row_sha(card),reason="合成源交集检查",human_approved=False)
        outcome=None
        try: outcome=experiment.validate_mechanism_cards([card],[review],self.unit_map,self.sources,"c"*64,minimum=1)
        except ValueError as exc: outcome=str(exc)
        self.assertEqual(outcome,[card])
        quote="乙销售违规。"
        supports[0].update(quote=quote,span=dict(start=source.index(quote),end=source.index(quote)+len(quote)))
        review["row_sha256"]=row_sha(card)
        with self.assertRaisesRegex(ValueError,"identify recalled unit"):
            experiment.validate_mechanism_cards([card],[review],self.unit_map,self.sources,"c"*64,minimum=1)

    def test_card_route_uses_similarity_top2_and_deduplicates_supported_ids(self):
        cards=[dict(card_id="K1",supports=[dict(unit_id="U1"),dict(unit_id="U2")]),
               dict(card_id="K2",supports=[dict(unit_id="U2")]),
               dict(card_id="K3",supports=[dict(unit_id="U1")])]
        rows,selected=experiment.mechanism_route(cards,[0.2,0.9,0.8],self.unit_map,card_top_k=2)
        self.assertEqual([r["card_id"] for r in selected],["K2","K3"])
        self.assertEqual([r["unit_id"] for r in rows],["U2","U1"])
        bad=copy.deepcopy(cards);bad[1]["supports"][0]["unit_id"]="ILLEGAL"
        with self.assertRaises(ValueError): experiment.mechanism_route(bad,[0.2,0.9,0.8],self.unit_map)
        with self.assertRaises(ValueError): experiment.mechanism_route(cards,[0.2,0.9,0.8],self.unit_map,card_top_k=5)

    def test_five_arm_dimensions_are_frozen_and_m3_never_reranks_cards(self):
        self.assertEqual(list(experiment.ARMS),["B0","S1","C2","W4","M3"])
        routes=[[dict(unit_id="U1",rank=1,score=2.0)],[dict(unit_id="U2",rank=1,score=1.0)]]
        cardroute=[dict(unit_id="U2",rank=1,score=0.9)]
        self.assertEqual(experiment.ARMS["W4"]["weights"],[2,1])
        self.assertEqual(experiment.ARMS["M3"]["weights"],[1,1,1])
        for arm in experiment.ARMS:
            self.assertEqual(experiment.ARMS[arm]["depth"],100)
        adapter=experiment.frozen_e04().frozen_modules()[1]
        record=experiment.build_record(dict(query_id="Q",text="误导"),"M3",routes+[cardroute],
            {"U1":0.5,"U2":0.8},self.unit_map,adapter,timing={},provenance={})
        self.assertEqual(record["files"][0]["indexed_text"],self.unit_map["U2"]["text"])
        self.assertEqual(set(r["unit_id"] for r in record["stages"]["rerank"]),{"U1","U2"})
        self.assertEqual(record["configuration"]["card_top_k"],2)

    def test_exact_42_queries_split_new20_replay22_and_no_old_text_as_new(self):
        replay={"R"+str(i):dict(query_id="R"+str(i),text="old"+str(i),group="g",query_role="risk",replay_origin="old") for i in range(22)}
        rows=list(replay.values())+[dict(query_id="N"+str(i),text="new"+str(i),group="g",query_role="risk" if i<10 else "boundary",replay_origin=None) for i in range(20)]
        split=experiment.validate_queries(rows,replay)
        self.assertEqual(split,{"new":20,"replay":22,"new_risk":10,"new_boundary":10})
        rows[-1]=dict(rows[-1],text="old1")
        with self.assertRaises(ValueError): experiment.validate_queries(rows,replay)

    def test_actual_frozen_query42_and_legacy_delivery_manifest_contract(self):
        replay={}
        for phase in ("dev","confirmation"):
            for query in experiment.read_jsonl(experiment.E04_OUT/(phase+"_queries.jsonl")):
                query=dict(query)
                query.setdefault("query_role","boundary" if query["group"]=="boundary_condition_change" else "risk")
                replay[query["query_id"]]=query
        rows=experiment.read_jsonl(experiment.OUT/"queries.jsonl")
        self.assertEqual(experiment.validate_queries(rows,replay)["new"],20)
        lookup=getattr(experiment,"delivery_file_hashes",None)
        self.assertIsNotNone(lookup,"legacy manifest lookup helper missing")
        delivery=experiment.read_json(experiment.E04_OUT/"delivery_manifest.json")
        hashes=lookup(delivery)
        target=experiment.E04_OUT/"dev_queries.jsonl"
        self.assertEqual(hashes[target.relative_to(experiment.ROOT).as_posix()],experiment.sha_file(target))

    def test_actual_source_candidates_pass_structure_with_rejected_reviews_only(self):
        # This check neither creates nor implies model semantic approval.
        source_rows=[]
        for name in ("prefix_inputs_p1.jsonl","prefix_inputs_p2.jsonl"):
            source_rows+=experiment.read_jsonl(experiment.E02_OUT/name)
        units={r["unit"]["unit_id"]:r["unit"] for r in source_rows}
        sources={r["file_id"]:r["full_source_text"] for r in source_rows}
        cohort=experiment.read_json(experiment.E02_OUT/"cohort.json")
        path=experiment.OUT/"scope_units.jsonl"
        rows=experiment.read_jsonl(path)
        reviews=[dict(unit_id=r["unit_id"],status="rejected",human_approved=False,reason="synthetic structural check only",
                      source_sha256=r["source_sha256"],row_sha256=row_sha(r),scope_units_sha256=experiment.sha_file(path)) for r in rows]
        self.assertEqual(experiment.validate_scope_units(rows,reviews,cohort,units,sources,experiment.sha_file(path)),{})
        path=experiment.OUT/"mechanism_cards.jsonl"
        cards=experiment.read_jsonl(path)
        reviews=[dict(card_id=r["card_id"],status="rejected",human_approved=False,reason="synthetic structural check only",
                      row_sha256=row_sha(r),mechanism_cards_sha256=experiment.sha_file(path)) for r in cards]
        self.assertEqual(experiment.validate_mechanism_cards(cards,reviews,units,sources,experiment.sha_file(path),minimum=0),[])

    def test_execution_freeze_validates_all_required_file_hashes(self):
        with tempfile.TemporaryDirectory(dir=HERE) as name:
            path=Path(name)/"input.jsonl";path.write_text("input",encoding="utf-8")
            freeze=Path(name)/"freeze.json"
            freeze.write_text(json.dumps({"files_sha256":{str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest()}}),encoding="utf-8")
            bound=experiment.validate_freeze(freeze,[path])
            self.assertEqual(len(bound),2)
            path.write_text("mutated",encoding="utf-8")
            with self.assertRaises(ValueError): experiment.validate_freeze(freeze,[path])


if __name__ == "__main__": unittest.main()
