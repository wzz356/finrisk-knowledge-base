"""Isolated compatibility checks; preserve source bytes and candidate semantics."""
from datetime import date
from pathlib import Path
import argparse
import ast
import csv
import hashlib
import json
import re
import sys
import traceback
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / 'outputs/FinRisk_剩余全量准备_20261011'
RUN = ROOT / 'outputs/FinRisk_剩余全量运行_v2_20261011'
REPORTS = RUN / 'reports/质量验收_20261012/compat'
DEFAULT_LIST = RUN / 'reports/继续生成_20261012/冻结硬检待处理清单.json'
VERSION = 'finrisk-compat-v1'
FROZEN_CODE = {
    'work/finrisk_confirm30/check_proposals.py': '43a7d56643279f0ee368d1f90a3097bd1c432a7a9df57fcf9356d83bfd108577',
    'work/finrisk_remaining/quality_guard.py': 'c3a8e9bf9de462383b08f6d8d3da6d3bff34554b3231ba35c3d0cd4e432e4ee3',
    'work/finrisk_bulk/prepare_run.py': '48d6a799b67d01f8745a9b8973532a0b2814b24ba32a9cb1b95b437889539b4f',
}

_DIGITS = {char: value for value, char in enumerate('零一二三四五六七八九')}
_DIGITS.update({'〇': 0, '○': 0, 'O': 0, 'Ｏ': 0, 'Ο': 0})
_ISO_DATE = re.compile(r'(?<![0-9])([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})(?![0-9])')
_DOT_DATE = re.compile(r'(?<![0-9.])([0-9]{4})\.([0-9]{1,2})\.([0-9]{1,2})(?![0-9.])')
_CHINESE_DATE = re.compile(
    r'(?<![0-9零〇○OＯΟ一二三四五六七八九])'
    r'([0-9零〇○OＯΟ一二三四五六七八九]{4})年'
    r'([0-9一二三四五六七八九十]{1,3})月'
    r'([0-9一二三四五六七八九十]{1,3})日'
)


def compact(value):
    return re.sub(r'\s+', '', value or '')


def _number(value):
    if value.isascii() and value.isdigit():
        return int(value)
    if '十' in value:
        left, right = value.split('十')
        return (_DIGITS[left] if left else 1) * 10 + (_DIGITS[right] if right else 0)
    return int(''.join(str(_DIGITS[char]) for char in value))


def _parse_date(match):
    try:
        return date(*(_number(part) for part in match.groups()))
    except (ValueError, KeyError):
        return None


