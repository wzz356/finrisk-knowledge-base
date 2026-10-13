"""Transparent wider-checklist sensitivity; exact historical bindings, not fresh primary grades."""
from collections import defaultdict
from e07 import OUT,demo
import e06


def main():
    items=demo.rows(OUT / 'e05_reading_pool.jsonl')
    sources=demo.source_map()
    packets={p['query_id']:p for p in demo.rows(demo.OUT / 'evidence_packets.jsonl')}
    judgments={j['query_id']:j for j in demo.rows(demo.OUT / 'model_judgments.jsonl')}
    historical={}
    for parent in demo.rows(demo.OUT / 'display_results.jsonl'):
        qid=parent['query_id'];packet=packets[qid];judgment=judgments[qid]
        e06.validate_parent_binding(parent,packet,judgment,sources)
        for hit,assessment in zip(packet['evidence'],judgment['evidence_assessments']):
            key=(qid,packet['input_text'],hit['file_id'],hit['unit_id'],hit['text'],hit['source_text_sha256'])
            historical[key]=assessment
    manual={
        ('D001','F007588'):dict(helpful=False,quote='',reason='登记/告知书等案由未具体涉及重疾给付或免责。'),
        ('D016','F008940'):dict(helpful=True,quote='销售人员存在宣传内容与保险条款等不一致问题、未向投保人告知附加险保险费等内容',
            reason='宽口径仅计泛化条款一致性核查帮助；未给期满给付、保证性或金额条件，不能作同机制证据。'),
        ('D016','F008944'):dict(helpful=True,quote='销售人员存在宣传内容与保险条款等不一致问题、未向投保人告知附加险保险费等内容',
            reason='宽口径仅计泛化条款一致性核查帮助；未给期满给付、保证性或金额条件，不能作同机制证据。')}
    results=[]
    for item in items:
        key=(item['query_id'],item['query_text'],item['file_id'],item['unit_id'],item['displayed_text'],item['source_sha256'])
        if key in historical:assessment=historical[key];origin='exact_V3_query_source_display_binding_historical'
        else:assessment=manual[(item['query_id'],item['file_id'])];origin='root_session_new_wider_checklist_opinion'
        if assessment['helpful']:
            assert assessment['quote'] in item['displayed_text'] and any(assessment['quote'] in s['text'] for s in item['source_segments'])
        results.append(dict(item_id=item['item_id'],item_sha256=demo.sha_json(item),assessment=assessment,
                            origin=origin,human_approved=False,primary_fresh_judgment=False))
    by_id={r['item_id']:r for r in results}
    grouped=defaultdict(lambda:defaultdict(list))
    for assignment in demo.rows(OUT / 'e05_reading_assignments.jsonl'):
        grouped[assignment['arm']][assignment['query_id']].append(by_id[assignment['item_id']]['assessment']['helpful'])
    metric={arm:dict(helpful=sum(sum(v) for v in qs.values()),positions=80,
            covered_queries=sum(any(v) for v in qs.values()),per_query={qid:sum(v) for qid,v in qs.items()}) for arm,qs in grouped.items()}
    demo.write_new(OUT / 'e05_sensitivity_bindings.jsonl',results,True)
    demo.write_new(OUT / 'e05_sensitivity.json',dict(status='complete_wider_checklist_sensitivity',
        exact_historical_contexts=sum(r['origin'].startswith('exact_V3') for r in results),
        new_wider_context_opinions=3,arms=metric,human_approved=False,primary_fresh_judgment=False,
        interpretation='Historical broad checkpoint utility plus three new explicit model opinions; not independent fresh grading. Primary comparison remains fresh 83-context unified judgments.'))
    print(metric)


if __name__=='__main__':main()
