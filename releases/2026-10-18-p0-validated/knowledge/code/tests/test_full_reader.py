import hashlib
import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK))


def canonical(v):
    return hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def textsha(v):
    return hashlib.sha256(v.encode()).hexdigest()


class FullReaderTests(unittest.TestCase):
    def setUp(self):
        temp_root=WORK/'full_reader_task'/'test_temp'
        temp_root.mkdir(parents=True,exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=temp_root)
        self.root = Path(self.tmp.name)
        self.versions = {k:k+'-fixture' for k in ('content','projection','articles','rules','scope')}
        self.draft = dict(file_id='F1', role='responsible_person', unresolved=['未核'])
        self.text = '甲公司。乙责任人。当前事实未核。'
        self.unit = dict(unit_id='raw:F1:stable', file_id='F1', candidate_sha256=canonical(self.draft),
                         source_sha256=textsha(self.text), source_spans=[dict(start=4,end=9)],
                         parent_source_spans=[dict(start=0,end=len(self.text))], evidence_ambiguous=True,
                         case_ids=['case:stable'], behavior_ids=['behavior:stable'],
                         associations=[dict(actor_role='responsible_person', quote=self.text[4:9], quote_source_spans=[dict(start=4,end=9)], current_fact_verified=False)])
        self.data = dict(structured=[], raw=[self.unit],
                         documents=[dict(official_file_id='F1', full_text=self.text, source_sha256=textsha(self.text), text_sha256=textsha(self.text), human_review_status='pending')],
                         candidates=[dict(file_id='F1', draft=self.draft, effective_draft_json_sha256=canonical(self.draft))],
                         rebinds=[], articles=[], legal_sources=[], scope_units=[], scope_sources=[], scope_spans=[])

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, name='bundle'):
        self.assertIsNotNone(importlib.util.find_spec('full_reader'),'full_reader API has not been implemented')
        from full_reader import build_index
        files = {}
        for kind, records in self.data.items():
            p=self.root/(kind+'.jsonl')
            p.write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in records), encoding='utf-8')
            files[kind]=p
        self.bundle=self.root/name
        self.lock=build_index(self.bundle, input_files=files, versions=self.versions)
        return self.open()

    def open(self, **kw):
        from full_reader import FullKnowledgeReader
        return FullKnowledgeReader(self.bundle, expected_manifest_sha256=self.lock['manifest_sha256'], expected_versions=kw.pop('expected_versions',self.versions), **kw)

    def test_public_reader_is_available(self):
        spec=importlib.util.find_spec('full_reader')
        self.assertIsNotNone(spec, 'full_reader API has not been implemented')

    def test_lazy_mapping_read_layers_and_original_records(self):
        with self.build() as r:
            self.assertIsInstance(r.units, Mapping)
            self.assertNotIsInstance(r.units, dict)
            self.assertEqual(r.units[self.unit['unit_id']],self.unit)
            self.assertEqual(r.documents['F1'],self.data['documents'][0])
            hit=r.read(self.unit['unit_id'])
            self.assertEqual(hit['text'],self.text[4:9])
            self.assertEqual(hit['associations'],self.unit['associations'])
            self.assertFalse(hit['human_approved'])
            self.assertIsNone(hit['runtime_relevance'])
            self.assertEqual(hit['attribution_status'],'candidate_associations_preserved_not_current_query_fact')
            self.assertEqual(r.read(self.unit['unit_id'],layer='extended')['text'],self.text)
            self.assertEqual(r.read_span(hit['segments'][0]['span_id']),hit['segments'][0])
            hit['associations'].clear()
            self.assertTrue(r.read(self.unit['unit_id'])['associations'])
            with self.assertRaises(ValueError):r.read('unknown')
            with self.assertRaises(ValueError):r.read(self.unit['unit_id'],layer='supplement')
            with self.assertRaises(ValueError):r.read_span('unknown')
            with self.assertRaises(ValueError):r.read(self.unit['unit_id'],layer='bad')

    def test_pinned_versions_manifest_and_database_tampering_rejected(self):
        self.build().close()
        with self.assertRaises(ValueError):self.open(expected_versions=dict(self.versions,scope='wrong'))
        from full_reader import FullKnowledgeReader
        with self.assertRaises(ValueError):FullKnowledgeReader(self.bundle,expected_manifest_sha256='0'*64,expected_versions=self.versions)
        db=self.bundle/'knowledge.sqlite'
        with db.open('ab') as f:f.write(b'tampered')
        with self.assertRaises(ValueError):self.open()

    def test_unknown_duplicate_and_invalid_source_span_rejected_at_build(self):
        self.data['raw'].append(dict(self.unit))
        with self.assertRaises(ValueError):self.build()
        self.data['raw'].pop(); self.unit['source_spans']=[dict(start=True,end=9)]
        with self.assertRaises(ValueError):self.build('second')

    def test_stale_binding_needs_exact_reviewed_metadata_patch(self):
        self.unit['candidate_sha256']='old'
        with self.assertRaisesRegex(ValueError,'stale'):self.build()
        self.data['rebinds']=[dict(unit_id=self.unit['unit_id'],file_id='F1',expected_baseline_draft_sha256='old',current_effective_draft_sha256=canonical(self.draft),requires_versions=self.versions,allowed_changed_fields=['candidate_sha256'],ranking_text_changed=False,preserve_stable_case_behavior_IDs=True)]
        with self.build('second') as r:self.assertTrue(r.read(self.unit['unit_id'])['binding_repaired_by_metadata_overlay'])
        self.data['rebinds'][0]['ranking_text_changed']=True
        with self.assertRaisesRegex(ValueError,'rebind'):self.build('third')

    def test_source_candidate_and_association_invariants_rejected(self):
        self.data['candidates'][0]['draft']['file_id']='F2'
        with self.assertRaisesRegex(ValueError,'draft'):self.build()
        self.data['candidates'][0]['draft']['file_id']='F1'
        self.unit['associations'][0]['quote']='invented'
        with self.assertRaisesRegex(ValueError,'quotation'):self.build('second')

    def test_bounded_cache_readonly_connection_and_portable_bundle(self):
        with self.build() as r:
            for _ in range(100):r.read(self.unit['unit_id'])
            self.assertLessEqual(r.cache_info()['entries'],r.cache_info()['max_entries'])
            self.assertLessEqual(r.cache_info()['bytes'],r.cache_info()['max_bytes'])
            with self.assertRaises(sqlite3.OperationalError):r.connection.execute('CREATE TABLE forbidden(x)')
        shutil.copytree(self.bundle,self.root/'moved')
        self.bundle=self.root/'moved'
        before={p.name for p in self.bundle.iterdir()}
        with self.open() as r:self.assertEqual(r.read(self.unit['unit_id'])['file_id'],'F1')
        self.assertEqual(before,{p.name for p in self.bundle.iterdir()})

    def test_scope_registered_spans_and_legal_article_preserve_contract(self):
        scope_span=dict(span_id='SCOPE:1',source_id='S1',start=4,end=9,text=self.text[4:9],text_sha256=textsha(self.text[4:9]),source_sha256=textsha(self.text),layer='hit')
        self.data['scope_sources']=[dict(source_id='S1',text=self.text,source_sha256=textsha(self.text))]
        self.data['scope_spans']=[scope_span]
        self.data['scope_units']=[dict(unit_id=self.unit['unit_id'],source_id='S1',source_sha256=textsha(self.text),layers=dict(hit=['SCOPE:1'],extended=[],supplement=[]))]
        self.data['legal_sources']=[dict(source_id='LAW1',text='法条')]
        self.data['articles']=[dict(article_id='A1',source_id='LAW1',start=0,end=2,text='法条',text_sha256=textsha('法条'),original_source_text_sha256=textsha('法条'))]
        with self.build() as r:
            self.assertEqual(r.read_span('SCOPE:1'),scope_span)
            self.assertTrue(r.read(self.unit['unit_id'])['scope_reviewed'])
            self.assertEqual(r.read(self.unit['unit_id'],layer='supplement')['segments'],[])
            self.assertFalse(r.read_article('A1')['current_business_fact_proof'])
        scope_span['text']='篡改'
        with self.assertRaises(ValueError):self.build('bad_scope')

    def test_constructor_rejects_extra_unregistered_span_even_with_new_payload_fingerprint(self):
        self.build().close()
        import zlib
        connection=sqlite3.connect(self.bundle/'knowledge.sqlite')
        rogue=dict(span_id='IDXSPAN:raw:F1:stable:hit:999',file_id='F1',start=0,end=1,text='甲')
        connection.execute('INSERT INTO records VALUES (?,?,?)',('spans',rogue['span_id'],zlib.compress(json.dumps(rogue).encode())))
        connection.commit();connection.close()
        manifest=json.loads((self.bundle/'manifest.json').read_text(encoding='utf-8'))
        db=self.bundle/'knowledge.sqlite'
        manifest['files']['knowledge.sqlite']=dict(bytes=db.stat().st_size,sha256=hashlib.sha256(db.read_bytes()).hexdigest())
        manifest['counts']['spans']+=1
        mp=self.bundle/'manifest.json';mp.write_text(json.dumps(manifest),encoding='utf-8')
        self.lock['manifest_sha256']=hashlib.sha256(mp.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'span'):
            with self.open():pass

    def test_reviewed_scope_may_include_a_registered_legal_article(self):
        self.data['legal_sources']=[dict(source_id='LAW1',text='法条')]
        self.data['articles']=[dict(article_id='A1',source_id='LAW1',start=0,end=2,text='法条',text_sha256=textsha('法条'),original_source_text_sha256=textsha('法条'))]
        self.data['scope_sources']=[dict(source_id='LAW1',text='法条',source_sha256=textsha('法条'))]
        self.data['scope_spans']=[dict(span_id='LAWSPAN',source_id='LAW1',start=0,end=2,text='法条',text_sha256=textsha('法条'),source_sha256=textsha('法条'),layer='hit')]
        self.data['scope_units']=[dict(unit_id='A1',article_id='A1',source_id='LAW1',source_sha256=textsha('法条'),layers=dict(hit=['LAWSPAN']))]
        with self.build() as r:
            self.assertIn('A1',r.scope.units)
            self.assertEqual(r.read_article('A1')['text'],'法条')
        self.data['scope_units'][0]['unit_id']='unknown_article'
        with self.assertRaisesRegex(ValueError,'scope'):self.build('unknown_scope')

    def test_bundle_includes_pinned_portable_code_and_runs_in_fresh_process(self):
        self.build().close()
        self.assertTrue((self.bundle/'full_reader.py').is_file(),'portable reader entry point missing')
        manifest=json.loads((self.bundle/'manifest.json').read_text(encoding='utf-8'))
        self.assertIn('full_reader_task/reader.py',manifest['files'])
        command='from full_reader import FullKnowledgeReader; import json; r=FullKnowledgeReader(".",expected_manifest_sha256='+repr(self.lock['manifest_sha256'])+',expected_versions='+repr(self.versions)+'); print(r.read('+repr(self.unit['unit_id'])+')["file_id"]); r.close()'
        result=subprocess.run([sys.executable,'-S','-X','utf8','-B','-c',command],cwd=self.bundle,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'F1')

    def test_constructor_and_full_verification_emit_real_progress(self):
        self.build().close()
        events=[]
        with self.open(progress=events.append):pass
        self.assertIn('records_validated',[event['stage'] for event in events])
        from full_reader_task.builder import verify_full_reader
        lock=verify_full_reader(self.bundle,self.lock,progress=events.append)
        report=json.loads((self.bundle/'verification_report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['read_calls'],2)
        self.assertEqual(report['persistent_read_benchmark']['read_calls'],4)
        self.assertIn('full_readback_complete',[event['stage'] for event in events])
        self.lock=lock
        with self.open():pass


if __name__=='__main__':unittest.main()
