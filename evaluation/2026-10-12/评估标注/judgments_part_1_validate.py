import collections
import hashlib
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding='utf-8')
D = pathlib.Path(__file__).parent
srcpath = D / 'judgment_part_1.jsonl'
outpath = D / 'judgments_part_1.jsonl'
src = [json.loads(s) for s in srcpath.read_text(encoding='utf-8').splitlines()]
out = [json.loads(s) for s in outpath.read_text(encoding='utf-8').splitlines()]
fields = {'pair_id','help_grade','help_type','mechanism_match','conditions_match','source_quote','reason','limitations','misleading_risk','contexts'}
cfields = {'context_id','help_grade','evidence_quote','reason','misleading_risk'}
assert len(src) == len(out) == 237
assert len({v['pair_id'] for v in out}) == len(out)
assert {v['pair_id'] for v in out} == {v['pair_id'] for v in src}
byid = {v['pair_id']: v for v in src}
actual = set()
expected = {(r['pair_id'], c['context_id']) for r in src for c in r['contexts']}
for v in out:
    assert set(v) == fields
    assert type(v['help_grade']) is int and 0 <= v['help_grade'] <= 3
    assert v['help_type'] in {'support','boundary','irrelevant'}
    assert v['mechanism_match'] in {'same','partial','different'}
    assert v['conditions_match'] in {'compatible','partial','conflict','unknown'}
    assert type(v['misleading_risk']) is bool
    assert isinstance(v['limitations'], list) and all(isinstance(s, str) for s in v['limitations'])
    assert isinstance(v['contexts'], list)
    for key in ['pair_id','source_quote','reason']:
        assert isinstance(v[key], str)
    r = byid[v['pair_id']]
    q = v['source_quote']
    if v['help_grade'] >= 2:
        assert q
    if q:
        assert q in r['full_source_text']
    cmap = {c['context_id']:c for c in r['contexts']}
    assert len(v['contexts']) == len(cmap) == len(r['contexts'])
    assert {c['context_id'] for c in v['contexts']} == set(cmap)
    for c in v['contexts']:
        assert set(c) == cfields
        assert type(c['help_grade']) is int and 0 <= c['help_grade'] <= 3
        assert type(c['misleading_risk']) is bool
        for key in ['context_id','evidence_quote','reason']:
            assert isinstance(c[key], str)
        key = (v['pair_id'], c['context_id'])
        assert key not in actual
        actual.add(key)
        q = c['evidence_quote']
        if c['help_grade'] >= 2:
            assert q
        if q:
            assert q in cmap[c['context_id']]['text'] and q in r['full_source_text']
assert actual == expected and len(actual) == 334
og = dict(sorted(collections.Counter(v['help_grade'] for v in out).items()))
cg = dict(sorted(collections.Counter(c['help_grade'] for v in out for c in v['contexts']).items()))
digest = hashlib.sha256(outpath.read_bytes()).hexdigest()
input_digest = hashlib.sha256(srcpath.read_bytes()).hexdigest()
text = f'''# 第1批模型辅助评分

已逐条阅读指定完整原文及各片段，保存237个query-file、334个context；这是模型辅助评分，非人工验收。

文件分值分布：{og}；片段分值分布：{cg}。

全集唯一覆盖、字段类型/枚举、0—3范围、所有非空引文在原文精确匹配、片段引文同时匹配text及原文检查通过。关键条件截断单独标记；未借原文补齐片段证据。

仅使用指定规范与第1批输入，未读取算法结果、其他评分或已知正例，未联网或调用付费API。评分文件已冻结。

judgments_part_1.jsonl SHA256：`{digest}`

judgment_part_1.jsonl SHA256：`{input_digest}`
'''
(D / 'notes_part_1.md').write_text(text, encoding='utf-8', newline='\n')
print(json.dumps({'pairs':len(out),'contexts':len(actual),'validation':'passed','grades':og,'context_grades':cg,'output_sha256':digest,'input_sha256':input_digest}, ensure_ascii=False))
