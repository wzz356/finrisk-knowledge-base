"""Regression tests for the isolated, evidence-preserving compatibility layer."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEST_TMP = HERE / 'compat_tmp'
TEST_TMP.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'work/finrisk_remaining'))
sys.path.insert(0, str(HERE))
if (HERE / 'compat_check_v1.py').exists():
    import compat_check_v1 as compatibility
    from compat_check_v1 import validate_date
else:
    from quality_guard import _validate_date as validate_date

sys.path.insert(0, str(ROOT / 'work/finrisk_bulk'))
from prepare_run import make_production_validator
from quality_guard import validate_remaining_quality
from recall_labels import validate_recall_labels
from next1000_quality import validate_coverage_granularity


def fixture(directory, text, party='甲公司', party_quote=None, amount=5000, currency_quote=None):
    source = Path(directory) / 'source.txt'
    raw = text.encode('utf-8')
    source.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    doc = {'source_id': 'S-test', 'text_id': 'T-test', 'text_version': 1,
           'source_sha256': digest, 'text_sha256': digest, 'full_text': text}
    task = {'file_id': 'F999999', 'raw_path': str(source), 'source_sha256': digest,
            'text_sha256': digest, 'text_version': 1, 'full_text': text, 'document': doc}
    case = {'local_key': 'company', 'party_name': party, 'party_type': 'institution',
            'party_quote': party_quote or party, 'penalty_doc_no': None, 'doc_no_quote': None,
            'regulator': None, 'regulator_quote': None, 'penalty_date': None,
            'penalty_date_quote': None, 'behavior_period': None, 'behavior_period_quote': None,
            'penalties': [{'type': '罚款', 'amount_yuan': amount, 'amount_quote': text,
                           'basis_quote': text, 'currency': 'CNY' if currency_quote else None,
                           'currency_quote': currency_quote}], 'legal_refs': [],
            'case_summary': 'test', 'case_summary_quotes': [text],
            'institution_hierarchy': {'level': None, 'geographic_level': None},
            'related_party_names': [], 'unknowns': []}
    proposal = {'file_id': task['file_id'], 'read_full_text': True, 'semantic_status': 'candidate',
                'human_review_status': 'pending', 'label_policy_version': 'recall-v2',
                'source_issues': [], 'insurance_relevance': {}, 'marketing_relevance': {},
                'cases': [case], 'behaviors': [], 'coverage': [{'quote': text,
                    'case_keys': ['company'], 'behavior_keys': [], 'classification': 'penalty'}],
                'unresolved': [], 'self_review_note': 'test'}
    return task, proposal


def validator(directory):
    if 'compatibility' in globals() and hasattr(compatibility, 'make_compatibility_validator'):
        return compatibility.make_compatibility_validator(Path(directory))
    production = make_production_validator(Path(directory))
    def legacy(task, proposal):
        validate_recall_labels(proposal)
        validate_coverage_granularity(task, proposal)
        validate_remaining_quality(task, proposal)
        result = production(task, proposal)
        if result['uncovered_tokens']:
            raise ValueError('uncovered tokens')
        return result
    return legacy


class DateCompatibilityTests(unittest.TestCase):
    def test_greek_omicron_chinese_date(self):
        try:
            validate_date('2010-06-17', '二Ο一Ο年六月十七日\n', 'case penalty_date')
        except ValueError as error:
            self.fail(str(error))

    def test_dot_date_with_unpadded_components(self):
        try:
            validate_date('2019-03-11', '2019.3.11\n', 'case penalty_date')
        except ValueError as error:
            self.fail(str(error))

    def test_existing_chinese_and_iso_dates(self):
        validate_date('2010-06-22', '二〇一〇年六月二十二日', 'date')
        validate_date('2019-3-11', '2019-03-11', 'date')

    def test_rejects_wrong_day_greek(self):
        with self.assertRaises(ValueError):
            validate_date('2010-06-18', '二Ο一Ο年六月十七日', 'date')

    def test_rejects_wrong_day_dot(self):
        with self.assertRaises(ValueError):
            validate_date('2019-03-12', '2019.3.11', 'date')

    def test_rejects_invalid_and_incomplete_dates(self):
        for value, quote in [('2019-02-29', '2019.2.29'), ('2019-03-11', '2019.3'), ('2019-03-11', '2019.3.110')]:
            with self.subTest(value=value, quote=quote), self.assertRaises(ValueError):
                validate_date(value, quote, 'date')


class StructuralCompatibilityTests(unittest.TestCase):
    def test_currency_split_by_original_newline(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            text = '甲公司虚列费用，罚款人\n民币0.5万元。\n'
            task, proposal = fixture(directory, text, currency_quote=text)
            try:
                result = validator(directory)(task, proposal)
            except (AssertionError, ValueError) as error:
                self.fail(f'Original line-broken CNY quotation rejected: {error}')
            self.assertTrue(result['all_quotes_exact'])
            self.assertEqual([], result['uncovered_tokens'])

    def test_parenthetical_short_name_interrupting_full_company_name(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            text = '甲保险有限公司（以下简称“甲公司”）北京分公司虚列费用，罚款0.5万元。\n'
            name = '甲保险有限公司北京分公司'
            task, proposal = fixture(directory, text, name, text)
            try:
                validator(directory)(task, proposal)
            except (AssertionError, ValueError) as error:
                self.fail(f'Explicit parenthetical abbreviation rejected: {error}')

    def test_wrong_amount_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            task, proposal = fixture(directory, '甲公司虚列费用，罚款0.5万元。', amount=50000)
            with self.assertRaises(ValueError):
                validator(directory)(task, proposal)

    def test_nonverbatim_currency_quote_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            task, proposal = fixture(directory, '甲公司虚列费用，罚款人\n民币0.5万元。', currency_quote='人民币')
            with self.assertRaises(ValueError):
                validator(directory)(task, proposal)

    def test_unrelated_name_and_general_subsequence_are_rejected(self):
        for name, text in [('乙公司', '甲公司虚列费用，罚款0.5万元。'),
                           ('甲公司北京分公司', '甲公司乙公司北京分公司虚列费用，罚款0.5万元。')]:
            with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory, self.subTest(name=name):
                task, proposal = fixture(directory, text, name, text)
                with self.assertRaises((AssertionError, ValueError)):
                    validator(directory)(task, proposal)

    def test_ordinary_parentheses_are_not_removed(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            text = '甲公司（乙公司）北京分公司虚列费用，罚款0.5万元。'
            task, proposal = fixture(directory, text, '甲公司北京分公司', text)
            with self.assertRaises((AssertionError, ValueError)):
                validator(directory)(task, proposal)

    def test_missing_coverage_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            task, proposal = fixture(directory, '甲公司虚列费用，罚款0.5万元。')
            proposal['coverage'] = []
            with self.assertRaises(ValueError):
                validator(directory)(task, proposal)

    def test_fine_quote_attributed_to_other_party_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            text = '甲公司虚列费用。乙公司虚列费用。对甲公司罚款0.5万元；对乙公司罚款1万元。'
            task, proposal = fixture(directory, text)
            other = copy.deepcopy(proposal['cases'][0])
            other.update(local_key='other', party_name='乙公司', party_quote='乙公司')
            other['penalties'] = []
            proposal['cases'].append(other)
            penalty = proposal['cases'][0]['penalties'][0]
            penalty.update(amount_yuan=10000, amount_quote='对乙公司罚款1万元', basis_quote='对乙公司罚款1万元')
            with self.assertRaises(ValueError):
                validator(directory)(task, proposal)

    def test_nonofficial_risk_tag_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            task, proposal = fixture(directory, '甲公司虚列费用，罚款0.5万元。')
            proposal['behaviors'] = [{'local_key': 'b1', 'risk_tags': [{'tag': '任意伪造标签'}]}]
            with self.assertRaises(ValueError):
                validator(directory)(task, proposal)

    def test_changed_source_or_text_binding_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            task, proposal = fixture(directory, '甲公司虚列费用，罚款0.5万元。')
            for field in ('source_sha256', 'text_sha256'):
                changed = copy.deepcopy(task)
                changed[field] = '0' * 64
                with self.subTest(field=field), self.assertRaises(ValueError):
                    validator(directory)(changed, proposal)


class BoundNameEvidenceTests(unittest.TestCase):
    def prepare(self, directory):
        text = '甲保险有限公司\n处罚编号123\n北京分公司虚列费用，罚款0.5万元。'
        task, proposal = fixture(directory, text, '甲保险有限公司北京分公司', text)
        candidate = Path(directory) / 'candidate.json'
        raw = (json.dumps(proposal, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        candidate.write_bytes(raw)
        row = {'exception_id': 'synthetic-name-001', 'file_id': task['file_id'],
               'case_key': 'company', 'party_name': proposal['cases'][0]['party_name'],
               'party_quote': text, 'source_sha256': task['source_sha256'],
               'text_sha256': task['text_sha256'], 'proposal_sha256': hashlib.sha256(raw).hexdigest(),
               'proposal_content_sha256': hashlib.sha256(compatibility.canonical(proposal)).hexdigest(),
               'candidate_path': str(candidate), 'review_status': 'source_verified_candidate',
               'review_method': 'full_text_semantic_review', 'reviewer': 'synthetic-test-reviewer',
               'rationale': 'Synthetic explicit audit of a page identifier inserted into the name.',
               'evidence_quote': text}
        return task, proposal, row, candidate

    def test_bound_semantic_name_evidence_accepts_only_specific_candidate(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            task, proposal, row, _ = self.prepare(directory)
            with self.assertRaises(AssertionError):
                make_production_validator(Path(directory) / 'legacy')(task, proposal)
            checked = compatibility.make_compatibility_validator(Path(directory) / 'compat', [row])(task, proposal)
            self.assertEqual('synthetic-name-001', checked['name_checks'][0]['rule_or_exception'])
            self.assertEqual('candidate', checked['semantic_status'])
            self.assertEqual('pending', checked['human_review_status'])

    def test_changed_exception_identity_or_quote_or_hash_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            task, proposal, row, _ = self.prepare(directory)
            for field in ('file_id', 'case_key', 'party_name', 'party_quote', 'source_sha256',
                          'text_sha256', 'proposal_sha256', 'proposal_content_sha256',
                          'review_status', 'review_method', 'evidence_quote'):
                bad_row = copy.deepcopy(row)
                bad_row[field] = 'wrong-binding'
                with self.subTest(field=field), self.assertRaises(ValueError):
                    compatibility.make_compatibility_validator(Path(directory) / field, [bad_row])(task, proposal)

    def test_changed_proposal_content_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            task, proposal, row, _ = self.prepare(directory)
            proposal['self_review_note'] = 'changed candidate'
            with self.assertRaises(ValueError):
                compatibility.make_compatibility_validator(Path(directory) / 'compat', [row])(task, proposal)

    def test_candidate_bytes_are_freshly_rechecked(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            task, proposal, row, candidate = self.prepare(directory)
            check = compatibility.make_compatibility_validator(Path(directory) / 'compat', [row])
            check(task, proposal)
            candidate.write_bytes(candidate.read_bytes() + b'\n')
            with self.assertRaises(ValueError):
                check(task, proposal)

    def test_duplicate_semantic_exceptions_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            task, proposal, row, _ = self.prepare(directory)
            with self.assertRaises(ValueError):
                compatibility.make_compatibility_validator(Path(directory) / 'compat', [row, row])(task, proposal)


class IsolationTests(unittest.TestCase):
    def test_structural_patch_count_fails_closed(self):
        missing = ast.parse("assert '人民币' in (penalty['currency_quote'] or '')")
        doubled = ast.parse("assert re.sub(r'\\s','',c['party_name']) in re.sub(r'\\s','',c['party_quote'])\n"
                            "assert '人民币' in (penalty['currency_quote'] or '')\n"
                            "assert '人民币' in (penalty['currency_quote'] or '')")
        for tree in (missing, doubled):
            with self.assertRaises(ValueError):
                compatibility.transform_structural_tree(tree)

    def test_global_quality_module_is_unchanged(self):
        from quality_guard import _validate_date as frozen_date
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            compatibility.make_compatibility_validator(Path(directory))
        with self.assertRaises(ValueError):
            frozen_date('2019-03-11', '2019.3.11', 'date')
        with self.assertRaises(ValueError):
            frozen_date('2010-06-17', '二Ο一Ο年六月十七日', 'date')

    def test_more_than_five_sources_are_rejected_before_read(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            with self.assertRaises(ValueError):
                compatibility.check_items([{'file_id': f'F{n:06d}'} for n in range(6)], Path(directory))


if __name__ == '__main__':
    unittest.main(verbosity=2)
