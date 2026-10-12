"""Source integrity, cache binding, blind pending pool and metrics fixtures."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name('eval_v2.py')
spec = importlib.util.spec_from_file_location('eval_v2', MODULE)
ev = importlib.util.module_from_spec(spec) if MODULE.exists() else None
if ev is not None:
    spec.loader.exec_module(ev)


class EvalTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(ev, 'V2 evaluation implementation is missing')
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent, prefix='eval_fixture_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        (self.repo / 'data/sources').mkdir(parents=True)
        self.body = '主体甲。违规事实。\n中间信息。\n限定条件。答辩。'
        self.queries = [{'query_id':f'Q{i:03}', 'text':f'查询{i}', 'group':'fixture',
                         'known_positive_file_ids':['F1']} for i in range(1,51)]
        self.qpath = self.write('queries.jsonl', self.queries)
        self.write('repo/data/sources/part-1.jsonl', [
            {'file_id':f'F{i}', 'full_text':self.body, 'text_sha256':ev.text_sha(self.body)}
            for i in range(1,7)])
        self.hits = [self.hit(f'F{i}', i) for i in range(1,6)]
        self.rows = [{'query_id':q['query_id'], 'text':q['text'], 'corpus':'structured',
                      'arm':'custom_arm', 'files':copy.deepcopy(self.hits)} for q in self.queries]
        self.rpath = self.write('results.jsonl', self.rows)
        self.review = self.root / 'review'

    def write(self, name, rows):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
        return path

    def hit(self, fid, rank):
        texts = ['主体甲。违规事实。','限定条件。答辩。']
        spans = [{'start':self.body.index(t),'end':self.body.index(t)+len(t)} for t in texts]
        return {'file_id':fid,'unit_id':f'{fid}:u', 'rank':rank, 'prefix':'',
                'source_text':''.join(texts), 'text':ev.GAP.join(texts),
                'source_spans':spans, 'source_segments':[{'text':t,'span':s} for t,s in zip(texts,spans)]}

    def build(self, **kw):
        return ev.build_pool({'v2_fixture':self.rpath}, self.qpath, self.repo, self.review, **kw)

    def judgment(self, p, grade=2):
        return {'pair_id':p['pair_id'],'help_grade':grade,'help_type':'support',
                'mechanism_match':'same','conditions_match':'compatible','source_quote':'违规事实',
                'reason':'原文直接说明风险机制','limitations':[],'misleading_risk':False,
                'contexts':[{'context_id':c['context_id'],'help_grade':grade,'evidence_quote':'违规事实',
                             'reason':'返回上下文直接载明行为','misleading_risk':False} for c in p['contexts']]}

    def test_multisegment_pool_blind_and_pending(self):
        manifest = self.build()
        pool = ev.read_rows(self.review/'blind_judgment_pool.jsonl')
        self.assertEqual(len(pool),250)
        self.assertEqual(manifest['top5_slots'],250)
        p = pool[0]
        self.assertEqual(p['pair_id'],ev.pair_id(p['query_id'],p['file_id']))
        self.assertEqual(p['contexts'][0]['context_id'],ev.context_id(self.hits[0]['text']))
        self.assertEqual(p['contexts'][0]['source_text'],self.hits[0]['source_text'])
        for row in pool:
            self.assertFalse({'variant','arm','rank','known_positive_file_ids'} & row.keys())
        pending = sum((ev.read_rows(self.review/f'judgment_part_{i}.jsonl') for i in range(1,4)),[])
        self.assertEqual(len(pending),250)
        self.assertTrue(all(p['needs_file_judgment'] for p in pending))

    def test_bad_segment_span_or_marker_rejected(self):
        for field,value in [('source_text','invented'),('text',self.hits[0]['source_text'])]:
            rows=copy.deepcopy(self.rows);rows[0]['files'][0][field]=value
            self.rpath=self.write('bad.jsonl',rows)
            with self.assertRaises(ValueError):self.build()
        rows=copy.deepcopy(self.rows);rows[0]['files'][0]['source_segments'][0]['span']['end']+=1
        self.rpath=self.write('bad.jsonl',rows)
        with self.assertRaises(ValueError):self.build()

    def test_v1_rule_still_requires_entire_source_text_each_span(self):
        h={'file_id':'F1','unit_id':'v1','rank':1,'text':'前缀\n违规事实', 'prefix':'前缀',
           'source_text':'违规事实', 'source_spans':[{'start':4,'end':8}]}
        c=ev.validate_context(h,self.body)
        self.assertEqual(c['text'],h['text'])
        h['source_spans'].append({'start':0,'end':4})
        with self.assertRaises(ValueError):ev.validate_context(h,self.body)

    def test_group_query_rank_and_duplicate_integrity(self):
        mutations=[lambda r:r.pop(), lambda r:r[0].update(text='changed'),
                   lambda r:r[0]['files'][0].update(rank=2),
                   lambda r:r[0]['files'].__setitem__(1,copy.deepcopy(r[0]['files'][0]))]
        for mutate in mutations:
            rows=copy.deepcopy(self.rows);mutate(rows);self.rpath=self.write('bad.jsonl',rows)
            with self.assertRaises(ValueError):self.build()

    def test_cache_exact_file_and_context_pending_only_changed_context(self):
        self.build();pool=ev.read_rows(self.review/'blind_judgment_pool.jsonl')
        cp=self.write('cached_pool.jsonl',pool);cj=self.write('cached_judgments.jsonl',[self.judgment(p) for p in pool])
        # Cache can contain V2 too; exact text and source/query bindings are authoritative.
        rows=copy.deepcopy(self.rows)
        for r in rows:
            h=r['files'][0];h['text']='违规事实';h['source_text']='违规事实';h['source_spans']=[{'start':4,'end':8}]
            h['source_segments']=[{'text':'违规事实','span':{'start':4,'end':8}}]
        self.rpath=self.write('new_results.jsonl',rows)
        self.build(cache_pool=cp,cache_judgments=cj,cache_queries=self.qpath)
        pending=sum((ev.read_rows(self.review/f'judgment_part_{i}.jsonl') for i in range(1,4)),[])
        self.assertEqual(len(pending),50)
        self.assertTrue(all(not p['needs_file_judgment'] for p in pending))
        self.assertTrue(all('help_grade' not in p for p in pending))
        self.assertTrue(all(len(p['contexts'])==1 for p in pending))
        minimal=[{'pair_id':p['pair_id'],'contexts':self.judgment(p)['contexts']} for p in pending]
        new=self.write('new_judgments.jsonl',minimal)
        merged=ev.merge_judgments(self.review,[new],self.root/'merged')
        self.assertEqual(len(merged),250)
        self.assertTrue(all(p['help_grade']==2 for p in merged))

    def test_cache_query_bytes_changed_disables_reuse(self):
        self.build();pool=ev.read_rows(self.review/'blind_judgment_pool.jsonl')
        cp=self.write('cached_pool.jsonl',pool);cj=self.write('cache.jsonl',[self.judgment(p) for p in pool])
        cq=self.write('cache_queries.jsonl',self.queries)
        cq.write_text(cq.read_text(encoding='utf-8')+'\n',encoding='utf-8')
        self.build(cache_pool=cp,cache_judgments=cj,cache_queries=cq)
        self.assertEqual(len(ev.read_rows(self.review/'cached_judgments.jsonl')),0)

    def test_invalid_quotes_missing_duplicate_forged_judgments_fail(self):
        self.build();pool=ev.read_rows(self.review/'blind_judgment_pool.jsonl')
        good=[self.judgment(p) for p in pool]
        cases=[good[:-1],good+[copy.deepcopy(good[0])]]
        bad=copy.deepcopy(good);bad[0]['pair_id']='Jfake';cases.append(bad)
        for field,value in [('source_quote',''),('source_quote','编造证据')]:
            bad=copy.deepcopy(good);bad[0][field]=value;cases.append(bad)
        bad=copy.deepcopy(good);bad[0]['contexts'][0]['evidence_quote']='前缀';cases.append(bad)
        bad=copy.deepcopy(good);bad[0]['contexts']=[];cases.append(bad)
        for rows in cases:
            path=self.write('judgments.jsonl',rows)
            with self.assertRaises(ValueError):ev.merge_judgments(self.review,[path],self.root/'metrics')

    def test_complete_metrics_arbitrary_variants_groups_and_no_global_recall(self):
        self.build();pool=ev.read_rows(self.review/'blind_judgment_pool.jsonl')
        path=self.write('judgments.jsonl',[self.judgment(p) for p in pool])
        out=self.root/'metrics'
        ev.merge_judgments(self.review,[path],out)
        summary=ev.compute_metrics(self.review,out/'validated_judgments.jsonl',out)
        m=summary['metrics'][0]
        self.assertEqual((m['variant'],m['corpus'],m['arm']),('v2_fixture','structured','custom_arm'))
        self.assertEqual(m['queries'],50)
        self.assertEqual(m['useful_at5'],1)
        self.assertEqual(m['context_useful_at5'],1)
        self.assertEqual(m['pool_conditional_ndcg_at5'],1)
        self.assertEqual(m['known_source_hit_at20'],1)
        self.assertEqual(m['known_source_rr_at20'],1)
        self.assertEqual(summary['human_judgments'],0)
        self.assertNotIn('global_recall',json.dumps(summary).lower())
        self.assertEqual(len(ev.read_rows(out/'per_query_metrics.jsonl')),50)

    def test_tampered_input_or_provenance_rejected(self):
        self.build();pool=ev.read_rows(self.review/'blind_judgment_pool.jsonl')
        path=self.write('judgments.jsonl',[self.judgment(p) for p in pool]);out=self.root/'merged'
        ev.merge_judgments(self.review,[path],out)
        prov=self.review/'judgment_provenance.jsonl';rows=ev.read_rows(prov);rows[0]['unit_id']='tampered'
        ev.write_rows(prov,rows)
        with self.assertRaises(ValueError):ev.compute_metrics(self.review,out/'validated_judgments.jsonl',out)

    def test_source_hash_changed_requires_new_file_judgment(self):
        self.build();pool=ev.read_rows(self.review/'blind_judgment_pool.jsonl')
        cp=self.write('cached_pool.jsonl',pool);cj=self.write('cache.jsonl',[self.judgment(p) for p in pool])
        self.write('repo/data/sources/part-1.jsonl',[
            {'file_id':f'F{i}','full_text':self.body+'新内容','text_sha256':ev.text_sha(self.body+'新内容')}
            for i in range(1,7)])
        self.build(cache_pool=cp,cache_judgments=cj,cache_queries=self.qpath)
        pending=sum((ev.read_rows(self.review/f'judgment_part_{i}.jsonl') for i in range(1,4)),[])
        self.assertEqual(len(pending),250)
        self.assertTrue(all(p['needs_file_judgment'] for p in pending))

    def test_metrics_include_and_verify_original_judgment_input_hashes(self):
        self.build();pool=ev.read_rows(self.review/'blind_judgment_pool.jsonl')
        jp=self.write('judgments.jsonl',[self.judgment(p) for p in pool]);out=self.root/'metrics'
        ev.merge_judgments(self.review,[jp],out)
        summary=ev.compute_metrics(self.review,out/'validated_judgments.jsonl',out)
        self.assertIn(str(jp.resolve()),summary['input_sha256'])
        jp.write_text(jp.read_text(encoding='utf-8')+'\n',encoding='utf-8')
        with self.assertRaises(ValueError):ev.compute_metrics(self.review,out/'validated_judgments.jsonl',out)

    def test_multiple_variants_sparse_results_zero_ideal_and_known_positive_denominator(self):
        rows=copy.deepcopy(self.rows)
        for r in rows:r['files']=r['files'][:1]
        second=self.write('other.jsonl',rows)
        ev.build_pool({'v1':self.rpath,'v2':second},self.qpath,self.repo,self.review)
        pool=ev.read_rows(self.review/'blind_judgment_pool.jsonl')
        jp=self.write('judgments.jsonl',[self.judgment(p,grade=0) for p in pool]);out=self.root/'metrics'
        ev.merge_judgments(self.review,[jp],out)
        summary=ev.compute_metrics(self.review,out/'validated_judgments.jsonl',out)
        self.assertEqual(len(summary['metrics']),2)
        for m in summary['metrics']:
            self.assertIsNone(m['pool_conditional_ndcg_at5'])
            self.assertEqual(m['pool_conditional_ndcg_at5_n'],0)
            self.assertEqual(m['useful_at5'],0)

    def test_context_grade_cannot_quote_gap_marker_or_concat_noncontinuous_source(self):
        self.build();pool=ev.read_rows(self.review/'blind_judgment_pool.jsonl')
        for quote in [ev.GAP,'违规事实。限定条件。']:
            rows=[self.judgment(p) for p in pool];rows[0]['contexts'][0]['evidence_quote']=quote
            jp=self.write('judgments.jsonl',rows)
            with self.assertRaises(ValueError):ev.merge_judgments(self.review,[jp],self.root/'metrics')


if __name__=='__main__':unittest.main()
