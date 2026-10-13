"""Behavioral regressions for extractive background and unbiased fresh pools."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    import evaluate as E
except ModuleNotFoundError:
    E = None

SOURCE = "甲机构。其销售人员承诺合同以外的赠品。乙机构另有独立事项。"


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def claim(quote="甲机构", label="文书主体"):
    start = SOURCE.index(quote)
    return {"label": label, "quote": quote, "span": {"start": start, "end": start + len(quote)}, "link_reason": "原文同段身份，仅为测试"}


def hit(with_prefix=True):
    raw = "其销售人员承诺合同以外的赠品。"
    start = SOURCE.index(raw)
    span = {"start": start, "end": start+len(raw)}
    h = {"file_id": "F1", "unit_id": "structured:F1:U1", "rank": 1, "score": 0.5,
         "text": raw, "source_text": raw, "source_spans": [span], "source_segments": [{"span": span, "text": raw}], "prefix": ""}
    if with_prefix:
        c = claim()
        prefix = c['label']+'：'+c['quote']
        h.update(prefix=prefix, prefix_claims=[c], prefix_source_unit_id=h['unit_id'],
                 prefix_profile="E02-extractive-v1", prefix_review_status="approved_model_review", base_context_text=raw)
        h['text'] = "【背景说明（原文摘录，候选）】\n"+prefix+"\n\n【原文片段】\n"+raw
    return h


def query():
    return {"query_id": "Q1", "text": "合同外赠品需要核查什么", "group": "risk", "query_role": "risk",
            "mechanism_description": "DO_NOT_LEAK_AUTHOR", "expected_help": "DO_NOT_LEAK_TARGET",
            "anchor_evidence": [{"file_id": "F1", "quote": "SECRET_ANCHOR"}], "known_positive_file_ids": ["F1"]}


def result(arm="P1", prefixed=True):
    q = query()
    return {"query_id": q['query_id'], "text": q['text'], "arm": arm, "corpus": "structured", "files": [hit(prefixed)], "timing": {}}


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(E, "E02 evaluator has not been implemented")

    def test_extract_accepted_and_original_segments_unchanged(self):
        h = hit()
        c = E.validate_context(h, SOURCE)
        self.assertEqual(c['text'], h['text'])
        self.assertEqual(c['source_segments'], h['source_segments'])
        self.assertEqual(c['prefix_claims'], h['prefix_claims'])

    def test_plain_v2_still_accepted(self):
        h = hit(False)
        self.assertEqual(E.validate_context(h, SOURCE)['text'], h['text'])

    def test_wrong_prefix_span_is_rejected(self):
        h = hit(); h['prefix_claims'][0]['span']['start'] += 1
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)

    def test_extra_unquoted_prefix_assertion_rejected(self):
        h = hit(); h['prefix'] += "\n该个人亲自实施"
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)

    def test_invalid_label_rejected(self):
        h = hit(); h['prefix_claims'][0]['label'] = "经人工验收合法"
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)

    def test_prefix_of_another_winner_unit_rejected(self):
        h = hit(); h['prefix_source_unit_id'] = 'structured:F1:OTHER'
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)

    def test_pending_review_not_accepted(self):
        h = hit(); h['prefix_review_status'] = 'pending'
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)

    def test_rendered_text_must_exactly_match_prefix_and_base(self):
        h = hit(); h['text'] += '多加的结论'
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)

    def test_original_context_cannot_be_fabricated(self):
        h = hit(); h['base_context_text'] += '虚构条件'
        with self.assertRaises(ValueError): E.validate_context(h, SOURCE)

    def test_roundtrip_pool_does_not_need_unblinded_winner_id(self):
        c = E.validate_context(hit(), SOURCE)
        self.assertNotIn('prefix_source_unit_id', c)
        self.assertEqual(E.validate_context(c, SOURCE)['context_id'], c['context_id'])

    def test_blind_pool_removes_author_instructions_anchors_and_ranks(self):
        q = query()
        pool, provenance = E.build_pool({'Q1': q}, [result()], {'F1': {'full_text': SOURCE, 'text_sha256': digest(SOURCE)}})
        p = next(iter(pool.values()))
        encoded = json.dumps(p,ensure_ascii=False)
        for key in ('query_task','expected_help','DO_NOT_LEAK','SECRET_ANCHOR','known_positive','"arm"','"rank"','"score"','"unit_id"','prefix_source_unit_id'):
            self.assertNotIn(key, encoded)
        self.assertEqual(provenance[0]['unit_id'], hit()['unit_id'])

    def test_prefix_quote_is_visible_and_source_exact(self):
        c = E.validate_context(hit(), SOURCE)
        j = {'context_id':c['context_id'],'help_grade':2,'evidence_quote':'甲机构','reason':'测试引用','misleading_risk':False}
        E.validate_context_judgment(j,c,SOURCE)
        j['evidence_quote']='文书主体：甲机构'
        with self.assertRaises(ValueError): E.validate_context_judgment(j,c,SOURCE)

    def test_new_output_guard_rejects_e04_and_root_itself(self):
        with self.assertRaises(ValueError): E.check_output_dir(HERE.parents[1]/'outputs/FinRisk_E04小批量实验_20261012/evaluation')
        with self.assertRaises(ValueError): E.check_output_dir(HERE.parents[1]/'outputs/FinRisk_E02小批量实验_20261013')

    def test_reused_old_semantic_judgments_are_not_allowed(self):
        with self.assertRaises(ValueError): E.prepare('q','r','out',reuse_pool='old',reuse_judgment_paths=['old'])

    def test_fixed5_denominator_and_missing_grade_not_zero(self):
        q=query(); q.pop('known_positive_file_ids')
        results=[result('P0',False),result('P1',True),result('P2',True)]
        pool,_=E.build_pool({'Q1':q},results,{'F1':{'full_text':SOURCE,'text_sha256':digest(SOURCE)}})
        p=next(iter(pool.values()))
        j={'pair_id':p['pair_id'],'help_grade':2,'help_type':'support','mechanism_match':'same','conditions_match':'compatible',
           'source_quote':'合同以外的赠品','reason':'测试','limitations':['测试夹具'],'misleading_risk':False,
           'contexts':[{'context_id':c['context_id'],'help_grade':2,'evidence_quote':'合同以外的赠品','reason':'测试','misleading_risk':False} for c in p['contexts']]}
        summary,_=E.compute_metrics({'Q1':q},results,pool,{p['pair_id']:j})
        self.assertTrue(all(r['context_useful_at5']==0.2 for r in summary['metrics']))
        self.assertIn('回放', ' '.join(summary['limitations']))
        j['contexts'].pop()
        with self.assertRaises(ValueError): E.compute_metrics({'Q1':q},results,pool,{p['pair_id']:j})

    def test_real_prepare_summarize_roundtrip_keeps_fresh_bindings(self):
        root = HERE.parents[1]/'outputs/FinRisk_E02小批量实验_20261013'
        with tempfile.TemporaryDirectory(dir=root) as td:
            base=Path(td)
            def save(name, values):
                path=base/name
                path.write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in values),encoding='utf-8')
                return path
            qp=save('q.jsonl',[query()])
            rp=save('r.jsonl',[result('P0',False),result('P1',True),result('P2',True)])
            sp=save('s.jsonl',[{'official_file_id':'F1','full_text':SOURCE,'text_sha256':digest(SOURCE),'source_sha256':digest(SOURCE)}])
            phase=base/'phase'
            prepared=E.prepare(qp,[rp],phase,sources_path=sp)
            self.assertEqual(prepared['reused_files'],0)
            pool=E.read_rows(phase/'blind_judgment_pool.jsonl')
            self.assertNotIn('query_task',pool[0])
            incomplete=E.summarize(qp,[rp],phase,[],sources_path=sp)
            self.assertEqual(incomplete['status'],'incomplete')
            p=pool[0]
            j={'pair_id':p['pair_id'],'help_grade':2,'help_type':'support','mechanism_match':'same','conditions_match':'compatible',
               'source_quote':'合同以外的赠品','reason':'测试','limitations':['夹具'],'misleading_risk':False,
               'contexts':[{'context_id':c['context_id'],'help_grade':2,'evidence_quote':'合同以外的赠品','reason':'测试','misleading_risk':False} for c in p['contexts']]}
            jp=save('j.jsonl',[j])
            complete=E.summarize(qp,[rp],phase,[jp],sources_path=sp)
            self.assertEqual(complete['status'],'complete')
            self.assertIn(str((HERE/'evaluate.py').resolve()),complete['input_sha256'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
