"""Ranking score and model quotation have separate validation states."""
import json
from quote_recovery import validate_completion as strict_validate
from api_adapter import RANGES

def validate_score(packet,response):
    if not isinstance(response,dict) or response.get('model') not in ['deepseek-flash','deepseek-v4.1-flash']:raise ValueError('unexpected model')
    choices=response.get('choices')
    if not isinstance(choices,list) or len(choices)!=1 or choices[0].get('finish_reason')!='stop':raise ValueError('incomplete response')
    value=json.loads(choices[0]['message']['content'])
    if not isinstance(value,dict) or value.get('pair_id')!=packet['pair_id']:raise ValueError('identity mismatch')
    score=value.get('score');level=value.get('level')
    if type(score) is not int or level not in RANGES or not RANGES[level][0]<=score<=RANGES[level][1]:raise ValueError('score/level mismatch')
    if any(not isinstance(value.get(k),str) or not value[k].strip() for k in ['reason','limitation']):raise ValueError('missing reason/limitation')
    if value.get('human_approved') is not False:raise ValueError('incorrect review identity')
    raw=value.get('source_quote')
    # Re-validation of the durable parsed object reconstructs the recorded raw quote.
    if raw is None and value.get('quotation_validation')=='invalid_model_quote_not_returned':raw=value.get('model_source_quote_raw')
    if not isinstance(raw,str):raise ValueError('model quote field missing/not string')
    canonical={k:value[k] for k in ['pair_id','score','level','reason','limitation','human_approved']}
    response_copy={**response,'choices':[dict(choices[0],message=dict(choices[0]['message'],content=json.dumps({**canonical,'source_quote':raw},ensure_ascii=False)))]}
    try:
        result=strict_validate(packet,response_copy)
        return {**result,'quotation_validation':'verified_literal_or_declared_typography','score_validation':'nonquotation_schema_valid'}
    except ValueError as exc:
        # No approximate substitution. A rank score is retained, the purported quote is not.
        return {**canonical,'source_quote':None,'model_source_quote_raw':raw,
                'quotation_validation':'invalid_model_quote_not_returned','quotation_error':str(exc),
                'score_validation':'nonquotation_schema_valid','evidence_support_validated':False}
