"""Verify the published dataset using only Python's standard library."""
import collections
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def lines(path):
    with path.open(encoding='utf-8') as f:
        for n,line in enumerate(f,1):
            if line.strip(): yield n,json.loads(line)


def main():
    manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    for relative,meta in manifest['files'].items():
        path=ROOT/relative
        assert path.resolve().is_relative_to(ROOT.resolve()), relative
        assert path.is_file() and path.stat().st_size==meta['bytes'],relative
        assert sha_file(path)==meta['sha256'],relative
    candidates={};sources={};batches=collections.Counter();cases=behaviors=0
    for part in sorted((ROOT/'data/candidates').glob('part-*.jsonl')):
        for line,row in lines(part):
            fid=row['file_id'];d=row['draft']
            assert fid not in candidates and d['file_id']==fid
            assert hashlib.sha256(canonical(d)).hexdigest()==row['draft_json_sha256'],fid
            assert row['semantic_status']=='candidate' and row['human_review_status']=='pending',fid
            assert row['original_semantic_status']==d.get('semantic_status')
            assert row['original_human_review_status']==d.get('human_review_status')
            if row['status_origin']=='frozen_early30_batch':
                assert row['batch']=='early30' and d.get('semantic_status') is None
            else:
                assert d.get('semantic_status')=='candidate' and d.get('human_review_status')=='pending'
            nc,nb=len(d.get('cases',[])),len(d.get('behaviors',[]))
            cases+=nc;behaviors+=nb;batches[row['batch']]+=1
            candidates[fid]={'path':part.relative_to(ROOT).as_posix(),'line':line,
                             'draft_json_sha256':row['draft_json_sha256'],
                             'original_candidate_sha256':row['original_candidate_sha256'],
                             'cases':nc,'behaviors':nb,'batch':row['batch']}
    for part in sorted((ROOT/'data/sources').glob('part-*.jsonl')):
        for line,row in lines(part):
            fid=row['file_id'];assert fid not in sources
            assert hashlib.sha256(row['full_text'].encode('utf-8')).hexdigest()==row['text_sha256'],fid
            sources[fid]={'path':part.relative_to(ROOT).as_posix(),'line':line,'text_sha256':row['text_sha256']}
    index={}
    for _,row in lines(ROOT/'data/file_index.jsonl'):
        fid=row['file_id'];assert fid not in index
        c,s=candidates[fid],sources[fid]
        assert row['candidate']=={'path':c['path'],'line':c['line']}
        assert row['source']=={'path':s['path'],'line':s['line']}
        for k in ['draft_json_sha256','original_candidate_sha256','cases','behaviors','batch']:
            assert row[k]==c[k],(fid,k)
        assert row['text_sha256']==s['text_sha256']
        index[fid]=row
    assert set(index)==set(candidates)==set(sources) and len(index)==9639
    assert dict(batches)=={'remaining8509':8509,'prior1000':1000,'early100':100,'early30':30}
    stats=manifest['counts']
    assert stats['documents']==len(index) and stats['cases']==cases and stats['behaviors']==behaviors
    dictionary=ROOT/'dictionary/risk_type_dictionary.csv'
    with dictionary.open(encoding='utf-8-sig',newline='') as f: tags=list(csv.DictReader(f))
    assert len(tags)==len({x['risk_tag'] for x in tags})==27
    projection=json.loads((ROOT/'indexes/2026-10-12/manifest.json').read_text(encoding='utf-8'))
    for corpus,expected in [('structured',64109),('raw',20148)]:
        h=hashlib.sha256();count=0
        for relative in projection[corpus]['parts']:
            data=(ROOT/relative).read_bytes();h.update(data);count+=len(data.splitlines())
        assert count==projection[corpus]['records']==expected
        assert h.hexdigest()==projection[corpus]['concatenated_sha256']
    print(json.dumps({'status':'passed','hashed_files':len(manifest['files']),
                      'documents':len(index),'cases':cases,'behaviors':behaviors,'batches':dict(batches),
                      'official_labels':27,'structured_projection_units':64109,'raw_projection_units':20148,
                      'human_approved_documents':0},ensure_ascii=False))


if __name__=='__main__':
    main()
