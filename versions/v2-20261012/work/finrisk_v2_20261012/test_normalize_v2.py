import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name('normalize_v2.py')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def fixture(fid='F000001', text='甲罚款10万元。没有向客户销售。条件成立时提示。甲罚款10万元。'):
    quote = '甲罚款10万元。'
    case = {'local_key': 'company', 'party_name': '甲', 'party_type': 'institution',
            'party_quote': quote, 'penalty_doc_no': None, 'regulator': None,
            'penalty_date': None, 'behavior_period': None, 'doc_no_quote': None,
            'regulator_quote': None, 'penalty_date_quote': None, 'behavior_period_quote': None,
            'case_summary': quote, 'case_summary_quotes': [quote], 'legal_refs': [],
            'penalties': [{'type': '罚款', 'amount_yuan': 100000, 'amount_quote': quote,
                           'basis_quote': quote, 'currency': None, 'currency_quote': None}],
            'institution_hierarchy': {'level': None, 'missing_reason': '未载'},
            'related_party_names': [], 'unknowns': ['币种未载，不能推断']}
    material = {'name': '提示', 'form': '文本', 'function': 'prohibition_reminder',
                'quote': '条件成立时提示。', 'original_expression_quote': None,
                'complete_business_material_available': False}
    behavior = {'local_key': 'violation', 'case_key': 'company', 'actor_role': 'institution_violation',
                'action': '提示', 'target': None, 'object': None, 'summary': '提示',
                'finding_quote': quote, 'conditions': [{'value': '条件成立', 'quote': '条件成立时提示。'}],
                'negations': [{'value': '没有销售', 'quote': '没有向客户销售。'}],
                'exceptions': [], 'uncertainties': ['对象未载'], 'regulatory_finding': '提示',
                'risk_mechanism': None, 'risk_mechanism_quotes': [], 'product_type': None,
                'product_quote': None, 'material_function': 'prohibition_reminder',
                'material_function_quotes': [], 'materials': [material],
                'observed_scene': {'scene_id': None, 'basis': 'unknown', 'quotes': []},
                'applicable_scenes': [], 'factor_values': [], 'zero_tag_reason': None,
                'risk_tags': [{'tag': '其他', 'match_basis': 'inferred', 'assignment_scope': 'behavior_context',
                               'necessary_conditions': ['仅本案'], 'limitations': ['缺乏材料'],
                               'quotes': [quote], 'reason': '机制未知'}]}
    draft = {'file_id': fid, 'cases': [case], 'behaviors': [behavior], 'coverage': [],
             'insurance_relevance': {'value': None, 'quotes': []},
             'marketing_relevance': {'value': None, 'quotes': []},
             'semantic_status': 'candidate', 'human_review_status': 'pending',
             'source_issues': ['源文本缺页待核'], 'unresolved': []}
    wrapper = {'file_id': fid, 'batch': 'early30', 'draft': draft, 'draft_json_sha256': digest(draft),
               'semantic_status': 'candidate', 'human_review_status': 'pending',
               'status_origin': 'draft', 'original_candidate_path': None,
               'original_candidate_sha256': None}
    text_sha = hashlib.sha256(text.encode('utf-8')).hexdigest()
    source = {'file_id': fid, 'full_text': text, 'text_sha256': text_sha,
              'source_sha256': text_sha, 'text_version': 1, 'document_metadata': {}}
    return wrapper, source


class NormalizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = None
        if MODULE.is_file():
            spec = importlib.util.spec_from_file_location('normalize_v2', MODULE)
            cls.mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.mod)

    def setUp(self):
        self.assertIsNotNone(self.mod, 'normalize_v2 implementation is missing')
        fixture_root = MODULE.parent / 'normalize_fixtures'
        fixture_root.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=fixture_root)
        self.assertTrue(Path(self.tmp.name).resolve().is_relative_to(fixture_root.resolve()))
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / 'result'

    def rows(self, name, extension=False):
        path = self.out / ('extensions' if extension else 'data') / (name + '.jsonl')
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]

    def build(self, wrappers, sources, overlays=None):
        return self.mod.normalize_records({x['file_id']: x for x in wrappers},
                                          {x['file_id']: x for x in sources}, self.out, overlays)

    def test_local_keys_do_not_cross_documents_and_ids_ignore_input_order(self):
        a, sa = fixture(); b, sb = fixture('F000002')
        self.build([a, b], [sa, sb])
        cases = self.rows('cases'); behaviors = self.rows('behaviors')
        self.assertEqual(len({x['case_id'] for x in cases}), 2)
        self.assertEqual(len({x['behavior_id'] for x in behaviors}), 2)
        first = {x['official_file_id']: x['case_id'] for x in cases}
        self.out = Path(self.tmp.name) / 'second'
        self.build([b, a], [sb, sa])
        self.assertEqual(first, {x['official_file_id']: x['case_id'] for x in self.rows('cases')})
        self.assertTrue(self.mod.verify(self.out)['passed'])

    def test_multi_party_penalties_never_aggregate(self):
        a, s = fixture()
        second = copy.deepcopy(a['draft']['cases'][0]); second.update(local_key='person', party_name='乙', party_type='person')
        second['penalties'][0]['amount_yuan'] = 20000
        a['draft']['cases'].append(second); a['draft_json_sha256'] = digest(a['draft'])
        self.build([a], [s])
        self.assertEqual([x['penalties'][0]['amount_yuan'] for x in self.rows('cases')], [100000, 20000])
        self.assertNotIn('total_fine_yuan', self.rows('cases')[0])

    def test_repeated_quotes_keep_every_exact_position_and_ambiguity(self):
        a, s = fixture(); self.build([a], [s])
        matches = [x for x in self.rows('evidence') if x['verbatim'] == '甲罚款10万元。']
        self.assertEqual([x['start_char'] for x in matches], [0, s['full_text'].rfind('甲罚款10万元。')])
        self.assertTrue(all(x['quote_location_ambiguity'] for x in matches))
        self.assertTrue(all(s['full_text'][x['start_char']:x['end_char']] == x['verbatim'] for x in matches))

    def test_tags_qualifiers_unknowns_and_source_gaps_preserved(self):
        a, s = fixture(); original = copy.deepcopy(a)
        self.build([a], [s]); behavior = self.rows('behaviors')[0]; case = self.rows('cases')[0]
        self.assertEqual(behavior['risk_tag_basis'][0]['match_basis'], 'inferred')
        self.assertEqual(behavior['risk_tag_basis'][0]['limitations'], ['缺乏材料'])
        self.assertEqual(behavior['negations'], a['draft']['behaviors'][0]['negations'])
        self.assertEqual(behavior['conditions'], a['draft']['behaviors'][0]['conditions'])
        self.assertIsNone(behavior['target']); self.assertIsNone(case['penalties'][0]['currency'])
        self.assertIn('币种未载，不能推断', case['missing_reasons'])
        self.assertIn('源文本缺页待核', case['quality_flags'])
        self.assertEqual(a, original)
        self.assertTrue(any(x['field'] == 'target' and x['origin'] == 'derived_missing_metadata'
                            for x in behavior['derived_missing_reasons']))

    def test_unmatched_quotes_preserve_facts_with_no_fabricated_evidence(self):
        a, s = fixture(); a['draft']['behaviors'][0]['finding_quote'] = '不存在于原文的引文'
        a['draft_json_sha256'] = digest(a['draft']); self.build([a], [s])
        behavior = self.rows('behaviors')[0]
        self.assertEqual(behavior['regulatory_finding'], '提示')
        self.assertEqual(behavior['fact_evidence_ids'], [])
        self.assertTrue(any(x['code'] == 'QUOTE_NOT_FOUND' for x in self.rows('issues', True)))
        self.assertNotIn('不存在于原文的引文', [x['verbatim'] for x in self.rows('evidence')])
        self.assertTrue(self.mod.verify(self.out)['passed'])

    def test_material_identity_shared_without_orphan_references(self):
        a, s = fixture(); second = copy.deepcopy(a['draft']['behaviors'][0]); second['local_key'] = 'second'
        a['draft']['behaviors'].append(second); a['draft_json_sha256'] = digest(a['draft'])
        self.build([a], [s]); material = self.rows('materials')
        self.assertEqual(len(material), 1)
        self.assertEqual(self.rows('behaviors')[0]['material_ids'], self.rows('behaviors')[1]['material_ids'])
        self.assertTrue(self.mod.verify(self.out)['passed'])

    def test_overlays_bind_separate_hashes_and_snapshots(self):
        a, s = fixture(); overlay = copy.deepcopy(a['draft']); overlay['cases'][0]['case_summary'] = '修正后摘要'
        self.build([a], [s], {a['file_id']: overlay})
        doc = self.rows('documents')[0]
        self.assertEqual(doc['base_draft_json_sha256'], digest(a['draft']))
        self.assertEqual(doc['effective_draft_json_sha256'], digest(overlay))
        snapshot = self.rows('candidate_snapshots', True)[0]
        self.assertEqual(snapshot['base_draft'], a['draft']); self.assertEqual(snapshot['effective_draft'], overlay)
        self.assertTrue(self.mod.verify(self.out)['passed'])

    def test_missing_early_status_uses_wrapper_not_human_approval(self):
        a, s = fixture(); a['draft'].pop('semantic_status'); a['draft'].pop('human_review_status')
        a['status_origin'] = 'frozen_early30_batch'; a['draft_json_sha256'] = digest(a['draft'])
        self.build([a], [s]); self.assertEqual(self.rows('cases')[0]['publication_status'], 'candidate')
        review = self.rows('reviews')[0]; self.assertEqual(review['status'], 'pending')
        self.assertIsNone(review['reviewer']); self.assertEqual(review['approved_scope'], [])
        self.assertTrue(all(x['creator'] == 'unknown' for x in self.rows('annotations')))

    def test_no_case_document_quotes_stay_document_extension(self):
        a, s = fixture(); a['draft']['cases'] = []; a['draft']['behaviors'] = []
        a['draft']['insurance_relevance']['quotes'] = ['甲罚款10万元。']
        a['draft_json_sha256'] = digest(a['draft']); self.build([a], [s])
        self.assertEqual(self.rows('evidence'), [])
        self.assertEqual(len(self.rows('document_evidence', True)), 2)
        self.assertTrue(self.mod.verify(self.out)['passed'])

    def test_verifier_detects_tampering_and_loader_detects_duplicate_ids(self):
        a, s = fixture(); self.build([a], [s])
        path = self.out / 'data/cases.jsonl'; path.write_text(path.read_text(encoding='utf-8') + '\n', encoding='utf-8')
        self.assertFalse(self.mod.verify(self.out)['passed'])
        repo = Path(self.tmp.name) / 'repo'; (repo / 'data/candidates').mkdir(parents=True)
        (repo / 'data/sources').mkdir(parents=True)
        (repo / 'data/candidates/part-0001.jsonl').write_text(json.dumps(a) + '\n' + json.dumps(a) + '\n', encoding='utf-8')
        (repo / 'data/sources/part-0001.jsonl').write_text(json.dumps(s) + '\n', encoding='utf-8')
        with self.assertRaises(ValueError): self.mod.load_records(repo)

    def rebind_manifest_file(self, relative):
        path = self.out / relative
        manifest_path = self.out / 'manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['files'][relative] = {'bytes': path.stat().st_size,
                                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

    def test_verifier_rejects_field_evidence_orphan_even_after_manifest_rehash(self):
        a, s = fixture(); self.build([a], [s]); rows = self.rows('cases')
        rows[0]['field_evidence']['party'] = ['NONEXISTENT']
        path = self.out / 'data/cases.jsonl'
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        self.rebind_manifest_file('data/cases.jsonl')
        self.assertFalse(self.mod.verify(self.out)['passed'])

    def test_verifier_recomputes_all_quote_occurrences(self):
        a, s = fixture(); self.build([a], [s]); rows = self.rows('quote_bindings', True)
        rows[0]['occurrences'] = [[0, 1]]
        path = self.out / 'extensions/quote_bindings.jsonl'
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        self.rebind_manifest_file('extensions/quote_bindings.jsonl')
        self.assertFalse(self.mod.verify(self.out)['passed'])

    def test_verifier_rejects_wrong_navigation_pointer(self):
        a, s = fixture(); self.build([a], [s])
        path = self.out / 'reading/case_reading.jsonl'; row = json.loads(path.read_text(encoding='utf-8'))
        row['document_table']['line'] = 999999
        path.write_text(json.dumps(row) + '\n', encoding='utf-8')
        self.rebind_manifest_file('reading/case_reading.jsonl')
        self.assertFalse(self.mod.verify(self.out)['passed'])

    def test_verifier_detects_fact_drift_after_manifest_rehash(self):
        a, s = fixture(); self.build([a], [s]); rows = self.rows('behaviors')
        rows[0]['action'] = '销售'
        path = self.out / 'data/behaviors.jsonl'
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        self.rebind_manifest_file('data/behaviors.jsonl')
        self.assertFalse(self.mod.verify(self.out)['passed'])

    def test_verifier_rejects_unrecorded_human_approval(self):
        a, s = fixture(); self.build([a], [s]); rows = self.rows('cases')
        rows[0].update(human_review_status='approved', fact_review_status='approved', publication_status='approved_core')
        path = self.out / 'data/cases.jsonl'
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        self.rebind_manifest_file('data/cases.jsonl')
        self.assertFalse(self.mod.verify(self.out)['passed'])

    def rewrite_rows(self, relative, rows):
        (self.out / relative).write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
        self.rebind_manifest_file(relative)

    def test_verifier_binds_source_inventory_sha_and_identity_to_original_snapshot(self):
        a, s = fixture(); s['source_id'] = 'ORIGINAL-SOURCE'
        self.build([a], [s]); original = self.rows('source_inventory')
        for field, value in [('source_sha256', '0' * 64), ('official_file_id', 'F999999'),
                             ('original_source_id', 'INVENTED-SOURCE')]:
            with self.subTest(field=field):
                rows = copy.deepcopy(original); rows[0][field] = value
                self.rewrite_rows('data/source_inventory.jsonl', rows)
                self.assertFalse(self.mod.verify(self.out)['passed'])

    def test_verifier_rejects_fabricated_second_review_and_dates(self):
        a, s = fixture(); self.build([a], [s]); original = self.rows('reviews')
        mutations = [{'independent_second_review_completed': True, 'reviewed_at': '2026-10-12T00:00:00Z'},
                     {'completion_flag_origin': 'human_completed'}, {'original_record_sha256': '0' * 64},
                     {'origin': 'human_review'}]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                rows = copy.deepcopy(original); rows[0].update(mutation)
                self.rewrite_rows('data/reviews.jsonl', rows)
                self.assertFalse(self.mod.verify(self.out)['passed'])

    def test_verifier_rejects_fabricated_annotation_review_metadata_and_creator(self):
        a, s = fixture(); a['draft']['creator'] = 'recorded creator'
        a['draft_json_sha256'] = digest(a['draft']); self.build([a], [s])
        self.assertTrue(self.mod.verify(self.out)['passed'])
        original = self.rows('annotations')
        for mutation in [{'reviewer': 'invented reviewer', 'reviewed_at': '2026-10-12T00:00:00Z'},
                         {'review_note': '已人审'}, {'creator': 'invented creator'}, {'value': 'invented value'}]:
            with self.subTest(mutation=mutation):
                rows = copy.deepcopy(original); rows[0].update(mutation)
                self.rewrite_rows('data/annotations.jsonl', rows)
                self.assertFalse(self.mod.verify(self.out)['passed'])

    def test_verifier_checks_each_evidence_navigation_pointer_and_complete_set(self):
        a, s = fixture(); self.build([a], [s])
        relative = 'reading/behavior_reading.jsonl'
        original = [json.loads(line) for line in (self.out / relative).read_text(encoding='utf-8').splitlines()]
        for change in ['invalid_line_and_spans', 'wrong_spans', 'wrong_text_id', 'missing_location', 'duplicate_location']:
            with self.subTest(change=change):
                rows = copy.deepcopy(original); pointers = rows[0]['evidence_locations']
                if change == 'invalid_line_and_spans': pointers[0].update(line=999999, start_char=999999, end_char=999999)
                elif change == 'wrong_spans': pointers[0]['end_char'] = 999999
                elif change == 'wrong_text_id': pointers[0]['text_id'] = 'INVENTED-TEXT'
                elif change == 'missing_location': pointers.pop()
                else: pointers.append(copy.deepcopy(pointers[0]))
                self.rewrite_rows(relative, rows)
                self.assertFalse(self.mod.verify(self.out)['passed'])

    def check_reading_mutations(self, relative, mutations):
        original = [json.loads(line) for line in (self.out / relative).read_text(encoding='utf-8').splitlines()]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                rows = copy.deepcopy(original); rows[0].update(mutation)
                self.rewrite_rows(relative, rows)
                self.assertFalse(self.mod.verify(self.out)['passed'])

    def test_verifier_binds_case_reading_all_business_values_to_core(self):
        a, s = fixture(); self.build([a], [s])
        self.check_reading_mutations('reading/case_reading.jsonl', [
            {'case_summary': '原稿未记载的事实'}, {'parties': []}, {'penalties': []},
            {'behavior_ids': []}, {'legal_refs': [{'value': '虚构法条'}]}, {'missing_reasons': []},
            {'field_evidence_state': {'state': 'approved'}}, {'proposal_local_key': 'invented'},
            {'reader_note': '虚构结论'}, {'extra_business_field': 'invented'}])

    def test_verifier_binds_behavior_reading_qualifiers_and_tags_to_core(self):
        a, s = fixture(); self.build([a], [s])
        self.check_reading_mutations('reading/behavior_reading.jsonl', [
            {'negations': []}, {'conditions': []}, {'exceptions': [{'value': '虚构例外'}]},
            {'uncertainties': []}, {'risk_tags': []}, {'risk_tag_basis': []}, {'actor_refs': []},
            {'behavior_summary': '虚构事实'}, {'case_id': 'INVENTED'},
            {'field_evidence_state': {'state': 'approved'}}])

    def test_verifier_binds_reading_review_states_to_core(self):
        a, s = fixture(); self.build([a], [s])
        for relative in ['reading/case_reading.jsonl', 'reading/behavior_reading.jsonl']:
            self.check_reading_mutations(relative, [{'human_review_status': 'approved', 'publication_status': 'approved_core'},
                                                   {'fact_review_status': 'approved'}])
            # Restore this file before checking the next independent reading table.
            key = 'cases' if 'case_reading' in relative else 'behaviors'
            rows = [json.loads(line) for line in (self.out / relative).read_text(encoding='utf-8').splitlines()]
            for field in ['human_review_status', 'publication_status', 'fact_review_status']:
                rows[0][field] = self.rows(key)[0][field]
            self.rewrite_rows(relative, rows)

    def test_verifier_binds_document_index_metadata_lists_and_states_to_snapshot(self):
        a, s = fixture(); self.build([a], [s])
        self.check_reading_mutations('reading/document_index.jsonl', [
            {'source_sha256': '0' * 64}, {'text_sha256': '0' * 64}, {'base_draft_json_sha256': '0' * 64},
            {'batch': 'invented'}, {'case_ids': []}, {'behavior_ids': []}, {'source_id': 'INVENTED'},
            {'source_metadata_links': {'pdf_path': 'invented'}}, {'original_candidate_path': 'invented'},
            {'quote_problem_count': 999}, {'source_issues': []},
            {'human_review_status': 'approved', 'publication_status': 'approved_core'}])

    def test_verifier_requires_exact_reading_categories_without_silent_skips(self):
        a, s = fixture(); self.build([a], [s])
        manifest_path = self.out / 'manifest.json'
        original = json.loads(manifest_path.read_text(encoding='utf-8'))
        for name in ['document_index', 'case_reading', 'behavior_reading']:
            with self.subTest(missing=name):
                manifest = copy.deepcopy(original); manifest['reading_counts'].pop(name)
                manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
                self.assertFalse(self.mod.verify(self.out)['passed'])
        manifest_path.write_text(json.dumps(original), encoding='utf-8')
        relative = 'reading/behavior_reading.jsonl'
        rows = [json.loads(line) for line in (self.out / relative).read_text(encoding='utf-8').splitlines()]
        rows[0].update(human_review_status='approved', negations=[])
        self.rewrite_rows(relative, rows)
        manifest = json.loads(manifest_path.read_text(encoding='utf-8')); manifest['reading_counts'].pop('behavior_reading')
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        self.assertFalse(self.mod.verify(self.out)['passed'])

    def test_verifier_requires_hash_entries_for_every_mandatory_artifact(self):
        a, s = fixture(); self.build([a], [s])
        manifest_path = self.out / 'manifest.json'
        original = json.loads(manifest_path.read_text(encoding='utf-8'))
        required = [f'data/{name}.jsonl' for name in self.mod.PRIMARY] + [f'extensions/{name}.jsonl' for name in self.mod.EXTENSIONS]
        required += [f'reading/{name}.jsonl' for name in ['document_index', 'case_reading', 'behavior_reading']]
        required += ['contract/schema.json', 'INDEX.md']
        self.assertEqual(len(required), 19)
        for relative in required:
            with self.subTest(missing_hash=relative):
                manifest = copy.deepcopy(original); manifest['files'].pop(relative)
                manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
                self.assertFalse(self.mod.verify(self.out)['passed'])

    def legacy_legal_fixture(self):
        a, s = fixture()
        a['draft']['cases'][0]['legal_refs'] = ['公开表未载决定日期。', ['原始旧值', '另一旧值'],
                                             {'value': '原结构法条', 'quote': None}]
        a['draft_json_sha256'] = digest(a['draft'])
        try: self.build([a], [s])
        except TypeError as exc: self.fail('合法旧legal_refs字符串/数组尚未兼容: ' + str(exc))
        return a, s

    def test_legacy_string_and_array_legal_refs_keep_uninterpreted_original_values(self):
        a, s = self.legacy_legal_fixture(); refs = self.rows('cases')[0]['legal_refs']
        for index, kind in [(0, 'string'), (1, 'array')]:
            self.assertEqual(refs[index]['legacy_original_value'], a['draft']['cases'][0]['legal_refs'][index])
            self.assertEqual(refs[index]['legacy_original_type'], kind)
            self.assertEqual(refs[index]['representation'], 'legacy_raw_uninterpreted')
            self.assertIsNone(refs[index]['value']); self.assertIsNone(refs[index]['quote'])
            self.assertEqual(refs[index]['evidence_ids'], [])
            self.assertEqual(refs[index]['metadata_status'], 'unknown')
        self.assertEqual(refs[2]['value'], '原结构法条')
        self.assertEqual(self.rows('candidate_snapshots', True)[0]['base_draft'], a['draft'])
        self.assertTrue(self.mod.verify(self.out)['passed'])

    def test_verifier_rejects_legacy_legal_value_type_or_invented_extraction(self):
        a, s = self.legacy_legal_fixture(); original = self.rows('cases')
        for mutation in [{'legacy_original_value': '伪造'}, {'legacy_original_type': 'object'},
                         {'value': '猜测法条', 'quote': '猜测引文'},
                         {'evidence_ids': [self.rows('evidence')[0]['evidence_id']]}]:
            with self.subTest(mutation=mutation):
                rows = copy.deepcopy(original); rows[0]['legal_refs'][0].update(mutation)
                self.rewrite_rows('data/cases.jsonl', rows)
                report = self.mod.verify(self.out)
                self.assertFalse(report['passed'])
                self.assertTrue(any(error.startswith('case_legal_drift:') for error in report['errors']))

    def test_null_uncertainties_preserve_unknown_in_core_snapshot_and_reading(self):
        a, s = fixture(); a['draft']['behaviors'][0]['uncertainties'] = None
        a['draft_json_sha256'] = digest(a['draft']); self.build([a], [s])
        behavior = self.rows('behaviors')[0]
        self.assertEqual(behavior['uncertainties'], [])
        self.assertIn('original_uncertainties', behavior); self.assertIsNone(behavior['original_uncertainties'])
        self.assertEqual(behavior['uncertainties_status'], 'unknown_in_candidate')
        self.assertTrue(behavior['uncertainties_missing_reason'].startswith('derived:'))
        self.assertTrue(any(item['field'] == 'uncertainties' for item in behavior['derived_missing_reasons']))
        reading = json.loads((self.out / 'reading/behavior_reading.jsonl').read_text(encoding='utf-8'))
        self.assertEqual(reading['uncertainties_status'], 'unknown_in_candidate')
        self.assertIsNone(reading['original_uncertainties'])
        self.assertIsNone(self.rows('candidate_snapshots', True)[0]['base_draft']['behaviors'][0]['uncertainties'])
        self.assertTrue(self.mod.verify(self.out)['passed'])

    def test_verifier_rejects_null_uncertainty_converted_to_recorded_absence(self):
        a, s = fixture(); a['draft']['behaviors'][0]['uncertainties'] = None
        a['draft_json_sha256'] = digest(a['draft']); self.build([a], [s])
        self.assertTrue(self.mod.verify(self.out)['passed'])
        rows = self.rows('behaviors')
        rows[0].update(uncertainties_status='recorded', original_uncertainties=[], uncertainties_missing_reason=None)
        self.rewrite_rows('data/behaviors.jsonl', rows)
        report = self.mod.verify(self.out)
        self.assertFalse(report['passed'])
        self.assertTrue(any(error.startswith('behavior_uncertainties_drift:') for error in report['errors']))

    def case_compat_fixture(self):
        a, s = fixture(); case = a['draft']['cases'][0]
        case['case_summary'] = [{'type': '罚款', 'amount_yuan': 100000}]
        case['unknowns'] = None; case['related_party_names'] = '未载清晰主体关系'
        a['draft_json_sha256'] = digest(a['draft']); self.build([a], [s])
        return a, s

    def test_case_compat_preserves_nonstring_summary_null_unknowns_and_related_raw_value(self):
        a, s = self.case_compat_fixture(); case = self.rows('cases')[0]
        self.assertEqual(case['case_summary'], '')
        self.assertEqual(case['original_case_summary'], a['draft']['cases'][0]['case_summary'])
        self.assertEqual(case['case_summary_status'], 'legacy_non_string_uninterpreted')
        self.assertEqual(case['missing_reasons'], [])
        self.assertIsNone(case['original_unknowns']); self.assertEqual(case['missing_reasons_status'], 'unknown_in_candidate')
        self.assertEqual(case['related_party_names'], '未载清晰主体关系')
        self.assertEqual(case['related_party_names_original_type'], 'string')
        self.assertEqual(case['related_party_names_status'], 'legacy_non_array_uninterpreted')
        reading = json.loads((self.out / 'reading/case_reading.jsonl').read_text(encoding='utf-8'))
        for field in ['original_case_summary', 'case_summary_status', 'original_unknowns', 'missing_reasons_status',
                      'related_party_names', 'related_party_names_original_type', 'related_party_names_status']:
            self.assertEqual(reading[field], case[field])
        self.assertEqual(self.rows('candidate_snapshots', True)[0]['base_draft'], a['draft'])
        self.assertTrue(self.mod.verify(self.out)['passed'])

    def test_case_compat_verifier_rejects_guessed_summary_and_legacy_unknown_drift(self):
        a, s = self.case_compat_fixture(); original = self.rows('cases')
        self.assertTrue(self.mod.verify(self.out)['passed'])
        for mutation in [{'case_summary': '猜测出来的摘要'}, {'original_case_summary': []},
                         {'original_unknowns': [], 'missing_reasons_status': 'recorded'},
                         {'related_party_names': ['推断主体']}, {'related_party_names_original_type': 'array'}]:
            with self.subTest(mutation=mutation):
                rows = copy.deepcopy(original); rows[0].update(mutation)
                self.rewrite_rows('data/cases.jsonl', rows)
                report = self.mod.verify(self.out)
                self.assertFalse(report['passed'])
                self.assertTrue(any(error.startswith('case_compat_drift:') for error in report['errors']))


if __name__ == '__main__':
    unittest.main()
