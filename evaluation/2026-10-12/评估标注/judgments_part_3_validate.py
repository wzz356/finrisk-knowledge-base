import collections
import hashlib
import json
from pathlib import Path

base = Path(__file__).parent
input_path = base / 'judgment_part_3.jsonl'
output_path = base / 'judgments_part_3.jsonl'
inputs = [json.loads(line) for line in input_path.read_text(encoding='utf-8').splitlines()]
outputs = [json.loads(line) for line in output_path.read_text(encoding='utf-8').splitlines()]
source_map = {row['pair_id']: row for row in inputs}
assert len(source_map) == len(inputs)
assert len({row['pair_id'] for row in outputs}) == len(outputs)
assert set(source_map) == {row['pair_id'] for row in outputs}

expected_keys = {'pair_id', 'help_grade', 'help_type', 'mechanism_match', 'conditions_match', 'source_quote', 'reason', 'limitations', 'misleading_risk', 'contexts'}
context_keys = {'context_id', 'help_grade', 'evidence_quote', 'reason', 'misleading_risk'}
expected_contexts = {(row['pair_id'], context['context_id']) for row in inputs for context in row['contexts']}
observed_contexts = []
for row in outputs:
    source = source_map[row['pair_id']]
    assert set(row) == expected_keys
    assert type(row['help_grade']) is int and 0 <= row['help_grade'] <= 3
    assert row['help_type'] in {'support', 'boundary', 'irrelevant'}
    assert row['mechanism_match'] in {'same', 'partial', 'different'}
    assert row['conditions_match'] in {'compatible', 'partial', 'conflict', 'unknown'}
    assert type(row['misleading_risk']) is bool
    assert type(row['limitations']) is list and all(type(item) is str for item in row['limitations'])
    assert type(row['reason']) is str and row['reason']
    assert type(row['source_quote']) is str
    assert row['help_grade'] < 2 or row['source_quote']
    assert not row['source_quote'] or row['source_quote'] in source['full_source_text']
    context_map = {context['context_id']: context for context in source['contexts']}
    assert len(row['contexts']) == len(source['contexts'])
    assert len({context['context_id'] for context in row['contexts']}) == len(row['contexts'])
    assert set(context_map) == {context['context_id'] for context in row['contexts']}
    for context in row['contexts']:
        assert set(context) == context_keys
        assert type(context['help_grade']) is int and 0 <= context['help_grade'] <= 3
        assert type(context['misleading_risk']) is bool
        assert type(context['reason']) is str and context['reason']
        assert type(context['evidence_quote']) is str
        assert context['help_grade'] < 2 or context['evidence_quote']
        assert not context['evidence_quote'] or context['evidence_quote'] in source['full_source_text']
        assert not context['evidence_quote'] or context['evidence_quote'] in context_map[context['context_id']]['text']
        observed_contexts.append((row['pair_id'], context['context_id']))
assert len(set(observed_contexts)) == len(observed_contexts)
assert set(observed_contexts) == expected_contexts

report = {
    'pairs': len(outputs),
    'contexts': len(observed_contexts),
    'queries': len({row['query_id'] for row in inputs}),
    'input_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(),
    'output_sha256': hashlib.sha256(output_path.read_bytes()).hexdigest(),
    'file_grade_counts': dict(sorted(collections.Counter(row['help_grade'] for row in outputs).items())),
    'context_grade_counts': dict(sorted(collections.Counter(context['help_grade'] for row in outputs for context in row['contexts']).items())),
    'file_misleading': sum(row['misleading_risk'] for row in outputs),
    'context_misleading': sum(context['misleading_risk'] for row in outputs for context in row['contexts']),
    'coverage_unique_schema_quote_checks': 'PASS',
}
print(json.dumps(report, ensure_ascii=False, indent=2))
