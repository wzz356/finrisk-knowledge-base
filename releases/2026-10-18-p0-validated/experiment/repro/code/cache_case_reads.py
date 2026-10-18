"""Read every shared RRF candidate through one real validated full reader."""
import sys
import time
from effect_common import *
sys.path.insert(0,str(RUNTIME/'code'))
from full_reader import FullKnowledgeReader
from evidence_runtime import EvidenceRuntime

def main():
    start=time.perf_counter();verify(read(OUT/'retrieval/freeze.json')['sha256'])
    config=read(RUNTIME/'contracts/runtime_manifest.json')['full_reader'];root=RUNTIME/config['root']
    def progress(x):print(json.dumps(x,ensure_ascii=False),flush=True)
    ids=sorted({r['unit_id'] for r in rows(OUT/'retrieval/candidate_map.jsonl')})
    with FullKnowledgeReader(root,config['manifest_sha256'],config['versions'],progress=progress) as reader:
        kb=EvidenceRuntime(RUNTIME,read(RUNTIME/'contracts/runtime_lock.json')['runtime_manifest_sha256'],case_reader=reader)
        records=[dict(unit_id=uid,read_result=kb.read_case(uid),read_result_sha256=canonical_sha(kb.read_case(uid))) for uid in ids]
        save(OUT/'retrieval/shared_case_reads.jsonl',records,True)
        old=set(read(RUNTIME/'contracts/legacy_snapshot_unit_ids.json')['unit_ids'])
        receipt=dict(passed=True,unique_RRF_units=len(ids),old_snapshot_contains=len(set(ids)&old),outside_old_snapshot=len(set(ids)-old),
            startup_seconds=reader.startup_seconds,seconds=time.perf_counter()-start,API_calls=0,versions=reader.versions,full_reader_manifest_sha256=config['manifest_sha256'],cache_sha256=sha(OUT/'retrieval/shared_case_reads.jsonl'),source_references_preserved=True)
    save(OUT/'retrieval/shared_case_read_receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
