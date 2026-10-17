"""Verify this candidate release with Python's standard library; no model/network."""
import argparse,gzip,hashlib,json
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main(root):
 root=Path(root).resolve();manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
 for row in manifest['files']:
  p=(root/row['path']).resolve();assert p.is_relative_to(root)
  assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
 version=json.loads((root/'version.json').read_text(encoding='utf-8'))
 index={r['file_id']:r for r in map(json.loads,(root/'file_index.jsonl').read_text(encoding='utf-8').splitlines())}
 seen=set();digest=hashlib.sha256();cases=behaviors=corrected=0
 with gzip.open(root/version['default_read_entry'],'rb') as f:
  for number,line in enumerate(f,1):
   digest.update(line);r=json.loads(line);fid=r['file_id'];assert fid not in seen;seen.add(fid)
   h=hashlib.sha256(json.dumps(r['draft'],ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
   assert h==r['effective_draft_json_sha256']==index[fid]['effective_draft_json_sha256'] and index[fid]['line']==number
   assert r['source_sha256']==index[fid]['source_sha256'] and r['text_sha256']==index[fid]['text_sha256']
   assert r['publication_status']=='candidate' and r['human_review_status']=='pending' and r['full_document_human_approved'] is False
   is_patch=fid in version['corrected_files'];assert index[fid]['corrected']==is_patch
   assert r['origin']==('existing_5_file_correction' if is_patch else 'unchanged_V2_effective_draft')
   corrected+=is_patch;cases+=len(r['draft']['cases']);behaviors+=len(r['draft']['behaviors'])
 assert len(seen)==len(index)==9639 and corrected==5 and cases==15620 and behaviors==25186
 assert digest.hexdigest()==version['uncompressed_jsonl_sha256']
 print(json.dumps({'status':'passed','verified_files':len(manifest['files']),'candidate_documents':len(seen),'corrected_files':corrected,
  'cases':cases,'behaviors':behaviors,'all_draft_and_source_index_fingerprints_verified':True,'model_or_network_calls':0},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--release',type=Path,default=Path(__file__).resolve().parent);main(p.parse_args().release)
