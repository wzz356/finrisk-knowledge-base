"""Offline, version-bound normalization of candidate wrappers; no semantic approval.

The contract is a typed-field contract, not a complete JSON Schema.  Exact text
location verifies the exported text only, not an unavailable original PDF/file.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / 'finrisk-knowledge-base/contracts/recall-v2/schema.json'
VERSION = 'finrisk-candidate-normalization-v2.1'
PRIMARY = {'source_inventory': 'source_id', 'documents': 'text_id', 'cases': 'case_id',
           'behaviors': 'behavior_id', 'evidence': 'evidence_id', 'annotations': 'annotation_id',
           'materials': 'material_id', 'reviews': 'review_id'}
EXTENSIONS = ['id_registry', 'document_evidence', 'responsibility_relations',
              'quote_bindings', 'issues', 'candidate_snapshots']
READING_TYPES = ['document_index', 'case_reading', 'behavior_reading']
CASE_COMPAT_METADATA = ['original_case_summary', 'case_summary_status', 'case_summary_missing_reason',
                        'original_unknowns', 'missing_reasons_status', 'unknowns_missing_reason',
                        'related_party_names_original_type', 'related_party_names_status', 'related_party_names_missing_reason']


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def json_sha(value):
    return sha(canonical(value))


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def iter_records(directory):
    """Read only the explicitly named JSONL directory; never discover other sets."""
    directory = Path(directory)
    for path in sorted(directory.glob('*.jsonl')):
        with path.open(encoding='utf-8-sig') as stream:
            for line_no, line in enumerate(stream, 1):
                if line.strip():
                    row = json.loads(line)
                    row['_export_location'] = {'path': str(path.resolve()), 'line': line_no}
                    yield row


def load_records(repo):
    repo = Path(repo)
    maps = []
    for kind in ['candidates', 'sources']:
        result = {}
        for row in iter_records(repo / 'data' / kind):
            fid = row['file_id']
            if fid in result:
                raise ValueError(f'duplicate {kind} file_id: {fid}')
            result[fid] = row
        maps.append(result)
    return tuple(maps)


def quote_fields(value, prefix=''):
    """Every original quote path remains visible, including unknown extra fields."""
    if isinstance(value, dict):
        for key, item in value.items():
            path = f'{prefix}.{key}' if prefix else key
            if key == 'quote' or key.endswith('_quote'):
                if item is not None:
                    yield path, item
            elif key == 'quotes' or key.endswith('_quotes'):
                if isinstance(item, list):
                    for index, quote in enumerate(item):
                        if quote is not None:
                            yield f'{path}[{index}]', quote
                elif item is not None:
                    yield path, item
            else:
                yield from quote_fields(item, path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from quote_fields(item, f'{prefix}[{index}]')


def occurrences(text, quote):
    result = []
    if not isinstance(quote, str) or not quote:
        return result
    start = text.find(quote)
    while start >= 0:
        result.append([start, start + len(quote)])
        start = text.find(quote, start + 1)
    return result


def missing(values, fields):
    return [{'field': field, 'origin': 'derived_missing_metadata',
             'reason': 'candidate_field_missing' if field not in values else 'candidate_records_null',
             'interpretation': '未记载或未核验，不能视为不存在、不适用或合规'}
            for field in fields if values.get(field) is None]


def legal_ref_record(original, evidence_ids):
    if isinstance(original, dict):
        return {**copy.deepcopy(original), 'evidence_ids': list(evidence_ids), 'current_effectiveness': 'unknown_not_checked'}
    if isinstance(original, (str, list)):
        return {'value': None, 'quote': None, 'legacy_original_value': copy.deepcopy(original),
                'legacy_original_type': 'string' if isinstance(original, str) else 'array',
                'representation': 'legacy_raw_uninterpreted', 'evidence_ids': [],
                'current_effectiveness': 'unknown_not_checked', 'metadata_status': 'unknown',
                'missing_reason': 'derived:旧候选法条字段为非对象值，仅保留原类型和值；未解析法条、引文或效力'}
    raise ValueError('unsupported legal_refs member type: ' + type(original).__name__)


def uncertainty_fields(original):
    value = original.get('uncertainties', [])
    if value is None:
        return {'uncertainties': [], 'original_uncertainties': None, 'uncertainties_status': 'unknown_in_candidate',
                'uncertainties_missing_reason': 'derived:原候选uncertainties为null，未记载或未核验；不能视为没有不确定性'}
    return {'uncertainties': copy.deepcopy(value)}


def case_compat_fields(original):
    summary, unknowns, related = original.get('case_summary', ''), original.get('unknowns', []), original.get('related_party_names', [])
    result = {'case_summary': copy.deepcopy(summary), 'missing_reasons': copy.deepcopy(unknowns),
              'related_party_names': copy.deepcopy(related)}
    if not isinstance(summary, str):
        result.update(case_summary='', original_case_summary=copy.deepcopy(summary),
                      case_summary_status='unknown_in_candidate' if summary is None else 'legacy_non_string_uninterpreted',
                      case_summary_missing_reason='derived:原候选摘要不是字符串，保留原类型和值；未推断或改写为事实摘要')
    if unknowns is None:
        result.update(missing_reasons=[], original_unknowns=None, missing_reasons_status='unknown_in_candidate',
                      unknowns_missing_reason='derived:原候选unknowns为null，未记载或未核验；不能视为没有未知')
    if not isinstance(related, list):
        result.update(related_party_names_original_type='null' if related is None else 'string' if isinstance(related, str) else type(related).__name__,
                      related_party_names_status='unknown_in_candidate' if related is None else 'legacy_non_array_uninterpreted',
                      related_party_names_missing_reason='derived:原候选相关主体字段不是名单数组，保留原值；未解析名单或推断主体关系')
    return result


def state(row, draft, wrapper):
    human = row.get('human_review_status', draft.get('human_review_status', wrapper.get('human_review_status', 'unknown')))
    publication = row.get('publication_status', draft.get('publication_status'))
    if publication is None:
        semantic = draft.get('semantic_status', wrapper.get('semantic_status', 'unknown'))
        publication = semantic if semantic in ['candidate', 'approved_core', 'quarantined', 'held'] else 'held'
    # A document-level or narrowly scoped review never approves absent field statuses.
    fallback = 'pending' if human == 'pending' else 'unknown'
    return {'human_review_status': human, 'publication_status': publication,
            'fact_review_status': row.get('fact_review_status', fallback),
            'tag_review_status': row.get('tag_review_status', fallback),
            'scene_review_status': row.get('scene_review_status', fallback),
            'status_origin': {'human': 'record' if 'human_review_status' in row else
                             ('draft' if 'human_review_status' in draft else wrapper.get('status_origin', 'wrapper')),
                             'field_status_default': 'derived_pending_or_unknown_only'},
            'field_review_status': copy.deepcopy(row.get('field_review_status', {})),
            'approved_scope': copy.deepcopy(row.get('approved_scope', []))}


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8') + b'\n')


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open('wb') as stream:
        for row in rows:
            stream.write(canonical(row) + b'\n')


def record_reading(name, row, line_no, tid, document_location, evidence_locations):
    """One exact reading projection for generation and independent comparison."""
    key = PRIMARY[name]
    reading = {key: row[key], 'file_id': row['official_file_id'], 'proposal_local_key': row['proposal_local_key'],
        'record_table': {'path': f'data/{name}.jsonl', 'line': line_no}, 'text_id': tid,
        'document_table': document_location, 'evidence_locations': evidence_locations,
        'fact_review_status': row['fact_review_status'], 'human_review_status': row['human_review_status'],
        'publication_status': row['publication_status'], 'field_evidence_state': row['field_evidence_state'],
        'reader_note': '按document_table回到全文；坐标为Unicode码点[start,end)，多次出现全部列出。'}
    fields = ['case_summary', 'parties', 'penalties', 'behavior_ids', 'legal_refs', 'missing_reasons'] if name == 'cases' else [
        'case_id', 'behavior_summary', 'actor_refs', 'conditions', 'negations', 'exceptions',
        'risk_tags', 'risk_tag_basis', 'uncertainties']
    reading.update({field: row[field] for field in fields})
    if name == 'cases':
        for field in CASE_COMPAT_METADATA:
            if field in row: reading[field] = row[field]
        if 'related_party_names_status' in row: reading['related_party_names'] = row['related_party_names']
    if name == 'behaviors':
        for field in ['original_uncertainties', 'uncertainties_status', 'uncertainties_missing_reason']:
            if field in row: reading[field] = row[field]
    return reading


def normalize_records(candidates, sources, out, overlays=None):
    """Normalize provided maps into a new independent directory, preserving facts.

    Overlays map file_id to an effective complete draft. Upstream approval/SHA
    authorization belongs to the caller; this function records both drafts/hashes.
    """
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError(f'output is nonempty; choose an independent directory: {out}')
    if set(candidates) != set(sources):
        raise ValueError('candidate/source file_id sets differ')
    overlays = overlays or {}
    if not set(overlays).issubset(candidates):
        raise ValueError('overlay contains unknown file_id')
    contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8-sig'))
    if set(contract['tables']) != set(PRIMARY):
        raise ValueError('eight-table contract changed; inspect before normalizing')
    tables = {name: [] for name in PRIMARY}
    extensions = {name: [] for name in EXTENSIONS}
    navigation = {name: [] for name in ['document_index', 'case_reading', 'behavior_reading']}
    identities = {}
    batches = Counter()
    for fid in sorted(candidates):
        wrapper, source = candidates[fid], sources[fid]
        base = wrapper['draft']
        draft = overlays.get(fid, base)
        if wrapper.get('file_id') != fid or source.get('file_id') != fid or base.get('file_id') != fid or draft.get('file_id') != fid:
            raise ValueError(f'file_id mismatch: {fid}')
        base_sha, effective_sha = json_sha(base), json_sha(draft)
        if wrapper.get('draft_json_sha256') != base_sha:
            raise ValueError(f'base draft JSON SHA mismatch: {fid}')
        full_text = source['full_text']
        actual_text_sha = sha(full_text.encode('utf-8'))
        if actual_text_sha != source['text_sha256']:
            raise ValueError(f'exported text SHA mismatch: {fid}')
        meta = copy.deepcopy(source.get('document_metadata', {}))
        for name in ['text_sha256', 'source_sha256', 'text_version']:
            if name in meta and meta[name] != source[name]:
                raise ValueError(f'source/document metadata mismatch {fid}: {name}')
        if 'full_text' in meta and meta['full_text'] != full_text:
            raise ValueError(f'document full_text mismatch: {fid}')
        meta.pop('full_text', None)
        binding = {'file_id': fid, 'source_sha256': source['source_sha256'],
                   'text_sha256': actual_text_sha, 'text_version': source.get('text_version', 1)}

        def identity(kind, local_key):
            descriptor = {'namespace': VERSION, 'object_kind': kind, **binding, 'local_key': local_key}
            key = canonical(descriptor)
            record_id = 'FRV2-' + kind.upper() + '-' + fid + '-' + sha(key)[:24]
            if record_id in identities and identities[record_id] != descriptor:
                raise ValueError('stable ID collision')
            if record_id not in identities:
                identities[record_id] = descriptor
                extensions['id_registry'].append({'record_id': record_id, **descriptor})
            return record_id

        sid = identity('source', 'exported_txt')
        tid = identity('text', 'exported_full_text')
        original_cases, original_behaviors = draft.get('cases', []), draft.get('behaviors', [])
        ckeys = [c['local_key'] for c in original_cases]
        bkeys = [b['local_key'] for b in original_behaviors]
        if len(ckeys) != len(set(ckeys)) or len(bkeys) != len(set(bkeys)):
            raise ValueError(f'duplicate local_key within document: {fid}')
        cids = {key: identity('case', key) for key in ckeys}
        bids = {key: identity('behavior', key) for key in bkeys}
        partyids = {key: identity('party', key) for key in ckeys}
        by_case = {c['local_key']: c for c in original_cases}
        for behavior in original_behaviors:
            if behavior['case_key'] not in cids:
                raise ValueError(f'unknown behavior.case_key {fid}: {behavior["case_key"]}')
        shared = {'official_file_id': fid, 'base_draft_json_sha256': base_sha,
                  'effective_draft_json_sha256': effective_sha, 'access_scope': 'local_internal'}
        status = state({}, draft, wrapper)
        batches[wrapper.get('batch', 'unknown')] += 1
        extensions['candidate_snapshots'].append({**binding, 'batch': wrapper.get('batch'),
            'base_draft_json_sha256': base_sha, 'effective_draft_json_sha256': effective_sha,
            'base_draft': base, 'effective_draft': draft if effective_sha != base_sha else None,
            'effective_draft_reference': 'effective_draft' if effective_sha != base_sha else 'base_draft',
            'wrapper_metadata': {k: v for k, v in wrapper.items() if k not in ['draft']},
            'source_record_metadata': {k: v for k, v in source.items() if k not in ['full_text', 'document_metadata']},
            'document_metadata': meta})
        evidence_cache, doc_evidence_cache, bindings = {}, {}, []
        issue_start = len(extensions['issues'])
        for path, quote in quote_fields(draft):
            case_match = re.match(r'^cases\[(\d+)\]', path)
            behavior_match = re.match(r'^behaviors\[(\d+)\]', path)
            case_key, behavior_key, target_id = None, None, tid
            if case_match:
                case_key = original_cases[int(case_match.group(1))]['local_key']
                target_id = cids[case_key]
            elif behavior_match:
                behavior = original_behaviors[int(behavior_match.group(1))]
                case_key, behavior_key = behavior['case_key'], behavior['local_key']
                target_id = bids[behavior_key]
            spans = occurrences(full_text, quote)
            eids = []
            for start, end in spans:
                local = {'case_local_key': case_key, 'start_char': start, 'end_char': end}
                eid = identity('evidence' if case_key else 'document_evidence', local)
                cache = evidence_cache if case_key else doc_evidence_cache
                if eid not in cache:
                    cache[eid] = {'evidence_id': eid, 'case_id': cids.get(case_key), 'behavior_ids': [],
                        'evidence_type': 'candidate_source_excerpt', 'text_id': tid,
                        'text_version': binding['text_version'], 'text_sha256': actual_text_sha,
                        'source_sha256': source['source_sha256'], 'verbatim': quote,
                        'start_char': start, 'end_char': end, 'offset_unit': 'unicode_codepoint',
                        'span_convention': '[start,end)', 'page_number': None,
                        'source_verification_method': 'exported_text_sha256_and_exact_unicode_span',
                        'source_status': 'verified', 'verification_scope': 'exported_text_only',
                        'original_source_bytes_verification': 'not_performed_by_normalizer',
                        'supported_fields': [], 'human_review_status': status['human_review_status'],
                        'historical_review_ids': [], 'quote_location_ambiguity': len(spans) > 1,
                        'occurrence_count_for_quote': len(spans), **shared}
                row = cache[eid]
                if path not in row['supported_fields']:
                    row['supported_fields'].append(path)
                if behavior_key and bids[behavior_key] not in row['behavior_ids']:
                    row['behavior_ids'].append(bids[behavior_key])
                eids.append(eid)
            quote_status = 'matched_ambiguous' if len(spans) > 1 else ('matched_unique' if spans else 'unmatched')
            entry = {**binding, 'proposal_field': path, 'quote': quote, 'case_id': cids.get(case_key),
                     'behavior_id': bids.get(behavior_key), 'target_id': target_id,
                     'occurrences': spans, 'evidence_ids': eids, 'status': quote_status,
                     'location_ambiguity': len(spans) > 1, 'effective_draft_json_sha256': effective_sha}
            bindings.append(entry)
            if not spans:
                extensions['issues'].append({**binding, 'origin': 'derived_quote_binding', 'target_id': target_id,
                    'field': path, 'code': 'QUOTE_NOT_FOUND' if isinstance(quote, str) and quote else 'QUOTE_INVALID_OR_EMPTY',
                    'original_quote': quote, 'status': 'pending', 'action': '保留原值，隔离该字段证据绑定；未生成位置',
                    'effective_draft_json_sha256': effective_sha})
        extensions['quote_bindings'].extend(bindings)
        tables['evidence'].extend(evidence_cache.values())
        extensions['document_evidence'].extend(doc_evidence_cache.values())

        def ev(prefix):
            result = []
            for entry in bindings:
                path = entry['proposal_field']
                if path == prefix or path.startswith(prefix + '.') or path.startswith(prefix + '['):
                    result.extend(entry['evidence_ids'])
            return list(dict.fromkeys(result))

        def binding_status(prefix):
            entries = [b for b in bindings if b['proposal_field'] == prefix or
                       b['proposal_field'].startswith(prefix + '.') or b['proposal_field'].startswith(prefix + '[')]
            return {'state': 'unmatched_source_quote' if any(x['status'] == 'unmatched' for x in entries) else
                    ('exact_source_quote' if entries else 'no_quote_recorded'),
                    'unmatched_fields': [x['proposal_field'] for x in entries if x['status'] == 'unmatched'],
                    'mechanical_only': True}

        def annotate(ck, target, field, value, prefix, scope=None):
            aid = identity('annotation', {'target_id': target, 'field': field})
            tables['annotations'].append({'annotation_id': aid, 'case_id': cids[ck], 'target_id': target,
                'field': field, 'value': copy.deepcopy(value), 'origin': 'preserved_candidate_draft',
                'creator': draft.get('creator') or 'unknown', 'model_or_prompt_version': draft.get('model_or_prompt_version'),
                'evidence_ids': ev(prefix), 'scope': scope if scope is not None else 'source_context_only',
                'exclusion_conditions': [], 'review_status': status['human_review_status'],
                'reviewer': None, 'reviewed_at': None, 'review_note': None,
                'creator_missing_reason': None if draft.get('creator') else '原候选未记录创建者，unknown非人名或审批人',
                'field_evidence_state': binding_status(prefix), **shared})
            return aid

        source_row = {'source_id': sid, 'official_file_id': fid,
            'original_filename': source.get('original_filename', meta.get('original_filename', '')),
            'relative_path': source.get('relative_path', meta.get('relative_path')),
            'file_type': 'txt', 'byte_size': len(full_text.encode('utf-8')),
            'byte_size_semantics': 'derived_exported_text_utf8_bytes; original_byte_size_unknown',
            'source_sha256': source['source_sha256'], 'linked_source_ids': [],
            'mapping_status': 'candidate', 'mapping_basis': 'provided_export_wrapper_file_id_and_declared_source_sha',
            'processing_status': 'partial', 'insurance_relevance': draft.get('insurance_relevance', {}).get('value'),
            'relevance_review_status': status['human_review_status'],
            'relevance_to_marketing': draft.get('marketing_relevance', {}).get('value'),
            'exclusion_reason': None, 'error_code': None, 'pipeline_version': VERSION, 'processed_at': None,
            'original_source_id': source.get('source_id'), 'source_sha_verification_scope': 'declared_in_input_wrapper',
            'original_mapping_metadata': {k: copy.deepcopy(meta[k]) for k in meta if 'pdf' in k.lower() or 'source' in k.lower() or 'path' in k.lower()},
            'derived_missing_reasons': missing({**meta, **source}, ['original_filename', 'relative_path']), **status, **shared}
        tables['source_inventory'].append(source_row)
        document = {**meta, 'text_id': tid, 'source_id': sid, 'text_version': binding['text_version'],
            'source_sha256': source['source_sha256'], 'text_sha256': actual_text_sha,
            'encoding': meta.get('encoding', 'utf-8'), 'newline_handling': meta.get('newline_handling', 'preserve_exported_text'),
            'full_text': full_text, 'extraction_method': meta.get('extraction_method', 'unknown_in_export_wrapper'),
            'page_map': meta.get('page_map'), 'paragraph_map': meta.get('paragraph_map'),
            'text_quality_flags': meta.get('text_quality_flags', []) + list(draft.get('source_issues', [])),
            'pdf_text_consistency_status': meta.get('pdf_text_consistency_status', 'unknown_in_export_wrapper'),
            'original_text_id': source.get('text_id'), 'original_source_id': source.get('source_id'),
            'source_export_location': source.get('_export_location'),
            'original_candidate_path': wrapper.get('original_candidate_path'),
            'original_candidate_sha256': wrapper.get('original_candidate_sha256'),
            'candidate_export_location': wrapper.get('_export_location'),
            'case_ids': list(cids.values()), 'behavior_ids': list(bids.values()),
            'source_issues': copy.deepcopy(draft.get('source_issues', [])),
            'unresolved': copy.deepcopy(draft.get('unresolved', [])),
            'derived_missing_reasons': missing(meta, ['page_map', 'paragraph_map', 'encoding', 'extraction_method']),
            **status, **shared}
        tables['documents'].append(document)
        for index, original in enumerate(original_cases):
            ck = original['local_key']; cid = cids[ck]; prefix = f'cases[{index}]'
            field_evidence = {field: ev(prefix + '.' + quote_field) for field, quote_field in
                [('party', 'party_quote'), ('penalty_doc_no', 'doc_no_quote'), ('regulator', 'regulator_quote'),
                 ('penalty_date', 'penalty_date_quote'), ('behavior_period', 'behavior_period_quote'),
                 ('case_summary', 'case_summary_quotes')]}
            penalties = []
            for pi, penalty in enumerate(original.get('penalties', [])):
                penalties.append({**copy.deepcopy(penalty), 'party_id': partyids[ck],
                                  'evidence_ids': ev(f'{prefix}.penalties[{pi}]'),
                                  'derived_missing_reasons': missing(penalty, ['amount_yuan', 'currency']),
                                  'aggregation_policy': 'preserve_each_original_penalty; no_total_or_cross_party_sum'})
            hierarchy = copy.deepcopy(original.get('institution_hierarchy', {}))
            hierarchy['evidence_ids'] = ev(prefix + '.institution_hierarchy')
            case = {'case_id': cid, 'event_group_id': original.get('event_group_id'),
                'event_group_basis': original.get('event_group_basis'), 'source_ids': [sid], 'text_ids': [tid],
                'penalty_doc_no': original.get('penalty_doc_no'), 'regulator': original.get('regulator'),
                'penalty_date': original.get('penalty_date'), 'behavior_period': original.get('behavior_period'),
                'parties': [{'party_id': partyids[ck], 'name': original.get('party_name'),
                             'party_type': original.get('party_type'), 'roles': ['penalized_party'],
                             'evidence_ids': field_evidence['party'], 'institution_hierarchy': hierarchy}],
                'penalties': penalties,
                'behavior_ids': [bids[b['local_key']] for b in original_behaviors if b['case_key'] == ck],
                'legal_refs': [legal_ref_record(ref, ev(f'{prefix}.legal_refs[{li}]'))
                               for li, ref in enumerate(original.get('legal_refs', []))],
                **case_compat_fields(original), 'case_origin': 'preserved_offline_candidate',
                'legacy_case_ids': [], 'field_evidence': field_evidence,
                'derived_missing_reasons': missing(original, ['penalty_doc_no', 'regulator', 'penalty_date', 'behavior_period', 'case_summary', 'unknowns', 'related_party_names']),
                'quality_flags': copy.deepcopy(draft.get('source_issues', [])), 'record_version': original.get('record_version', 1),
                'proposal_local_key': ck, 'source_record_path': prefix, 'field_evidence_state': binding_status(prefix),
                **state(original, draft, wrapper), **shared}
            case['annotation_ids'] = [annotate(ck, cid, 'case_summary', original.get('case_summary'), prefix + '.case_summary_quotes'),
                                      annotate(ck, cid, 'institution_hierarchy', original.get('institution_hierarchy'), prefix + '.institution_hierarchy')]
            tables['cases'].append(case)
        material_cache = {}
        for index, original in enumerate(original_behaviors):
            bk, ck = original['local_key'], original['case_key']; bid, cid = bids[bk], cids[ck]
            prefix = f'behaviors[{index}]'; material_ids = []
            for mi, material in enumerate(original.get('materials', [])):
                # Explicit local key wins; otherwise equal case-scoped original material values share identity.
                material_key = {'case_local_key': ck, 'material_local_key': material.get('local_key')}
                if material.get('local_key') is None:
                    material_key['derived_original_material_sha256'] = json_sha(material)
                mid = identity('material', material_key)
                material_ids.append(mid)
                m_prefix = f'{prefix}.materials[{mi}]'
                if mid not in material_cache:
                    material_cache[mid] = {'material_id': mid, 'case_id': cid,
                        'name': material.get('name', ''), 'material_form': material.get('form', material.get('type', 'unknown')),
                        'material_function': material.get('function', 'unknown'), 'origin': 'preserved_candidate_material',
                        'evidence_ids': [], 'original_expression_ids': [],
                        'complete_business_material_available': material.get('complete_business_material_available', False),
                        'completeness': material.get('completeness', 'unknown_in_candidate'),
                        'original_expression_missing_reason': material.get('missing_reason') or
                            (None if material.get('original_expression_quote') else 'derived:候选未记录原话，不能认为原业务材料已完整取得'),
                        'review_status': material.get('review_status', status['human_review_status']),
                        'behavior_ids': [], 'original_material': copy.deepcopy(material),
                        'derived_missing_reasons': missing(material, ['name', 'form', 'function', 'original_expression_quote']),
                        'source_record_paths': [], **shared}
                mrow = material_cache[mid]
                if bid not in mrow['behavior_ids']: mrow['behavior_ids'].append(bid)
                mrow['source_record_paths'].append(m_prefix)
                for field, suffix in [('evidence_ids', '.quote'), ('original_expression_ids', '.original_expression_quote')]:
                    mrow[field] = list(dict.fromkeys(mrow[field] + ev(m_prefix + suffix)))
            tag_basis = [{**copy.deepcopy(tag), 'evidence_ids': ev(f'{prefix}.risk_tags[{ti}]')}
                         for ti, tag in enumerate(original.get('risk_tags', []))]
            tags = [tag.get('tag') for tag in original.get('risk_tags', [])]
            observed = copy.deepcopy(original.get('observed_scene', {})); observed['evidence_ids'] = ev(prefix + '.observed_scene')
            applicable = [{**copy.deepcopy(scene), 'evidence_ids': ev(f'{prefix}.applicable_scenes[{si}]')}
                          for si, scene in enumerate(original.get('applicable_scenes', []))]
            factors = {factor['factor_id']: {**copy.deepcopy(factor), 'evidence_ids': ev(f'{prefix}.factor_values[{fi}]')}
                       for fi, factor in enumerate(original.get('factor_values', []))}
            qualifier_evidence = [{'kind': group, 'original_value': copy.deepcopy(value),
                                   'evidence_ids': ev(f'{prefix}.{group}[{qi}]')}
                                  for group in ['conditions', 'negations', 'exceptions']
                                  for qi, value in enumerate(original.get(group, []))]
            annotation_ids = [annotate(ck, bid, field, original.get(field), prefix + '.' + field,
                                      {'assignment_scope': 'preserved_in_value; no_scope_expansion'})
                              for field in ['risk_tags', 'observed_scene', 'applicable_scenes', 'factor_values']]
            annotation_ids += [annotate(ck, bid, field, original.get(field), prefix + '.' + field + '_quotes')
                               for field in ['material_function', 'risk_mechanism']]
            behavior = {'behavior_id': bid, 'case_id': cid, 'event_behavior_ref': original.get('event_behavior_ref'),
                'actor_refs': [{'party_id': partyids[ck], 'name': by_case[ck].get('party_name'), 'role': original.get('actor_role')}],
                'actor_role': original.get('actor_role'), 'target': original.get('target'), 'action': original.get('action'),
                'object': original.get('object'), 'behavior_summary': original.get('summary', ''),
                'background_evidence_ids': ev('insurance_relevance'), 'fact_evidence_ids': ev(prefix + '.finding_quote'),
                'condition_evidence_ids': list(dict.fromkeys(e for q in qualifier_evidence for e in q['evidence_ids'])),
                'original_expression_ids': list(dict.fromkeys(e for mid in material_ids for e in material_cache[mid]['original_expression_ids'])),
                'conditions': copy.deepcopy(original.get('conditions', [])), 'negations': copy.deepcopy(original.get('negations', [])),
                'exceptions': copy.deepcopy(original.get('exceptions', [])), 'qualification_evidence': qualifier_evidence,
                **uncertainty_fields(original), 'regulatory_finding': original.get('regulatory_finding'),
                'risk_mechanism': original.get('risk_mechanism'), 'primary_risk_tag': tags[0] if tags else None,
                'secondary_risk_tags': tags[1:], 'risk_tags': tags, 'risk_tag_basis': tag_basis,
                'observed_scene': observed, 'applicable_scenes': applicable, 'product_type': original.get('product_type'),
                'product_evidence_ids': ev(prefix + '.product_quote'), 'material_function': original.get('material_function', 'unknown'),
                'material_ids': list(dict.fromkeys(material_ids)), 'annotation_ids': annotation_ids,
                'factor_values': factors, 'missing_reasons': [original['zero_tag_reason']] if original.get('zero_tag_reason') else [],
                'derived_missing_reasons': missing(original, ['target', 'action', 'object', 'regulatory_finding', 'risk_mechanism', 'product_type', 'uncertainties']),
                'record_version': original.get('record_version', 1), 'proposal_local_key': bk, 'original_case_key': ck,
                'source_record_path': prefix, 'field_evidence_state': binding_status(prefix),
                **state(original, draft, wrapper), **shared}
            tables['behaviors'].append(behavior)
        tables['materials'].extend(material_cache.values())
        rid = identity('review', 'inherited_candidate_status')
        tables['reviews'].append({'review_id': rid, 'case_id': None, 'origin': 'candidate_status_snapshot',
            'target_ids': list(cids.values()) + list(bids.values()), 'field_scope': [], 'decision': None,
            'status': status['human_review_status'], 'reviewer': None, 'reviewed_at': None,
            'original_record_path': wrapper.get('original_candidate_path'),
            'original_record_sha256': wrapper.get('original_candidate_sha256'),
            'approved_scope': [], 'exclusion_scope': [], 'independent_second_review_completed': False,
            'completion_flag_origin': 'derived_unrecorded; not_an_assessment',
            'inherited_document_status': copy.deepcopy(status), **shared})
        navigation['document_index'].append({**shared, **binding, 'batch': wrapper.get('batch'),
            'source_id': sid, 'text_id': tid, 'case_ids': list(cids.values()), 'behavior_ids': list(bids.values()),
            'document_table': {'path': 'data/documents.jsonl', 'line': len(tables['documents'])},
            'candidate_snapshot': {'path': 'extensions/candidate_snapshots.jsonl', 'line': len(extensions['candidate_snapshots'])},
            'source_export_location': source.get('_export_location'),
            'candidate_export_location': wrapper.get('_export_location'),
            'original_candidate_path': wrapper.get('original_candidate_path'),
            'source_metadata_links': {k: v for k, v in meta.items() if 'path' in k.lower() or 'pdf' in k.lower()},
            'quote_problem_count': len(extensions['issues']) - issue_start,
            'source_issues': copy.deepcopy(draft.get('source_issues', [])), **status})
    for name, rows in tables.items():
        write_jsonl(out / 'data' / (name + '.jsonl'), rows)
    for name, rows in extensions.items():
        write_jsonl(out / 'extensions' / (name + '.jsonl'), rows)
    evidence_locations = {}
    for group, name in [('data', 'evidence'), ('extensions', 'document_evidence')]:
        rows = tables[name] if group == 'data' else extensions[name]
        for line_no, row in enumerate(rows, 1):
            evidence_locations[row['evidence_id']] = {'path': f'{group}/{name}.jsonl', 'line': line_no,
                'text_id': row['text_id'], 'start_char': row['start_char'], 'end_char': row['end_char']}
    doc_locations = {row['text_id']: row['document_table'] for row in navigation['document_index']}
    case_texts = {row['case_id']: row['text_ids'][0] for row in tables['cases']}
    quoted_by_target = {}
    for entry in extensions['quote_bindings']:
        quoted_by_target.setdefault(entry['target_id'], set()).update(entry['evidence_ids'])
    for name, key in [('cases', 'case_id'), ('behaviors', 'behavior_id')]:
        for line_no, row in enumerate(tables[name], 1):
            tid = row['text_ids'][0] if name == 'cases' else case_texts[row['case_id']]
            quoted_ids = sorted(quoted_by_target.get(row[key], []))
            reading = record_reading(name, row, line_no, tid, doc_locations[tid], [evidence_locations[eid] for eid in quoted_ids])
            navigation['case_reading' if name == 'cases' else 'behavior_reading'].append(reading)
    for name, rows in navigation.items():
        write_jsonl(out / 'reading' / (name + '.jsonl'), rows)
    write_json(out / 'contract/schema.json', contract)
    counts = {name: len(rows) for name, rows in tables.items()}
    index_text = '\n'.join(['# 候选阅读导航', '',
        '所有状态来自候选或原记录；位置验证只验证导出文本，不能替代语义审核、PDF核验或真人批准。', '',
        f'文书 {len(candidates)}；个案 {counts["cases"]}；行为 {counts["behaviors"]}。', '',
        '- [全量文书索引](reading/document_index.jsonl)', '- [个案阅读](reading/case_reading.jsonl)',
        '- [行为阅读](reading/behavior_reading.jsonl)', '- [未匹配引文及问题](extensions/issues.jsonl)',
        '- [全部引文字段与位置](extensions/quote_bindings.jsonl)', '- [原稿与生效稿绑定](extensions/candidate_snapshots.jsonl)', '',
        'JSONL索引的line是1起始行号；原文仅存于documents表，每份文书一行。原文坐标为Unicode码点[start,end)。',
        '材料、注释和证据ID均可连接对应数据表；没有按名称跨文书合并主体或案件。', '',
        '|批次|文书数|', '|---|---:|'] + [f'|{batch}|{count}|' for batch, count in sorted(batches.items())]) + '\n'
    (out / 'INDEX.md').write_bytes(index_text.encode('utf-8'))
    manifest = {'normalizer_version': VERSION, 'contract_format': contract['format'],
        'validation_claim': 'declared_field_types_enums_and_separate_ids_spans_hashes; not_complete_JSON_Schema_or_semantic_approval',
        'candidate_count': len(candidates), 'overlay_count': len(overlays), 'batches': dict(sorted(batches.items())),
        'core_tables': list(PRIMARY), 'extension_tables': EXTENSIONS, 'counts': counts,
        'extension_counts': {name: len(rows) for name, rows in extensions.items()},
        'reading_counts': {name: len(rows) for name, rows in navigation.items()},
        'original_source_bytes_verified_by_normalizer': False,
        'files': {path.relative_to(out).as_posix(): {'bytes': path.stat().st_size, 'sha256': file_sha(path)}
                  for path in sorted(out.rglob('*')) if path.is_file()}}
    write_json(out / 'manifest.json', manifest)
    return manifest


def read_jsonl(path):
    with Path(path).open(encoding='utf-8-sig') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def declared_type(value, types):
    checks = {'null': value is None, 'string': isinstance(value, str),
              'integer': isinstance(value, int) and not isinstance(value, bool),
              'number': isinstance(value, (int, float)) and not isinstance(value, bool),
              'boolean': isinstance(value, bool), 'array': isinstance(value, list), 'object': isinstance(value, dict)}
    return any(checks.get(name, False) for name in types)


def verify(out):
    """Independent, repeatable mechanical checks; unmatched quotes remain issues."""
    out = Path(out); errors = []
    try:
        manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8-sig'))
        contract = json.loads((out / 'contract/schema.json').read_text(encoding='utf-8-sig'))
        reading_counts = manifest.get('reading_counts', {})
        if not isinstance(reading_counts, dict):
            errors.append('manifest_reading_counts_type'); reading_counts = {}
        if set(reading_counts) != set(READING_TYPES): errors.append('manifest_reading_categories_incomplete_or_unknown')
        required_files = {f'data/{name}.jsonl' for name in PRIMARY} | {f'extensions/{name}.jsonl' for name in EXTENSIONS}
        required_files |= {f'reading/{name}.jsonl' for name in READING_TYPES} | {'contract/schema.json', 'INDEX.md'}
        for relative in sorted(required_files - set(manifest['files'])):
            errors.append('manifest_missing_required_file_hash:' + relative)
        for relative, info in manifest['files'].items():
            path = (out / relative).resolve()
            if not path.is_relative_to(out.resolve()) or not path.is_file():
                errors.append('missing_or_outside_file:' + relative); continue
            if path.stat().st_size != info['bytes'] or file_sha(path) != info['sha256']:
                errors.append('file_hash_or_size:' + relative)
        tables = {name: read_jsonl(out / 'data' / (name + '.jsonl')) for name in PRIMARY}
        extensions = {name: read_jsonl(out / 'extensions' / (name + '.jsonl')) for name in EXTENSIONS}
        idsets, all_ids = {}, set()
        for name, rows in tables.items():
            key = PRIMARY[name]; ids = [row[key] for row in rows]
            idsets[name] = set(ids)
            if len(ids) != len(idsets[name]): errors.append('duplicate_primary:' + name)
            if len(rows) != manifest['counts'][name]: errors.append('count:' + name)
            for row in rows:
                if row[key] in all_ids: errors.append('cross_table_id_collision:' + row[key])
                all_ids.add(row[key])
                spec = contract['tables'][name]
                for field, rule in {**spec['required_fields'], **spec.get('optional_fields', {})}.items():
                    if field not in row:
                        if field in spec['required_fields']: errors.append(f'missing_field:{name}:{row[key]}:{field}')
                    elif not declared_type(row[field], rule['type']): errors.append(f'type:{name}:{row[key]}:{field}')
                    elif 'enum' in rule and row[field] not in rule['enum']: errors.append(f'enum:{name}:{row[key]}:{field}')
        for name, rows in extensions.items():
            if len(rows) != manifest['extension_counts'][name]: errors.append('extension_count:' + name)
        evidence = {row['evidence_id']: row for row in tables['evidence'] + extensions['document_evidence']}
        if len(evidence) != len(tables['evidence']) + len(extensions['document_evidence']): errors.append('duplicate_evidence')
        all_ids.update(evidence)
        parties = {party['party_id'] for case in tables['cases'] for party in case['parties']}
        all_ids.update(parties)
        documents = {row['text_id']: row for row in tables['documents']}
        documents_by_file = {row['official_file_id']: row for row in tables['documents']}
        sources_by_id = {row['source_id']: row for row in tables['source_inventory']}
        snapshots_by_file = {row['file_id']: row for row in extensions['candidate_snapshots']}
        if len(snapshots_by_file) != len(extensions['candidate_snapshots']): errors.append('duplicate_snapshot_file_id')
        for document in documents.values():
            source = sources_by_id.get(document['source_id'])
            snapshot = snapshots_by_file.get(document['official_file_id'])
            if source is None or snapshot is None: errors.append('document_source_or_snapshot_missing:' + document['text_id']); continue
            original_source = snapshot['source_record_metadata']
            for field in ['file_id', 'source_sha256', 'text_sha256', 'text_version']:
                if snapshot.get(field) != original_source.get(field): errors.append('snapshot_original_source_binding:' + document['text_id'] + ':' + field)
            if source['official_file_id'] != document['official_file_id'] or source['source_sha256'] != document['source_sha256'] or source['source_sha256'] != original_source['source_sha256']:
                errors.append('source_inventory_document_binding:' + document['source_id'])
            if source.get('original_source_id') != original_source.get('source_id') or document.get('original_source_id') != original_source.get('source_id') or document.get('original_text_id') != original_source.get('text_id'):
                errors.append('original_source_identity_drift:' + document['text_id'])
        cases = {row['case_id']: row for row in tables['cases']}
        behaviors = {row['behavior_id']: row for row in tables['behaviors']}
        review_targets_by_file = {}
        for name, key in [('cases', 'case_id'), ('behaviors', 'behavior_id')]:
            for row in tables[name]: review_targets_by_file.setdefault(row['official_file_id'], []).append(row[key])
        reference_keys = {'source_id', 'source_ids', 'text_id', 'text_ids', 'case_id', 'case_ids',
                          'behavior_id', 'behavior_ids', 'party_id', 'evidence_ids', 'background_evidence_ids',
                          'fact_evidence_ids', 'condition_evidence_ids', 'original_expression_ids',
                          'product_evidence_ids', 'annotation_ids', 'material_ids', 'target_id', 'target_ids',
                          'historical_review_ids', 'event_group_id', 'event_behavior_ref'}

        def check_refs(value, context):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == 'field_evidence' and isinstance(item, dict):
                        for field, ids in item.items():
                            for record_id in ids:
                                if record_id not in evidence: errors.append('orphan_field_evidence:' + context + ':' + field)
                    elif key in reference_keys and item is not None:
                        ids = item if isinstance(item, list) else [item]
                        for record_id in ids:
                            if not isinstance(record_id, str) or record_id not in all_ids:
                                errors.append('orphan:' + context + ':' + key + ':' + str(record_id))
                    elif key not in ['original_material', 'value', 'original_mapping_metadata', 'unresolved', 'source_issues', 'text_quality_flags']:
                        check_refs(item, context)
            elif isinstance(value, list):
                for item in value: check_refs(item, context)
        for name, rows in tables.items():
            for row in rows: check_refs(row, name + ':' + row[PRIMARY[name]])
        for row in extensions['document_evidence']: check_refs(row, 'document_evidence')
        for row in extensions['quote_bindings']: check_refs(row, 'quote_bindings')
        bindings_by_field, bindings_by_file, quoted_by_target = {}, {}, {}
        for row in extensions['quote_bindings']:
            key = (row['file_id'], row['proposal_field'])
            if key in bindings_by_field: errors.append('duplicate_quote_binding:' + str(key))
            bindings_by_field[key] = row
            bindings_by_file.setdefault(row['file_id'], []).append(row)
            quoted_by_target.setdefault(row['target_id'], set()).update(row['evidence_ids'])
            document = documents_by_file.get(row['file_id'])
            if document is None: continue
            expected_spans = occurrences(document['full_text'], row['quote'])
            if row['occurrences'] != expected_spans: errors.append('quote_occurrences:' + str(key))
            actual_spans = [[evidence[eid]['start_char'], evidence[eid]['end_char']]
                            for eid in row['evidence_ids'] if eid in evidence]
            if actual_spans != expected_spans: errors.append('quote_evidence_occurrences:' + str(key))
            if row['location_ambiguity'] != (len(expected_spans) > 1): errors.append('quote_ambiguity:' + str(key))
            for eid in row['evidence_ids']:
                if eid in evidence and (evidence[eid]['verbatim'] != row['quote'] or evidence[eid]['text_id'] != document['text_id']): errors.append('quote_evidence_binding:' + str(key))
        for document in documents.values():
            if sha(document['full_text'].encode('utf-8')) != document['text_sha256']: errors.append('text_sha:' + document['text_id'])
        for row in evidence.values():
            document = documents.get(row['text_id'])
            if not document: continue
            if any(row[field] != document[field] for field in ['text_sha256', 'source_sha256', 'text_version']): errors.append('evidence_version:' + row['evidence_id'])
            start, end = row['start_char'], row['end_char']
            if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start or end > len(document['full_text']) or document['full_text'][start:end] != row['verbatim']:
                errors.append('evidence_span:' + row['evidence_id'])
            if row.get('case_id') and row['case_id'] in cases and row['text_id'] not in cases[row['case_id']]['text_ids']: errors.append('evidence_case_text:' + row['evidence_id'])
        for behavior in behaviors.values():
            case = cases.get(behavior['case_id'])
            if case and behavior['behavior_id'] not in case['behavior_ids']: errors.append('case_behavior_inverse:' + behavior['behavior_id'])
        registry = {row['record_id']: row for row in extensions['id_registry']}
        if len(registry) != len(extensions['id_registry']): errors.append('duplicate_registry')
        for record_id, descriptor in registry.items():
            identity = {key: value for key, value in descriptor.items() if key != 'record_id'}
            expected = 'FRV2-' + descriptor['object_kind'].upper() + '-' + descriptor['file_id'] + '-' + json_sha(identity)[:24]
            if expected != record_id: errors.append('unstable_id:' + record_id)
            snapshot = snapshots_by_file.get(descriptor['file_id'])
            if snapshot is None or any(descriptor.get(field) != snapshot.get(field) for field in ['file_id', 'source_sha256', 'text_sha256', 'text_version']):
                errors.append('registry_original_source_binding:' + record_id)
        for document in documents.values():
            for key, kind, local_key in [('source_id', 'source', 'exported_txt'), ('text_id', 'text', 'exported_full_text')]:
                descriptor = registry.get(document[key], {})
                if descriptor.get('object_kind') != kind or descriptor.get('local_key') != local_key or descriptor.get('file_id') != document['official_file_id']:
                    errors.append('document_source_registry_identity:' + document['text_id'] + ':' + key)
        if set(registry) != all_ids: errors.append('registry_all_ids_differ')
        cases_by_key = {(row['official_file_id'], row['proposal_local_key']): row for row in tables['cases']}
        behaviors_by_key = {(row['official_file_id'], row['proposal_local_key']): row for row in tables['behaviors']}
        expected_quote_keys = set()
        expected_case_keys, expected_behavior_keys = set(), set()
        inherited_states, expected_annotations = {}, {}

        def bound_eids(fid, prefix):
            return list(dict.fromkeys(eid for entry in bindings_by_file.get(fid, [])
                                     if entry['proposal_field'] == prefix or entry['proposal_field'].startswith(prefix + '.') or
                                     entry['proposal_field'].startswith(prefix + '[') for eid in entry['evidence_ids']))

        def expected_annotation(snapshot, draft, ck, target, field, value, prefix, scope):
            expected_annotations[(target, field)] = {'case_id': ck, 'target_id': target, 'field': field,
                'value': value, 'origin': 'preserved_candidate_draft', 'creator': draft.get('creator') or 'unknown',
                'model_or_prompt_version': draft.get('model_or_prompt_version'),
                'evidence_ids': bound_eids(snapshot['file_id'], prefix), 'scope': scope, 'exclusion_conditions': [],
                'review_status': inherited_states[snapshot['file_id']]['human_review_status'],
                'reviewer': None, 'reviewed_at': None, 'review_note': None,
                'creator_missing_reason': None if draft.get('creator') else '原候选未记录创建者，unknown非人名或审批人'}

        def check_state(actual, expected, context):
            for field, value in expected.items():
                if actual.get(field) != value: errors.append('state_or_scope_drift:' + context + ':' + field)

        for row in extensions['candidate_snapshots']:
            if json_sha(row['base_draft']) != row['base_draft_json_sha256']: errors.append('base_draft_sha:' + row['file_id'])
            effective = row['effective_draft'] if row['effective_draft_reference'] == 'effective_draft' else row['base_draft']
            inherited = state({}, effective, row['wrapper_metadata'])
            inherited_states[row['file_id']] = inherited
            if json_sha(effective) != row['effective_draft_json_sha256']: errors.append('effective_draft_sha:' + row['file_id'])
            match = documents_by_file.get(row['file_id'])
            if match is None: errors.append('snapshot_document:' + row['file_id'])
            elif any(match[field] != row[field] for field in ['text_sha256', 'source_sha256', 'text_version', 'base_draft_json_sha256', 'effective_draft_json_sha256']): errors.append('snapshot_binding:' + row['file_id'])
            if match: check_state(match, inherited, 'document:' + row['file_id'])
            for path, quote in quote_fields(effective):
                key = (row['file_id'], path); expected_quote_keys.add(key)
                if key not in bindings_by_field or bindings_by_field[key]['quote'] != quote: errors.append('original_quote_missing_or_changed:' + str(key))
            for case_index, original in enumerate(effective.get('cases', [])):
                key = (row['file_id'], original['local_key']); expected_case_keys.add(key)
                actual = cases_by_key.get(key)
                if actual is None: errors.append('original_case_missing:' + str(key)); continue
                check_state(actual, state(original, effective, row['wrapper_metadata']), 'case:' + str(key))
                for field, quote_field in [('case_summary', 'case_summary_quotes'), ('institution_hierarchy', 'institution_hierarchy')]:
                    expected_annotation(row, effective, actual['case_id'], actual['case_id'], field, original.get(field),
                                        f'cases[{case_index}].{quote_field}', 'source_context_only')
                for field in ['penalty_doc_no', 'regulator', 'penalty_date', 'behavior_period']:
                    if actual.get(field) != original.get(field, [] if field == 'related_party_names' else None): errors.append('case_fact_drift:' + str(key) + ':' + field)
                expected_compat = case_compat_fields(original)
                for field in ['case_summary', 'missing_reasons', 'related_party_names'] + CASE_COMPAT_METADATA:
                    if (field in actual) != (field in expected_compat) or actual.get(field) != expected_compat.get(field):
                        errors.append('case_compat_drift:' + str(key) + ':' + field)
                if len(actual['parties']) != 1 or actual['parties'][0]['name'] != original.get('party_name') or actual['parties'][0]['party_type'] != original.get('party_type'): errors.append('case_party_drift:' + str(key))
                if len(actual['penalties']) != len(original.get('penalties', [])): errors.append('case_penalty_count:' + str(key))
                for original_pen, actual_pen in zip(original.get('penalties', []), actual['penalties']):
                    if any(actual_pen.get(field) != value for field, value in original_pen.items()): errors.append('case_penalty_drift:' + str(key))
                    if actual_pen['party_id'] != actual['parties'][0]['party_id']: errors.append('case_penalty_party:' + str(key))
                if len(actual['legal_refs']) != len(original.get('legal_refs', [])): errors.append('case_legal_count:' + str(key))
                for ref_index, (original_ref, actual_ref) in enumerate(zip(original.get('legal_refs', []), actual['legal_refs'])):
                    expected_ref = legal_ref_record(original_ref, bound_eids(row['file_id'], f'cases[{case_index}].legal_refs[{ref_index}]'))
                    if actual_ref != expected_ref: errors.append('case_legal_drift:' + str(key))
            for behavior_index, original in enumerate(effective.get('behaviors', [])):
                key = (row['file_id'], original['local_key']); expected_behavior_keys.add(key)
                actual = behaviors_by_key.get(key)
                if actual is None: errors.append('original_behavior_missing:' + str(key)); continue
                check_state(actual, state(original, effective, row['wrapper_metadata']), 'behavior:' + str(key))
                for field in ['risk_tags', 'observed_scene', 'applicable_scenes', 'factor_values', 'material_function', 'risk_mechanism']:
                    qualifier = {'assignment_scope': 'preserved_in_value; no_scope_expansion'} if field in ['risk_tags', 'observed_scene', 'applicable_scenes', 'factor_values'] else 'source_context_only'
                    quote_field = field + '_quotes' if field in ['material_function', 'risk_mechanism'] else field
                    expected_annotation(row, effective, actual['case_id'], actual['behavior_id'], field, original.get(field),
                                        f'behaviors[{behavior_index}].{quote_field}', qualifier)
                for field in ['actor_role', 'target', 'action', 'object', 'regulatory_finding', 'risk_mechanism', 'product_type', 'material_function']:
                    if actual.get(field) != original.get(field): errors.append('behavior_fact_drift:' + str(key) + ':' + field)
                if actual['behavior_summary'] != original.get('summary', ''): errors.append('behavior_summary_drift:' + str(key))
                for field in ['conditions', 'negations', 'exceptions']:
                    if actual[field] != original.get(field, []): errors.append('behavior_qualifier_drift:' + str(key) + ':' + field)
                expected_uncertainties = uncertainty_fields(original)
                for field in ['uncertainties', 'original_uncertainties', 'uncertainties_status', 'uncertainties_missing_reason']:
                    if (field in actual) != (field in expected_uncertainties) or actual.get(field) != expected_uncertainties.get(field):
                        errors.append('behavior_uncertainties_drift:' + str(key) + ':' + field)
                if actual['original_case_key'] != original['case_key']: errors.append('behavior_case_key_drift:' + str(key))
                expected_case = cases_by_key.get((row['file_id'], original['case_key']))
                if expected_case and actual['case_id'] != expected_case['case_id']: errors.append('behavior_cross_case:' + str(key))
                if actual['risk_tags'] != [tag.get('tag') for tag in original.get('risk_tags', [])]: errors.append('behavior_tag_drift:' + str(key))
                if len(actual['risk_tag_basis']) != len(original.get('risk_tags', [])): errors.append('behavior_tag_basis_count:' + str(key))
                for original_tag, actual_tag in zip(original.get('risk_tags', []), actual['risk_tag_basis']):
                    if any(actual_tag.get(field) != value for field, value in original_tag.items()): errors.append('behavior_tag_basis_drift:' + str(key))
        if expected_case_keys != set(cases_by_key): errors.append('case_key_set_drift')
        if expected_behavior_keys != set(behaviors_by_key): errors.append('behavior_key_set_drift')
        if expected_quote_keys != set(bindings_by_field): errors.append('quote_field_set_drift')
        for row in tables['source_inventory']:
            check_state(row, inherited_states.get(row['official_file_id'], {}), 'source:' + row['source_id'])
        for row in evidence.values():
            if row['human_review_status'] != inherited_states.get(row['official_file_id'], {}).get('human_review_status'):
                errors.append('evidence_review_state_drift:' + row['evidence_id'])
        for row in tables['annotations']:
            if row['review_status'] != inherited_states.get(row['official_file_id'], {}).get('human_review_status'):
                errors.append('annotation_review_state_drift:' + row['annotation_id'])
            expected = expected_annotations.get((row['target_id'], row['field']))
            if expected is None or any(row.get(field) != value for field, value in expected.items()):
                errors.append('annotation_original_record_drift:' + row['annotation_id'])
        if len(tables['annotations']) != len(expected_annotations): errors.append('annotation_original_record_count')
        for row in tables['reviews']:
            if row['status'] != inherited_states.get(row['official_file_id'], {}).get('human_review_status') or row['reviewer'] is not None or row['approved_scope'] or row['field_scope'] or row['decision'] is not None:
                errors.append('candidate_snapshot_review_drift:' + row['review_id'])
            snapshot = snapshots_by_file.get(row['official_file_id'])
            if snapshot is None: errors.append('review_snapshot_missing:' + row['review_id']); continue
            wrapper = snapshot['wrapper_metadata']
            expected = {'origin': 'candidate_status_snapshot', 'case_id': None,
                'target_ids': review_targets_by_file.get(row['official_file_id'], []),
                'field_scope': [], 'decision': None, 'status': inherited_states[row['official_file_id']]['human_review_status'],
                'reviewer': None, 'reviewed_at': None, 'original_record_path': wrapper.get('original_candidate_path'),
                'original_record_sha256': wrapper.get('original_candidate_sha256'), 'approved_scope': [], 'exclusion_scope': [],
                'independent_second_review_completed': False, 'completion_flag_origin': 'derived_unrecorded; not_an_assessment',
                'inherited_document_status': inherited_states[row['official_file_id']]}
            if any(row.get(field) != value for field, value in expected.items()): errors.append('review_original_snapshot_drift:' + row['review_id'])
        pointer_tables = {f'data/{name}.jsonl': rows for name, rows in tables.items()}
        pointer_tables.update({f'extensions/{name}.jsonl': rows for name, rows in extensions.items()})
        document_locations = {row['text_id']: {'path': 'data/documents.jsonl', 'line': line_no}
                              for line_no, row in enumerate(tables['documents'], 1)}
        evidence_locations = {row['evidence_id']: {'path': f'{group}/{name}.jsonl', 'line': line_no,
                              'text_id': row['text_id'], 'start_char': row['start_char'], 'end_char': row['end_char']}
                              for group, name, records in [('data', 'evidence', tables['evidence']),
                                                          ('extensions', 'document_evidence', extensions['document_evidence'])]
                              for line_no, row in enumerate(records, 1)}
        expected_readings = {name: {} for name in ['document_index', 'case_reading', 'behavior_reading']}
        for name, key in [('cases', 'case_id'), ('behaviors', 'behavior_id')]:
            for line_no, row in enumerate(tables[name], 1):
                tid = row['text_ids'][0] if name == 'cases' else cases[row['case_id']]['text_ids'][0]
                expected = record_reading(name, row, line_no, tid, document_locations[tid],
                    [evidence_locations[eid] for eid in sorted(quoted_by_target.get(row[key], []))])
                expected_readings['case_reading' if name == 'cases' else 'behavior_reading'][row[key]] = expected
        problem_counts = Counter(row['file_id'] for row in extensions['issues'])
        for snapshot_line, snapshot in enumerate(extensions['candidate_snapshots'], 1):
            fid = snapshot['file_id']; document = documents_by_file[fid]
            draft = snapshot['effective_draft'] if snapshot['effective_draft_reference'] == 'effective_draft' else snapshot['base_draft']
            wrapper, original_source = snapshot['wrapper_metadata'], snapshot['source_record_metadata']
            expected_readings['document_index'][fid] = {'official_file_id': fid, 'file_id': fid,
                'base_draft_json_sha256': snapshot['base_draft_json_sha256'],
                'effective_draft_json_sha256': snapshot['effective_draft_json_sha256'], 'access_scope': 'local_internal',
                'source_sha256': snapshot['source_sha256'], 'text_sha256': snapshot['text_sha256'], 'text_version': snapshot['text_version'],
                'batch': wrapper.get('batch'), 'source_id': document['source_id'], 'text_id': document['text_id'],
                'case_ids': [cases_by_key[(fid, case['local_key'])]['case_id'] for case in draft.get('cases', [])],
                'behavior_ids': [behaviors_by_key[(fid, behavior['local_key'])]['behavior_id'] for behavior in draft.get('behaviors', [])],
                'document_table': document_locations[document['text_id']],
                'candidate_snapshot': {'path': 'extensions/candidate_snapshots.jsonl', 'line': snapshot_line},
                'source_export_location': original_source.get('_export_location'),
                'candidate_export_location': wrapper.get('_export_location'),
                'original_candidate_path': wrapper.get('original_candidate_path'),
                'source_metadata_links': {key: value for key, value in snapshot['document_metadata'].items() if 'path' in key.lower() or 'pdf' in key.lower()},
                'quote_problem_count': problem_counts[fid], 'source_issues': draft.get('source_issues', []),
                **inherited_states[fid]}
        for name in READING_TYPES:
            count = reading_counts.get(name)
            rows = read_jsonl(out / 'reading' / (name + '.jsonl'))
            if len(rows) != count: errors.append('reading_count:' + name)
            reading_key = {'document_index': 'file_id', 'case_reading': 'case_id', 'behavior_reading': 'behavior_id'}[name]
            actual_keys = [row.get(reading_key) for row in rows]
            if len(actual_keys) != len(set(actual_keys)) or set(actual_keys) != set(expected_readings[name]):
                errors.append('reading_original_record_set:' + name)
            for row in rows:
                expected = expected_readings[name].get(row.get(reading_key))
                if row != expected: errors.append('reading_original_record_drift:' + name + ':' + str(row.get(reading_key)))
                for field in ['document_table', 'record_table', 'candidate_snapshot']:
                    if field in row:
                        pointer = row[field]
                        targets = pointer_tables.get(pointer['path'], [])
                        if not isinstance(pointer['line'], int) or isinstance(pointer['line'], bool) or pointer['line'] < 1 or pointer['line'] > len(targets):
                            errors.append('reading_pointer:' + name); continue
                        target = targets[pointer['line'] - 1]
                        expected_field = 'text_id' if field == 'document_table' else ('file_id' if field == 'candidate_snapshot' else ('case_id' if name == 'case_reading' else 'behavior_id'))
                        if target.get(expected_field) != row.get(expected_field): errors.append('reading_pointer_target:' + name)
                if name in ['case_reading', 'behavior_reading']:
                    target_id = row.get('case_id' if name == 'case_reading' else 'behavior_id')
                    located_ids = []
                    if 'evidence_locations' not in row: errors.append('reading_evidence_locations_missing:' + name)
                    for pointer in row.get('evidence_locations', []):
                        if not isinstance(pointer, dict): errors.append('reading_evidence_pointer_type:' + name); continue
                        targets = pointer_tables.get(pointer.get('path'), []) if pointer.get('path') in ['data/evidence.jsonl', 'extensions/document_evidence.jsonl'] else []
                        line = pointer.get('line')
                        if not isinstance(line, int) or isinstance(line, bool) or line < 1 or line > len(targets):
                            errors.append('reading_evidence_pointer:' + name); continue
                        target = targets[line - 1]; located_ids.append(target['evidence_id'])
                        if any(pointer.get(field) != target[field] for field in ['text_id', 'start_char', 'end_char']) or target['text_id'] != row['text_id']:
                            errors.append('reading_evidence_pointer_binding:' + name)
                    if len(located_ids) != len(set(located_ids)) or set(located_ids) != quoted_by_target.get(target_id, set()):
                        errors.append('reading_evidence_complete_set:' + name + ':' + str(target_id))
        if manifest['candidate_count'] != len(documents) or len(extensions['candidate_snapshots']) != len(documents): errors.append('document_candidate_count')
        return {'passed': not errors, 'errors': errors, 'core_counts': {name: len(rows) for name, rows in tables.items()},
                'extension_counts': {name: len(rows) for name, rows in extensions.items()},
                'unmatched_quote_count': len(extensions['issues']),
                'validation_scope': 'mechanical_declared_fields_ids_hashes_spans; semantic_and_human_review_not_claimed'}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {'passed': False, 'errors': errors + [type(exc).__name__ + ':' + str(exc)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--overlays', type=Path, help='JSON object mapping file_id to complete effective draft')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if not args.verify_only:
        if not args.repo: parser.error('--repo is required for generation')
        candidates, sources = load_records(args.repo)
        overlays = json.loads(args.overlays.read_text(encoding='utf-8-sig')) if args.overlays else None
        normalize_records(candidates, sources, args.output, overlays)
    report = verify(args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
