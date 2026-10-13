"""Freeze reviewed recursive/navigation inputs before actual retrieval."""
from pathlib import Path
import e05_runner as e
from e07 import OUT,demo,WORK


def main():
    inputs=demo.read_json(OUT / 'freeze_cluster3.json')['files_sha256']
    for path,digest in inputs.items():assert demo.sha_file(path)==digest
    extras=[OUT / 'freeze_cluster3.json', OUT / 'clusters_level3.json',
        OUT / 'clusters_level3.json.run.json', OUT / 'summaries_level3.jsonl',OUT / 'tree_nodes.jsonl',
        WORK / 'e05_summary_review.md',WORK / 'tests_root_green.log',demo.OUT / 'queries.jsonl',demo.OUT / 'input_freeze.json']
    for level in (1,2,3):extras.append(OUT / f'clusters_level{level}.json.token_audit.jsonl')
    e04,base=e.modules()
    extras+=e.dependencies(e04,base,e.read_json(e04.LEGACY_RUN))
    for path in extras:inputs[str(Path(path).resolve())]=demo.sha_file(path)
    assert '最终' in (WORK / 'e05_summary_review.md').read_text(encoding='utf-8')
    assert demo.sha_file(WORK / 'e05_summary_review.md')=='221ece088819273374616231c49069f9f83ee57b6f7738406fc54fb00abed55e'
    demo.write_new(OUT / 'freeze_retrieve.json',dict(files_sha256=inputs,models_reviewed=True,
        human_approved=False,weights=[1,1],node_counts={'DIR':6,'TREE':7},summary_as_evidence=False))
    e.validate_freeze(OUT / 'freeze_retrieve.json',extras+[OUT / 'queries.jsonl',OUT / 'leaves.jsonl',OUT / 'directory_nodes.jsonl',OUT / 'tree_nodes.jsonl'])
    print({'frozen_files':len(inputs),'status':'passed_before_retrieval'})


if __name__=='__main__':main()
