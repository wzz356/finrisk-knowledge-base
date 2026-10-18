"""只读证据读取契约：先于实现创建，真实文件，不使用模型或网络。"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).with_name('evidence_loader.py')
VERSIONS = {'content': 'content-v1', 'projection': 'projection-v1',
            'articles': 'articles-v1', 'rules': 'rules-v1', 'scope': 'scope-v1'}

def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

class LoaderContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.tmp.name)
        text = '甲公司：行为甲。\n乙公司：行为乙。\n条件：真实回答。'
        self.source = {'source_id': 'S1', 'file_id': 'F1', 'text': text,
                       'source_sha256': sha(text)}
        self.spans = [
            {'span_id': 'P1', 'source_id': 'S1', 'start': 4, 'end': 8,
             'text': text[4:8], 'text_sha256': sha(text[4:8]), 'layer': 'hit'},
            {'span_id': 'P2', 'source_id': 'S1', 'start': 0, 'end': 8,
             'text': text[:8], 'text_sha256': sha(text[:8]), 'layer': 'supplement'},
            {'span_id': 'P3', 'source_id': 'S1', 'start': 9, 'end': 17,
             'text': text[9:17], 'text_sha256': sha(text[9:17]), 'layer': 'extended'}]
        self.unit = {'unit_id': 'U1', 'file_id': 'F1', 'source_id': 'S1',
                     'source_sha256': sha(text), 'layers': {'hit': ['P1'],
                     'supplement': ['P2'], 'extended': ['P3']},
                     'candidate_status': 'candidate', 'human_approved': False,
                     'attribution_limits': ['乙公司内容不可归给甲公司'],
                     'effect_status': 'historical_case_not_current_legality',
                     'human_review_status': 'pending'}
        self.write_bundle()

    def tearDown(self):
        self.tmp.cleanup()

    def write_bundle(self):
        files = {}
        for name, rows in [('sources.jsonl', [self.source]),
                           ('spans.jsonl', self.spans), ('scope_overlays.jsonl', [self.unit])]:
            raw = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows)
            (self.root / name).write_text(raw, encoding='utf-8')
            files[name] = {'sha256': hashlib.sha256((self.root / name).read_bytes()).hexdigest()}
        self.manifest = {'schema': 'finrisk-evidence-handoff-v1',
                         'versions': copy.deepcopy(VERSIONS), 'files': files}
        (self.root / 'handoff_manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def loader(self, versions=None):
        self.assertTrue(MODULE.exists(), '缺少只读加载器实现；RED 阶段预期失败')
        spec = importlib.util.spec_from_file_location('scope_loader', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.EvidenceLoader(self.root, expected_versions=versions)

    def test_missing_version_rejected(self):
        with self.assertRaisesRegex(ValueError, 'version'):
            self.loader()

    def test_incompatible_projection_rejected(self):
        bad = dict(VERSIONS, projection='other')
        with self.assertRaisesRegex(ValueError, 'version'):
            self.loader(bad)

    def test_unknown_id_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unknown'):
            self.loader(VERSIONS).read('NOT_REGISTERED')

    def test_default_returns_only_registered_hit(self):
        got = self.loader(VERSIONS).read('U1')
        self.assertEqual([s['span_id'] for s in got['segments']], ['P1'])
        self.assertEqual(got['segments'][0]['text'], self.source['text'][4:8])
        self.assertFalse(got['human_approved'])
        self.assertEqual(got['attribution_limits'], self.unit['attribution_limits'])

    def test_extended_requires_explicit_layer(self):
        got = self.loader(VERSIONS).read('U1', layer='extended')
        self.assertEqual([s['span_id'] for s in got['segments']], ['P3'])
        self.assertEqual(got['layer'], 'extended')

    def test_wrong_layer_span_rejected(self):
        with self.assertRaisesRegex(ValueError, 'scope'):
            self.loader(VERSIONS).read('P3', layer='hit')

    def test_arbitrary_range_rejected(self):
        with self.assertRaisesRegex(ValueError, 'range'):
            self.loader(VERSIONS).read('P1', start=0, end=17)

    def test_source_corruption_rejected(self):
        with (self.root / 'sources.jsonl').open('a', encoding='utf-8') as f:
            f.write(' ')
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.loader(VERSIONS)

    def test_registered_but_invalid_span_rejected(self):
        self.spans[0]['end'] = 999
        self.write_bundle()
        with self.assertRaisesRegex(ValueError, 'span'):
            self.loader(VERSIONS)

    def test_span_exact_range_allowed(self):
        got = self.loader(VERSIONS).read('P1', start=4, end=8)
        self.assertEqual(got['segments'][0]['text'], self.source['text'][4:8])

    def test_duplicate_unit_rejected(self):
        file = self.root / 'scope_overlays.jsonl'
        file.write_text(file.read_text(encoding='utf-8') * 2, encoding='utf-8')
        self.manifest['files'][file.name]['sha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
        (self.root / 'handoff_manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.loader(VERSIONS)

    def test_unit_span_namespace_collision_rejected(self):
        self.spans[0]['span_id'] = 'U1'
        self.unit['layers']['hit'] = ['U1']
        self.write_bundle()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.loader(VERSIONS)

    def test_span_source_fingerprint_mismatch_rejected(self):
        self.spans[0]['source_sha256'] = '0' * 64
        self.write_bundle()
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.loader(VERSIONS)

    def test_caller_cannot_mutate_future_read(self):
        loader = self.loader(VERSIONS)
        got = loader.read('U1')
        got['segments'][0]['text'] = '伪造'
        got['attribution_limits'].clear()
        later = loader.read('U1')
        self.assertEqual(later['segments'][0]['text'], self.source['text'][4:8])
        self.assertEqual(later['attribution_limits'], self.unit['attribution_limits'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
