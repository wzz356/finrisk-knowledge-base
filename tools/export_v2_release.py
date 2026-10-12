"""Publish the frozen offline V2, retaining V1 inputs and byte-exact payload maps."""
import collections
import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from v2_payloads import LIMIT, pack_file, sha

ROOT = Path(__file__).resolve().parents[2]
PUB = Path(__file__).resolve().parent
REPO = ROOT.parents[1] / 'finrisk-v2-publish'
SOURCE = ROOT / 'outputs/FinRisk_知识库V2_20261012'
VERSION = REPO / 'versions/v2-20261012'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def rows(path):
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def text(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8')


def main(resume=False):
    if VERSION.exists() and not resume:
        raise FileExistsError('release directory already exists; do not overwrite a prepared release')
    VERSION.mkdir(parents=True, exist_ok=resume)
    original = json.loads((SOURCE / 'delivery_manifest.json').read_text(encoding='utf-8'))
    maps, skipped = [], []
    for item in original['files']:
        path = ROOT / item['path']
        relative = None
        prefix = 'outputs/FinRisk_知识库V2_20261012/'
        if item['path'].startswith(prefix):
            relative = item['path'][len(prefix):]
            if relative.startswith('registration_final/') and relative not in {
                'registration_final/registration_plan.jsonl', 'registration_final/registration_receipts.jsonl',
                'registration_final/registration_summary.json', 'registration_final/registration_verification.json',
                'registration_final/before_sqlite/backups.json',
            }:
                relative = None
        elif item['path'].startswith(('work/finrisk_v2_20261012/', 'work/finrisk_v2_frozen8509_gpu/')):
            relative = item['path']
        if relative is None:
            skipped.append({'path': item['path'], 'reason': 'local ledger backup/targets/validator inputs; facts retained in snapshots and candidates, receipts and verification published'})
            continue
        if sha(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('frozen source drift: ' + item['path'])
        maps.append(pack_file(path, VERSION, relative))
        if len(maps) % 25 == 0:
            print(json.dumps({'event': 'payloads_exported', 'count': len(maps)}), flush=True)
    for name in ('delivery_manifest.json', 'delivery_verification.json'):
        maps.append(pack_file(SOURCE / name, VERSION, 'baseline/' + name))
    # Live human evidence was created after freezing; export it as a separate latest snapshot.
    for path in sorted((SOURCE / 'human_acceptance').rglob('*')):
        if path.is_file() and path.suffix in ('.md', '.json'):
            maps.append(pack_file(path, VERSION, path.relative_to(SOURCE).as_posix()))
    for name in ('manifest.json', 'export_statistics.json', 'README.md'):
        maps.append(pack_file(ROOT / 'finrisk-knowledge-base' / name, VERSION, 'baseline/v1_' + name))
    # The query set and exact legacy runner are needed to interpret/replay the frozen results.
    maps.append(pack_file(ROOT / 'outputs/FinRisk_召回实验_20261012/queries.jsonl', VERSION, 'evaluation/queries.jsonl'))
    maps.append(pack_file(ROOT / 'work/finrisk_retrieval_20261012/runner.py', VERSION, 'work/finrisk_retrieval_20261012/runner.py'))
    for name in ('v2_payloads.py', 'verify_v2_release.py', 'test_v2_payloads.py', 'export_v2_release.py'):
        shutil.copyfile(PUB / name, REPO / 'tools' / name)

    base_index = {r['file_id']: r for r in rows(REPO / 'data/file_index.jsonl')}
    dictionary_path = REPO / 'dictionary/risk_type_dictionary.csv'
    with dictionary_path.open(encoding='utf-8-sig', newline='') as stream:
        tags = {r['risk_tag'] for r in csv.DictReader(stream)}
    assert len(tags) == 27
    candidate_dir = VERSION / 'data/candidates'
    candidate_dir.mkdir(parents=True, exist_ok=resume)
    buffer = bytearray()
    number = line_number = 0
    index, seen = [], set()
    counts = collections.Counter()
    changed = 0

    def flush():
        nonlocal number, line_number
        if buffer:
            (candidate_dir / f'part-{number:04d}.jsonl').write_bytes(buffer)
            buffer.clear()
            line_number = 0

    for snapshot in rows(SOURCE / 'normalized_final/extensions/candidate_snapshots.jsonl'):
        reference = snapshot['effective_draft_reference']
        if reference not in ('base_draft', 'effective_draft'):
            raise ValueError('unknown effective draft reference')
        fid, draft = snapshot['file_id'], snapshot[reference]
        if not isinstance(draft, dict):
            raise ValueError('declared effective draft reference is not an object')
        assert fid not in seen and draft['file_id'] == fid
        seen.add(fid)
        dsha = hashlib.sha256(canonical(draft)).hexdigest()
        assert dsha == snapshot['effective_draft_json_sha256']
        base = base_index[fid]
        assert base['draft_json_sha256'] == snapshot['base_draft_json_sha256']
        assert base['text_sha256'] == snapshot['text_sha256']
        overlay = dsha != snapshot['base_draft_json_sha256']
        changed += overlay
        for behavior in draft['behaviors']:
            assert all(tag['tag'] in tags for tag in behavior.get('risk_tags', []))
        wrapper = {'file_id': fid, 'batch': snapshot['batch'], 'draft': draft,
                   'draft_json_sha256': dsha, 'base_draft_json_sha256': snapshot['base_draft_json_sha256'],
                   'text_sha256': snapshot['text_sha256'], 'source_sha256': snapshot['source_sha256'],
                   'text_version': snapshot['text_version'], 'overlay_applied': overlay,
                   'semantic_status': 'candidate', 'human_review_status': 'pending',
                   'version': 'v2-20261012', 'source': base['source'], 'base_candidate': base['candidate'],
                   'provenance': {'original_candidate_byte_sha256': base['original_candidate_sha256'],
                                  'original_wrapper_metadata': snapshot['wrapper_metadata'],
                                  'original_byte_sha_applies_to_base_authored_file': True},
                   'partial_human_acceptance': 'see versions/v2-20261012/human_acceptance; not full document approval'}
        raw = canonical(wrapper) + b'\n'
        if len(raw) > LIMIT:
            raise ValueError('single candidate exceeds part limit')
        if buffer and (line_number >= 100 or len(buffer) + len(raw) > LIMIT):
            flush()
        if not buffer:
            number += 1
        line_number += 1
        buffer.extend(raw)
        index.append({'file_id': fid, 'batch': snapshot['batch'],
                      'candidate': {'path': f'versions/v2-20261012/data/candidates/part-{number:04d}.jsonl', 'line': line_number},
                      'source': base['source'], 'base_candidate': base['candidate'],
                      'draft_json_sha256': dsha, 'base_draft_json_sha256': snapshot['base_draft_json_sha256'],
                      'text_sha256': snapshot['text_sha256'], 'overlay_applied': overlay,
                      'cases': len(draft['cases']), 'behaviors': len(draft['behaviors'])})
        counts.update(documents=1, cases=len(draft['cases']), behaviors=len(draft['behaviors']))
    flush()
    assert len(seen) == len(base_index) == 9639 and counts['cases'] == 15620 and counts['behaviors'] == 25186 and changed == 157
    (VERSION / 'data/file_index.jsonl').write_bytes(b''.join(canonical(r) + b'\n' for r in index))
    names = [m['path'] for m in maps]
    assert len(names) == len(set(names))
    save(VERSION / 'payload_map.json', {'format': 'lossless-original-payload-map-v1', 'payloads': maps,
                                      'compression': 'large JSONL represented by same-named directory of gzip parts; original order/bytes preserved'})
    save(VERSION / 'publication_statistics.json', {
        **dict(counts), 'changed_candidate_documents': changed, 'official_risk_labels': 27,
        'candidate_parts': number, 'human_review_items': 9, 'human_approved_full_documents': 0,
        'v2_result_records': 400, 'total_comparison_groups': 14, 'query_method_records_including_v1': 700,
        'evaluation_unique_query_file_pairs': 1000, 'evaluation_contexts': 1670,
        'scope_variants': {'same8509': 8509, 'all9639': 9639}, 'queries': 50,
        'application_default_switched': False, 'retrieval_improvement_experiments_started': False,
        'excluded': ['360 reserved blind document bodies', 'credentials', 'model weights', 'vector caches', 'venvs',
                     'original textbook PDF', 'local SQLite backups', 'duplicate registration targets/validator inputs',
                     'failed/partial runs', 'duplicate recovery output trees'],
        'excluded_frozen_local_files': skipped,
    })
    text(VERSION / 'README.md', '''# FinRisk V2：9639份离线候选知识库与复测

这是V2发布版本。统一9639份文书、15620个主体案件、25186条行为，157份有效修订；早期30份已迁移官方27类召回优先标签。全量机械检查、登记对账和保存输入恢复通过。当前有9项展示字段/片段的人工判断，完整文书批准0，应用默认库未切换。

## 直接阅读

- [9639份有效候选](data/candidates)、[文书定位索引](data/file_index.jsonl)。每份候选直接包含当前有效draft，保留基线稿/来源/版本SHA与相对定位。
- 原文共享仓库根目录[data/sources](../../data/sources)，原稿共享[data/candidates](../../data/candidates)。版本索引source/base_candidate的path均相对仓库根目录。
- [V2重建与召回复测报告](V2重建与召回复测报告.md)、[任务清单](任务清单状态_V2.md)、[阅读导航](normalized_final/INDEX.md)。
- [14组指标](metrics/metrics.json)、[逐查询指标](metrics/per_query_metrics.jsonl)、[固定50查询](evaluation/queries.jsonl)。
- [同8509结果](retrieval/same8509_final_results.jsonl)、[全9639结果](retrieval/all9639_results.jsonl)。两范围各200条真实结果。
- [质量冻结](quality/input_freeze.json)、[登记对账](registration_final/registration_verification.json)、[恢复报告](recovery/recovery_report.json)。
- [最新人工验收记录](human_acceptance/验收进度.md)、[后续模型审核委托](human_acceptance/delegated_review_authorization.json)。

冻结报告中的human0/尚未发布是当时历史状态；以上最新人工记录和本发布版本说明当前状态，不覆盖原证据。

## 当前检索效果

| 全9639结构化方案 | 有用文件@5 | 有用片段@5 |
|---|---:|---:|
| BM25 | 78.4% | 78.8% |
| BGE | 67.2% | 61.2% |
| 双路RRF | 77.6% | 73.6% |
| RRF＋rerank | 74.8% | 72.8% |

BM25改善，RRF/rerank相对V1回退。同8509受控范围也显示回退，原基线保留。50条是开发查询，模型评分不是全库人工金标；nDCG只针对联合已评池，不能称全库Recall。9项人工核定不会自动改写冻结指标。16处全文/片段判断分歧、旧关注队列未全审、责任关系表0等限制详见总报告。

## 大文件读取与无损恢复

超过20MiB的JSONL以“同名目录”保存，目录内是按原行顺序的gzip分片和parts.json；因此上面的同名链接可以直接打开分片目录。所有八表、引用/ID映射、阅读索引、两范围raw/structured投影、完整结果及评分内容均已保存，没有只上传摘要。

克隆整个仓库后，核验本版本：

```powershell
python .\\tools\\verify_v2_release.py --repo .
```

恢复原始文件名、逐字节内容及SHA到一个空目录：

```powershell
python .\\tools\\v2_payloads.py --version .\\versions\\v2-20261012 --destination .\\restored-v2
```

恢复只用Python标准库。恢复输出仍保留原运行时点的绝对路径等历史元数据；跨机器GPU复跑需安装依赖、取得对应BGE/reranker和配置路径，仓库不含模型权重或向量缓存。候选与共享原文直接从整个仓库读取，无需为了单份候选恢复全部大文件。

[公开文件清单](publication_manifest.json)核验本目录实际公开文件；[原始载荷映射](payload_map.json)核验拆分前SHA；[本地原冻结清单](baseline/delivery_manifest.json)包含未发布的本地冗余/SQLite资产，仅作历史证据，不把它当公开文件全集。
''')
    old_readme = (ROOT / 'finrisk-knowledge-base/README.md').read_text(encoding='utf-8')
    text(REPO / 'docs/V1_README_20261012.md', old_readme)
    text(REPO / 'README.md', '''# FinRisk 重建知识库

**当前版本：[V2 / 9639份知识库与召回复测](versions/v2-20261012)。** 关联应用：[finrisk-workbench](https://github.com/wzz356/finrisk-workbench)。

V2完成统一八表、稳定ID、原文证据绑定、阅读入口和两范围检索投影，修订157份有效候选，早期30份迁移官方27类标签。全量机械检查、8509主批次登记对账与保存输入恢复通过。当前9项展示字段/片段已人工判断，完整文书批准0；后续复核由用户委托助手，判断来源保持模型复核。应用默认库未切换。

## 当前数据与实验入口

- [9639份V2有效候选](versions/v2-20261012/data/candidates)、[文书定位索引](versions/v2-20261012/data/file_index.jsonl)、[共享原文](data/sources)。
- [V2重建与召回复测报告](versions/v2-20261012/V2重建与召回复测报告.md)、[任务清单进度](versions/v2-20261012/任务清单状态_V2.md)。
- [八表与阅读导航](versions/v2-20261012/normalized_final/INDEX.md)、[检索投影](versions/v2-20261012/indexes)、[完整实验结果](versions/v2-20261012/retrieval)、[完整评分与指标](versions/v2-20261012/metrics)。
- [人工验收记录](versions/v2-20261012/human_acceptance/验收进度.md)、[质量/登记/恢复及使用说明](versions/v2-20261012/README.md)。

| 全9639结构化方案 | 有用文件@5 | 有用片段@5 |
|---|---:|---:|
| BM25 | 78.4% | 78.8% |
| BGE | 67.2% | 61.2% |
| BM25+BGE→RRF | 77.6% | 73.6% |
| RRF→rerank | 74.8% | 72.8% |

50条开发查询、真实BGE及reranker；全文与实际片段分别模型评分。BM25改善，双路/Rerank回退，尚未切默认库。两范围V2共400结果，加V1六组后14组/700记录；1000个query-file配对、1670种片段。nDCG是池内条件指标，不能称全库Recall或官方竞赛成绩。

## 版本与校验

根目录data/candidates、indexes/2026-10-12、evaluation/2026-10-12及quality/2026-10-12保留V1基线；[V1历史说明](docs/V1_README_20261012.md)。读取当前候选请用versions/v2-20261012/data/candidates。V2原文共享根data/sources，字典仍是[官方27类](dictionary/risk_type_dictionary.csv)。

```powershell
python .\\tools\\verify_repository.py
python .\\tools\\verify_v2_release.py --repo .
```

大JSONL采用无损gzip分片，有同名目录及恢复工具，详见[V2使用说明](versions/v2-20261012/README.md)。[根发布清单](manifest.json)核验本仓库实际文件，[V2清单](versions/v2-20261012/publication_manifest.json)核验版本载荷。

360份预留正文、凭据、教材原PDF、模型权重、虚拟环境、向量缓存和本地SQLite备份不在新版本中。此版本是离线候选与实验归档，机械通过不等于全案语义审核或正式应用上线。
''')
    version_files = {p.relative_to(VERSION).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)}
                     for p in sorted(VERSION.rglob('*')) if p.is_file()}
    assert max(x['bytes'] for x in version_files.values()) <= LIMIT
    save(VERSION / 'publication_manifest.json', {'version': 'v2-20261012', 'files': version_files,
                                               'counts': dict(counts), 'frozen_local_manifest_sha256': sha(SOURCE / 'delivery_manifest.json'),
                                               'human_review_items': 9, 'full_document_approval_count': 0})
    root_manifest = json.loads((ROOT / 'finrisk-knowledge-base/manifest.json').read_text(encoding='utf-8'))
    root_manifest.update(current_version='v2-20261012', current_version_path='versions/v2-20261012',
                         v1_input_data_retained=True, current_human_review_items=9, full_document_approval_count=0)
    root_manifest['files'] = {p.relative_to(REPO).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)}
                              for p in sorted(REPO.rglob('*')) if p.is_file() and '.git' not in p.relative_to(REPO).parts and p != REPO / 'manifest.json'}
    save(REPO / 'manifest.json', root_manifest)
    report = {'status': 'exported', 'candidate_documents': 9639, 'changed_candidates': 157,
              'original_payloads': len(maps), 'version_files': len(version_files) + 1,
              'version_bytes': sum(r['bytes'] for r in version_files.values()), 'root_files': len(root_manifest['files']),
              'max_new_file_bytes': max(r['bytes'] for r in version_files.values()), 'human_review_items': 9,
              'skipped_local_duplicates': len(skipped)}
    save(PUB / 'export_report.json', report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true')
    main(parser.parse_args().resume)
