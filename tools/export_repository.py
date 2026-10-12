"""Export existing candidates and source-grounded experiments without modifying originals."""
import collections
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'finrisk-knowledge-base'
OUTPUTS = ROOT / 'outputs'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows(path):
    with path.open(encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))


def text(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((value.rstrip()+'\n').encode('utf-8'))


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def latest(folder):
    selected = {}
    revisions = {}
    for p in folder.rglob('*.json'):
        m = re.fullmatch(r'(F\d{6})_r0(?:_fix(\d+))?\.json', p.name)
        if not m:
            continue
        fid, rev = m[1], int(m[2] or 0)
        if fid in selected and revisions[fid] == rev:
            assert sha(p.read_bytes()) == sha(selected[fid].read_bytes()), (fid, rev)
        if fid not in selected or rev > revisions[fid]:
            selected[fid], revisions[fid] = p, rev
    return selected


def sharded(records, folder, per_part=100):
    """Returns per-file positions; each original document is kept as a single JSONL row."""
    folder.mkdir(parents=True, exist_ok=True)
    positions = {}
    for offset in range(0, len(records), per_part):
        target = folder / f'part-{offset//per_part+1:04}.jsonl'
        part = records[offset:offset+per_part]
        target.write_bytes(b''.join(canonical(row)+b'\n' for row in part))
        for line, row in enumerate(part, 1):
            positions[row['file_id']] = {'path':target.relative_to(OUT).as_posix(), 'line':line}
    return positions


def split_exact_lines(source, folder, per_part=5000):
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    count = 0
    sink = None
    try:
        with source.open('rb') as f:
            for line in f:
                if count % per_part == 0:
                    if sink: sink.close()
                    target = folder / f'part-{count//per_part+1:04}.jsonl'
                    sink = target.open('wb')
                    paths.append(target.relative_to(OUT).as_posix())
                sink.write(line)
                count += 1
    finally:
        if sink: sink.close()
    h = hashlib.sha256()
    for p in paths:
        h.update((OUT/p).read_bytes())
    assert h.hexdigest() == sha(source.read_bytes())
    return {'records':count, 'parts':paths, 'concatenated_sha256':h.hexdigest()}


def main():
    assert not OUT.exists() or not any(OUT.iterdir()), 'Export destination is nonempty; inspect before reusing.'
    OUT.mkdir(exist_ok=True)
    remaining_prepare = OUTPUTS/'FinRisk_剩余全量准备_20261011'
    blind = load(remaining_prepare/'blind_reserve_metadata.json')['records']
    blind_ids = {x['file_id'] for x in blind}
    assert len(blind_ids) == 360
    exports = []
    documents = []

    def add(fid, stage, proposal, source, metadata):
        assert fid not in blind_ids
        raw = proposal.read_bytes()
        draft = json.loads(raw.decode('utf-8-sig'))
        assert draft['file_id'] == fid
        if stage == 'early30':
            # Ten original early proposals omit status fields; their frozen batch remains pending.
            assert draft.get('semantic_status') in (None,'candidate')
            assert draft.get('human_review_status') in (None,'pending')
            assert metadata['human_review_status'] == 'pending'
        else:
            assert draft.get('semantic_status') == 'candidate'
            assert draft.get('human_review_status') == 'pending'
        body = source.encode('utf-8')
        assert sha(body) == metadata['text_sha256'], fid
        exports.append({'file_id':fid, 'batch':stage, 'semantic_status':'candidate',
                        'human_review_status':'pending', 'original_candidate_path':proposal.relative_to(ROOT).as_posix(),
                        'original_candidate_sha256':sha(raw), 'draft_json_sha256':sha(canonical(draft)),
                        'original_semantic_status':draft.get('semantic_status'),
                        'original_human_review_status':draft.get('human_review_status'),
                        'status_origin':'draft' if draft.get('semantic_status') else 'frozen_early30_batch', 'draft':draft})
        documents.append({'file_id':fid, 'batch':stage, 'text_sha256':sha(body),
                          'source_sha256':metadata['source_sha256'], 'text_id':metadata.get('text_id'),
                          'source_id':metadata.get('source_id'), 'text_version':metadata.get('text_version',1),
                          'full_text':source, 'document_metadata':metadata.get('document',{}),
                          'human_review_status':'pending', 'semantic_status':'candidate'})

    for stage, run_name, prepare_name, expected in [
        ('remaining8509','FinRisk_剩余全量运行_v2_20261011','FinRisk_剩余全量准备_20261011',8509),
        ('prior1000','FinRisk_1000运行_v1_20261011','FinRisk_1000准备_20261011',1000)]:
        selected = latest(OUTPUTS/run_name/'authored')
        expected_ids = {x['file_id'] for x in load(OUTPUTS/prepare_name/'selected.json')}
        assert len(selected)==expected and set(selected)==expected_ids
        for fid, proposal in sorted(selected.items()):
            task=load(OUTPUTS/prepare_name/'tasks'/f'{fid}.json')
            add(fid,stage,proposal,task['full_text'],task)
    early = OUTPUTS/'FinRisk_基础重建运行_v1_20261010'
    first100 = list(rows(early/'recall_v2/first100/documents.jsonl'))
    assert len(first100)==100
    for d in first100:
        p=early/d['proposal_path']
        assert sha(p.read_bytes())==d['proposal_sha256']
        source=(early/d['source_path']).read_bytes().decode('utf-8-sig')
        add(d['file_id'],'early100',p,source,d)
    early30 = OUTPUTS/'FinRisk_30份模型预审与人工验收候选_20261010'
    source30={d['official_file_id']:d for d in rows(early30/'data/documents.jsonl')}
    props30=list((early30/'proposals').rglob('F*.json'))
    assert len(source30)==len(props30)==30
    for p in props30:
        d=source30[p.stem]
        add(p.stem,'early30',p,d['full_text'],d)
    exports.sort(key=lambda x:x['file_id'])
    documents.sort(key=lambda x:x['file_id'])
    ids={x['file_id'] for x in exports}
    assert len(ids)==len(exports)==len(documents)==9639 and ids.isdisjoint(blind_ids)
    draft_positions=sharded(exports,OUT/'data/candidates')
    source_positions=sharded(documents,OUT/'data/sources')
    source_lookup={x['file_id']:x for x in documents}
    file_index=[]
    batches=collections.Counter()
    cases=behaviors=0
    for e in exports:
        fid=e['file_id'];d=e['draft'];s=source_lookup[fid]
        batches[e['batch']]+=1;cases+=len(d.get('cases',[]));behaviors+=len(d.get('behaviors',[]))
        file_index.append({'file_id':fid,'batch':e['batch'], 'candidate':draft_positions[fid],
                           'source':source_positions[fid], 'original_candidate_sha256':e['original_candidate_sha256'],
                           'draft_json_sha256':e['draft_json_sha256'], 'text_sha256':s['text_sha256'],
                           'cases':len(d.get('cases',[])), 'behaviors':len(d.get('behaviors',[])),
                           'label_policy_version':d.get('label_policy_version'),
                           'semantic_status':'candidate','human_review_status':'pending'})
    (OUT/'data/file_index.jsonl').write_bytes(b''.join(canonical(x)+b'\n' for x in file_index))
    dictionary=remaining_prepare/'dictionary/risk_type_dictionary.csv'
    tags=list(csv.DictReader(dictionary.read_text(encoding='utf-8-sig').splitlines()))
    assert len(tags)==27
    copy(dictionary,OUT/'dictionary/risk_type_dictionary.csv')
    for f in (remaining_prepare/'contracts').iterdir():
        if f.is_file(): copy(f,OUT/'contracts/recall-v2'/f.name)
    for f in (early30/'contracts').iterdir():
        if f.is_file(): copy(f,OUT/'contracts/early30'/f.name)
    projections=ROOT/'work/finrisk_retrieval_20261012/prepared_v2'
    projection_meta={'scope':'remaining8509 only; matches the frozen retrieval experiment',
                     'source_files':8509, 'semantic_status':'candidate'}
    for corpus,expected in [('structured',64109),('raw',20148)]:
        projection_meta[corpus]=split_exact_lines(projections/f'{corpus}.jsonl',OUT/f'indexes/2026-10-12/{corpus}')
        assert projection_meta[corpus]['records']==expected
    copy(projections/'manifest.json',OUT/'indexes/2026-10-12/original_projection_manifest.json')
    copy(projections/'projection_audit.jsonl',OUT/'indexes/2026-10-12/projection_audit.jsonl')
    save(OUT/'indexes/2026-10-12/manifest.json',projection_meta)
    evaluation=OUTPUTS/'FinRisk_召回实验_20261012'
    shutil.copytree(evaluation,OUT/'evaluation/2026-10-12',ignore=shutil.ignore_patterns('__pycache__','*.pyc','cache','vector_cache','*.npy'))
    quality=OUTPUTS/'FinRisk_剩余全量运行_v2_20261011/reports/质量验收_20261012'
    shutil.copytree(quality,OUT/'quality/2026-10-12',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for f in [early/'recall_v2/first100/manifest.json',early/'current_session90/first100_summary_v2.json',
              early30/'reports/model_review_summary.json',remaining_prepare/'prior30_policy_migration.json']:
        copy(f,OUT/'quality/earlier_batches'/(f.parent.name+'_'+f.name))
    doc_names=['FinRisk_基于教材第三章的离线知识库重建详细规划.md',
               'FinRisk_离线知识库重建任务清单_教材方法对应.md',
               'FinRisk_知识库重建任务清单_基础必做与锦上添花.md',
               'FinRisk_BM25_BGE_RRF_Rerank_召回测评方案_20261012.md',
               '第三章_知识库构建与智能体化RAG学习笔记.md',
               '第三章_知识库构建与智能体化RAG学习笔记.tex',
               '第三章_知识库构建与智能体化RAG学习笔记.pdf']
    for name in doc_names: copy(OUTPUTS/name,OUT/'docs'/name)
    counts={'documents':len(exports),'cases':cases,'behaviors':behaviors,'batches':dict(batches),
            'official_risk_labels':27,'human_approved_documents':0,'blind_reserved_excluded':360,
            'evaluation_documents':8509,'evaluation_queries':50}
    text(OUT/'.gitignore', '.env*\n.venv/\nvenv/\n.cache/\n__pycache__/\n*.pyc\n*.pem\n*.key\n*.p12\n*.pfx\n*.sqlite*\n*.npy\n*.safetensors\nmodels/\n')
    text(OUT/'.gitattributes','* -text\n')
    text(OUT/'README.md',f'''# FinRisk 重建知识库

本仓库存放保险违规风险判别所用知识库的重建候选与离线召回实验，更新日期2026-10-12。关联应用项目：[finrisk-workbench](https://github.com/wzz356/finrisk-workbench)。

**当前全部结构化记录仍是候选、待人工验收；公开保存不等于通过审核或已经替换应用默认知识库。**

## 数据规模

| 批次 | 文书数 | 状态 |
|---|---:|---|
| 最新剩余全量 | 8509 | 选择每份文书数字修订号最高的最新候选 |
| 此前1000份 | 1000 | 保留该批最新版本 |
| 早期基础100份 | 100 | 沿用已冻结的recall-v2候选 |
| 早期30份 | 30 | 保留原始契约与标签口径，尚未迁移为recall-v2 |
| 合计 | **9639** | **{cases}个主体案件记录、{behaviors}条行为记录** |

官方27类标签字典原样保存。360份盲验正文未读取、未上传。候选、修订历史、模型预审、部分保存方式的人类确认与全案人工批准是不同口径，本仓库不会将其混为通过验收。

## 数据入口

- [候选数据分片](data/candidates)：每行是一份文书，`draft`为原结构化提案；包装层记录批次、原稿SHA及可复核JSON内容SHA。
- [原文来源分片](data/sources)：每行一份`full_text`，保留文本SHA、来源ID、文本版本和文书元数据。
- [文书索引](data/file_index.jsonl)：9639行，给出每份候选/原文所在相对路径和行号，以及案件/行为数量。
- [官方27类字典](dictionary/risk_type_dictionary.csv)、[当前契约](contracts/recall-v2)、[早期30份契约](contracts/early30)。
- [检索投影](indexes/2026-10-12)：本轮8509份的64109个结构化证据单元和20148个原文切片，按5000行分片，按文件名拼接可恢复原投影字节与SHA。尚未去重、补齐父段或校准重排。

候选分片每份100文书，JSONL用UTF-8编码，每行独立JSON。可以按`data/file_index.jsonl`定位单份，或顺序读取全部分片。原文、引用、未确定字段、责任角色和既有问题都保留；来源文本SHA按UTF-8原样编码计算，不做换行转换。

## 本轮召回实验

[实验报告](evaluation/2026-10-12/实验报告.md) · [人工验收样例](evaluation/2026-10-12/人工验收样例.md) · [50条逐查询对照](evaluation/2026-10-12/逐查询对照.md) · [独立复标分歧](evaluation/2026-10-12/独立复标记录.md)

真实运行BM25 + bge-small-zh-v1.5双路Top100 → 等权RRF（k=60）Top100 → bge-reranker-base重排，随后按案例/文书max聚合。主指标评价Top5对风险机制、适用条件或边界的帮助，完整文书和实际返回片段分别判读。

| 结构化方案 | 有用文件@5 | 有用片段@5 |
|---|---:|---:|
| BM25 | 74.8% | 72.4% |
| BGE | 71.6% | 66.8% |
| 双路RRF | 82.0% | 79.6% |
| 双路RRF＋重排 | 81.6% | 76.0% |

50条合成开发查询、六组对照，671个查询—文件配对、945种返回上下文经模型辅助初评，另24个配对独立上下文复标。不是人工验收、盲测或官方竞赛成绩；只有8509份最新批次进入本轮实验，不能将其分数扩张到全部9639份候选。当前问题主要为重复单元、关键上下文缺失、行为证据关联与重排机制混淆。

## 质量与后续任务

[本轮质量验收报告](quality/2026-10-12/质量验收报告.md) · [原文/候选登记数量核对](quality/2026-10-12/最终登记与候选数量核对.json) · [规划与教材方法对应](docs/FinRisk_离线知识库重建任务清单_教材方法对应.md)

最新8509份中100份定向抽样已复核及修稿；不能据此宣称全库语义通过。已有本地账本登记4700份、3809份尚未登记，33份登记SHA需要同步；本仓库以最新候选为准并保留这些差异，不在发布时补写账本或批准记录。

下一步：合并重复检索单元且保留多主体归属，补齐父段/关键条件和正确行为关联，固定查询复测，校准reranker，再进行更广来源与27类覆盖的人工验收。

## 校验与使用说明

```powershell
python .\\tools\\verify_repository.py
```

该命令只使用Python标准库，核验全部发布文件SHA、9639份候选及来源对应、正文和提案内容哈希、27类字典，以及分片投影拼接SHA。校验通过证明导出完整性，不代替语义或人工验收。

[发布清单](manifest.json)保存全部相对路径、字节大小与SHA。[发布说明](docs/PUBLICATION.md)解释各阶段范围和历史路径。实验脚本按原执行版本保留；在新机器上重跑GPU检索需安装依赖、下载对应模型并配置本机路径，不能把归档脚本当作已经部署的服务。

模型权重、向量缓存、虚拟环境、凭据、教材原PDF和盲验正文均不在仓库。这里的学习笔记与LaTeX/PDF是本次生成的说明文档，不是教材原文件。
''')
    text(OUT/'docs/PUBLICATION.md','''# 公开发布说明

2026-10-12，按用户明确要求新建公开仓库并推送本次知识库重建成果。此前用户已确认公开上传监管文书原文及阶段成果；本次沿用该范围。

1. 最新8509、此前1000、早期100与早期30为互不重叠的来源集合，合计9639份，另360份盲验正文隔离且不在仓库。
2. 只导出各文书最新版本或已冻结提案，未重新生成、修改事实、补造字段、迁移早期30份标签或改变审批。原稿字节SHA与JSON内容SHA分别保存，不能把重序列化后的行字节SHA当作原稿SHA。
3. 早期30份保留旧标签门槛与契约；其零标签等情况不能伪称已采用召回优先策略。其他批次保留既有recall-v2标签与关联限制。
   其中10份早期原提案没有semantic_status/human_review_status字段；原稿不补写，包装层依据冻结批次状态标为candidate/pending并注明status_origin=frozen_early30_batch。
4. 原始文档中的绝对路径、access_scope=local_internal、尚未公开上传等说明是原运行时点的历史元数据；本仓库本次已公开，实际访问以GitHub可见性为准。读取数据请使用本仓库data/file_index.jsonl中的相对路径。
5. 检索评测、投影、模型辅助评分和完整性报告原样保存。历史SHA仍绑定原工作区输入；新增manifest核验本公开导出，而非声称所有历史路径在任何机器都存在。
   原实验交付完整性清单含本机验证缓存，本公开仓库省略cache/向量缓存，公开文件全集以根目录manifest.json为准。
6. 公开仓库没有改变应用默认KB、账本、审批及人工验收状态。重复归属、事件关联、片段完整性和语义质量问题详见质量与召回报告。
''')
    save(OUT/'export_statistics.json',counts)
    copy(Path(__file__),OUT/'tools/export_repository.py')
    print(json.dumps({'status':'exported','counts':counts,'file_count':sum(x.is_file() for x in OUT.rglob('*'))},ensure_ascii=False))


if __name__=='__main__':
    main()
