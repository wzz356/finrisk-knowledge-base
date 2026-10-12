"""Join separately judged, non-overlapping contexts; do not produce any grades."""
from run_v2 import ROOT,read_rows,canonical,sha_file,save_json

def main():
    base=ROOT/'work/finrisk_v2_20261012/judgments'
    names=['same8509_p1.jsonl','same8509_p2.jsonl','same8509_p3.jsonl','all9639_supplemental.jsonl']
    pool={};origins={};seenctx=set()
    for name in names:
        origins[name]=sha_file(base/name)
        for row in read_rows(base/name):
            pid=row['pair_id'];out=pool.setdefault(pid,{'pair_id':pid,'contexts':[]})
            if 'help_grade' in row:
                fields={k:v for k,v in row.items() if k not in ['pair_id','contexts']}
                if 'help_grade' in out and {k:v for k,v in out.items() if k not in ['pair_id','contexts']}!=fields:
                    raise ValueError('conflicting independent file grade: '+pid)
                out.update(fields)
            for context in row['contexts']:
                key=(pid,context['context_id'])
                if key in seenctx:raise ValueError('duplicate context judgment: '+str(key))
                seenctx.add(key);out['contexts'].append(context)
    if len(pool)!=669 or len(seenctx)!=725:raise ValueError('new judgment population incomplete')
    path=ROOT/'outputs/FinRisk_知识库V2_20261012/evaluation/new_judgments.jsonl'
    path.write_bytes(b''.join(canonical(pool[p])+b'\n' for p in sorted(pool)))
    save_json(path.with_suffix('.provenance.json'),{'input_sha256':origins,'pairs':len(pool),
        'contexts':len(seenctx),'output_sha256':sha_file(path),'code_sha256':sha_file(__file__),
        'grading':'Joined existing individual source-read model judgments; no score generation; human0'})
    print({'pairs':len(pool),'contexts':len(seenctx)})

if __name__=='__main__':main()