def validate_date(value, quote, where):
    if value is None:
        return
    patterns = (_ISO_DATE, _DOT_DATE, _CHINESE_DATE)
    matches = [pattern.fullmatch(compact(value)) for pattern in patterns]
    actual = next((_parse_date(match) for match in matches if match), None)
    if actual is None:
        raise ValueError(f'{where}: invalid complete date value {value!r}')
    dates = {_parse_date(match) for pattern in patterns for match in pattern.finditer(compact(quote))}
    if actual not in dates:
        raise ValueError(f'{where}: date value {actual.isoformat()} differs from complete date quote')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(proposal):
    return (json.dumps(proposal, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')


def _imports():
    for relative in ('work/finrisk_remaining', 'work/finrisk_bulk'):
        path = str(ROOT / relative)
        if path not in sys.path:
            sys.path.insert(0, path)


def _bound_source(relative):
    raw = (ROOT / relative).read_bytes()
    if sha(raw) != FROZEN_CODE[relative]:
        raise ValueError('Frozen base checker SHA differs: ' + relative)
    return raw


def _isolated_module(relative, name):
    raw = _bound_source(relative)
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / relative)
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


_ABBREVIATION = re.compile(r'[（(](?:以下简称|下称|简称)(?:为)?[“"‘]?[^（）()\n]{1,80}?[”"’]?[）)]')


def validate_party_name(task, proposal, case, aliases=()):
    """Require a contiguous name, explicit abbreviation insertion, or bound audit."""
    quote = case['party_quote']
    if not isinstance(quote, str) or not quote or quote not in task['full_text']:
        raise ValueError('party_quote must be an exact continuous source quotation')
    name = compact(case['party_name'])
    if not name:
        raise ValueError('party_name must be nonempty')
    if name in compact(quote):
        return 'whitespace_only'
    if name in _ABBREVIATION.sub('', compact(quote)):
        return 'explicit_parenthetical_abbreviation'
    candidates = [row for row in aliases if row.get('file_id') == task['file_id']
                  and row.get('case_key') == case['local_key']]
    if len(candidates) != 1:
        raise ValueError('Name requires exactly one source-bound semantic evidence exception: '
                         + task['file_id'] + '/' + case['local_key'])
    row = candidates[0]
    expected = {'file_id': task['file_id'], 'case_key': case['local_key'],
                'party_name': case['party_name'], 'party_quote': quote,
                'source_sha256': task['source_sha256'], 'text_sha256': task['text_sha256'],
                'proposal_content_sha256': sha(canonical(proposal)),
                'review_status': 'source_verified_candidate',
                'review_method': 'full_text_semantic_review'}
    for key, value in expected.items():
        if row.get(key) != value:
            raise ValueError('Semantic name evidence binding differs: ' + key)
    for key in ('exception_id', 'reviewer', 'rationale', 'evidence_quote', 'candidate_path', 'proposal_sha256'):
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError('Semantic name evidence requires nonempty ' + key)
    if row['evidence_quote'] not in task['full_text'] or quote not in row['evidence_quote']:
        raise ValueError('Semantic name evidence excerpt must be exact and include party_quote')
    candidate_path = Path(row['candidate_path']).resolve()
    if not candidate_path.is_relative_to(ROOT.resolve()):
        raise ValueError('Semantic name evidence candidate path escapes workspace')
    raw = candidate_path.read_bytes()
    _imports()
    from remaining_runtime import strict_json
    if sha(raw) != row['proposal_sha256'] or sha(canonical(strict_json(raw))) != expected['proposal_content_sha256']:
        raise ValueError('Semantic name evidence candidate byte/content SHA differs')
    return row['exception_id']


def validate_currency(penalty):
    if '人民币' not in compact(penalty['currency_quote']):
        raise ValueError('CNY requires exact source evidence spelling 人民币, allowing whitespace only')


_NAME_ASSERT = ast.parse("assert re.sub(r'\\s','',c['party_name']) in re.sub(r'\\s','',c['party_quote'])").body[0]
_CURRENCY_ASSERT = ast.parse("assert '人民币' in (penalty['currency_quote'] or '')").body[0]


def transform_structural_tree(tree):
    """Replace exactly two known field assertions; all other nodes are retained."""
    class CompatibilityFields(ast.NodeTransformer):
        def __init__(self):
            self.counts = {'name': 0, 'currency': 0}

        def visit_Assert(self, node):
            fingerprint = ast.dump(node, include_attributes=False)
            if fingerprint == ast.dump(_NAME_ASSERT, include_attributes=False):
                self.counts['name'] += 1
                replacement = ast.parse('_compat_party_check(input_record, p, c)').body[0]
                return ast.copy_location(replacement, node)
            if fingerprint == ast.dump(_CURRENCY_ASSERT, include_attributes=False):
                self.counts['currency'] += 1
                replacement = ast.parse('_compat_currency_check(penalty)').body[0]
                return ast.copy_location(replacement, node)
            return node
    visitor = CompatibilityFields()
    result = visitor.visit(tree)
    if visitor.counts != {'name': 1, 'currency': 1}:
        raise ValueError('Frozen structural compatibility replacements must be exactly two: '
                         + str(visitor.counts))
    return ast.fix_missing_locations(result), visitor.counts


def _structural_module(run_dir):
    relative = 'work/finrisk_confirm30/check_proposals.py'
    tree, counts = transform_structural_tree(ast.parse(_bound_source(relative)))
    module = types.ModuleType('finrisk_compat_structural_v1')
    module.__file__ = str(ROOT / relative)
    exec(compile(tree, module.__file__, 'exec'), module.__dict__)
    module.OUT = Path(run_dir)
    module.compatibility_replacements = counts
    return module


def make_compatibility_validator(run_dir, alias_records=()):
    """Production-equivalent guards plus strictly scoped formatting compatibility."""
    _imports()
    _bound_source('work/finrisk_bulk/prepare_run.py')
    from prepare_run import OUT, freeze_bytes, review_reasons, check_penalty_amounts
    from recall_labels import validate_recall_labels
    from next1000_quality import validate_coverage_granularity
    from remaining_runtime import strict_json
    structural = _structural_module(run_dir)
    quality = _isolated_module('work/finrisk_remaining/quality_guard.py', 'finrisk_compat_quality_v1')
    quality._validate_date = validate_date
    labels = {row['risk_tag'] for row in csv.DictReader((OUT / 'dictionary/risk_type_dictionary.csv')
                .read_text(encoding='utf-8-sig').splitlines())}
    scenes = set(strict_json((OUT / 'contracts/scene_dictionary.json').read_bytes())['scenes'])
    factors = {factor['factor_id'] for factor in strict_json((OUT / 'inputs/factor_catalog.json').read_bytes())['factors']}
    aliases = json.loads(json.dumps(alias_records, ensure_ascii=False, allow_nan=False))
    if not isinstance(aliases, list):
        raise ValueError('Semantic name evidence records must be a list')
    events = []
    def party_check(task, proposal, case):
        rule = validate_party_name(task, proposal, case, aliases)
        events.append({'case_key': case['local_key'], 'rule_or_exception': rule})
    structural._compat_party_check = party_check
    structural._compat_currency_check = validate_currency

    def validate(task, proposal):
        if task['document']['full_text'] != task['full_text']:
            raise ValueError('Task/document full_text differs')
        for key in ('source_sha256', 'text_sha256', 'text_version'):
            if task[key] != task['document'][key]:
                raise ValueError('Task/document source binding differs: ' + key)
        if sha(task['full_text'].encode('utf-8')) != task['text_sha256']:
            raise ValueError('Task text SHA differs')
        validate_recall_labels(proposal)
        validate_coverage_granularity(task, proposal)
        quality.validate_remaining_quality(task, proposal)
        payload = canonical(proposal)
        path = Path(run_dir) / 'validation_inputs' / f'{task["file_id"]}_{sha(payload)}.json'
        freeze_bytes(path, payload)
        events.clear()
        result, _ = structural.check_one(path, task, labels, scenes, factors)
        if result['coverage_uncovered_tokens']:
            raise ValueError('coverage leaves source tokens uncovered: ' + str(result['coverage_uncovered_tokens'][:3]))
        reasons = sorted(set(review_reasons(task['full_text'], proposal)) | set(check_penalty_amounts(proposal)))
        return {'requires_review': bool(reasons), 'reasons': reasons, 'cases': result['cases'],
                'behaviors': result['behaviors'], 'quote_fields_checked': result['quote_bindings'],
                'quote_spans_checked': result['spans_checked'], 'all_quotes_exact': result['all_quotes_exact'],
                'uncovered_tokens': result['coverage_uncovered_tokens'], 'compatibility_version': VERSION,
                'structural_replacements': structural.compatibility_replacements,
                'name_checks': list(events), 'semantic_status': 'candidate', 'human_review_status': 'pending'}
    return validate


def _verified_item(row):
    """Check frozen metadata and only this requested task/source, never full batches."""
    _imports()
    from fast_runtime import verify_overlay, batch_record, part_input, strict_json
    verify_overlay()
    manifest = strict_json((PACK / 'manifest.json').read_bytes())
    files = manifest['files']
    for name, expected in manifest['code_sha256'].items():
        if not Path(name).is_absolute() or sha(Path(name).read_bytes()) != expected:
            raise ValueError('Frozen package code binding differs: ' + name)
    def package_file(relative):
        path = (PACK / relative).resolve()
        if not path.is_relative_to(PACK.resolve()) or relative not in files:
            raise ValueError('Frozen package file membership differs: ' + relative)
        raw = path.read_bytes()
        if sha(raw) != files[relative]:
            raise ValueError('Frozen package file SHA differs: ' + relative)
        return raw
    shared = {'selected.json', 'schedule.json', 'runtime_config_template.json'}
    shared.update(relative for relative in files if relative.startswith(('contracts/', 'dictionary/')))
    for relative in shared:
        package_file(relative)
    batch_id, part_id = row['group'].split('/')
    for relative in files:
        if relative.startswith('batches/' + batch_id + '/'):
            package_file(relative)
    batch = batch_record(batch_id)
    group, output = part_input(batch, part_id)
    matching = [item for item in group['tasks'] if item['file_id'] == row['file_id']]
    if len(matching) != 1:
        raise ValueError('Candidate file ID is absent from its frozen scheduled group')
    task = strict_json(package_file(matching[0]['task_path']))
    if task['file_id'] != row['file_id']:
        raise ValueError('Task ID differs from requested candidate')
    raw_path = Path(task['raw_path']).resolve()
    if not raw_path.is_relative_to(PACK.resolve()):
        raise ValueError('Task raw source path escapes frozen package')
    raw = package_file(raw_path.relative_to(PACK.resolve()).as_posix())
    if sha(raw) != task['source_sha256']:
        raise ValueError('Task raw source SHA differs')
    candidate = Path(row['path']).resolve()
    if not candidate.is_relative_to(output):
        raise ValueError('Candidate path escapes its frozen scheduled output group')
    proposal_raw = candidate.read_bytes()
    if sha(proposal_raw) != row['candidate_sha256']:
        raise ValueError('Candidate byte SHA differs from explicit review list')
    proposal = strict_json(proposal_raw)
    if proposal.get('file_id') != row['file_id'] or proposal.get('read_full_text') is not True:
        raise ValueError('Candidate file ID or full-read declaration differs')
    return task, proposal, candidate, proposal_raw


def check_items(items, report_dir, alias_records=()):
    if not isinstance(items, list) or not 1 <= len(items) <= 5:
        raise ValueError('Each invocation must explicitly select one to five source documents')
    if len({row['file_id'] for row in items}) != len(items):
        raise ValueError('Duplicate candidate IDs in compatibility invocation')
    validator = make_compatibility_validator(report_dir, alias_records)
    records, failures = [], []
    for row in items:
        try:
            task, proposal, candidate, raw = _verified_item(row)
            result = validator(task, proposal)
            records.append({'file_id': row['file_id'], 'candidate_path': str(candidate),
                            'proposal_sha256': sha(raw), 'proposal_content_sha256': sha(canonical(proposal)),
                            'source_sha256': task['source_sha256'], 'text_sha256': task['text_sha256'],
                            **result})
        except (AssertionError, ValueError, KeyError, TypeError, OSError) as error:
            frame = traceback.extract_tb(error.__traceback__)[-1]
            failures.append({'file_id': row['file_id'], 'reason': f'{type(error).__name__}: {error}',
                             'origin': f'{Path(frame.filename).name}:{frame.lineno} {frame.line}'})
    return {'status': 'pass' if not failures else 'fail', 'compatibility_version': VERSION,
            'documents_requested': len(items), 'documents_passed': len(records), 'records': records,
            'failures': failures, 'source_read_batch_limit': 5,
            'frozen_base_checker_sha256': FROZEN_CODE,
            'compat_checker_sha256': sha(Path(__file__).read_bytes()),
            'external_api_calls': 0, 'semantic_status': 'candidate', 'human_review_status': 'pending'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', default=str(DEFAULT_LIST))
    parser.add_argument('--ids', required=True, nargs='+')
    parser.add_argument('--aliases')
    parser.add_argument('--report', required=True)
    args = parser.parse_args(argv)
    _imports()
    from remaining_runtime import strict_json
    from prepare_run import freeze_json
    requested = args.ids
    if not 1 <= len(requested) <= 5 or len(set(requested)) != len(requested):
        parser.error('--ids requires one to five unique IDs')
    review_list = strict_json(Path(args.list).read_bytes())
    selected = [row for row in review_list['items'] if row['file_id'] in set(requested)]
    if len(selected) != len(requested):
        parser.error('Selected IDs are absent or duplicated in explicit review list')
    alias_records = []
    if args.aliases:
        alias_records = strict_json(Path(args.aliases).read_bytes())['records']
    report_path = Path(args.report).resolve()
    if not report_path.is_relative_to(REPORTS.resolve()):
        parser.error('--report must remain within the isolated compatibility report directory')
    result = check_items(selected, report_path.parent / report_path.stem, alias_records)
    result['review_list_sha256'] = sha(Path(args.list).read_bytes())
    result['alias_evidence_sha256'] = sha(Path(args.aliases).read_bytes()) if args.aliases else None
    freeze_json(report_path, result)
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
