"""Conservative, source-position-preserving retrieval projection (stdlib only).

Model input is bounded source text. Complete logical paragraphs and explicit
adjacent regulatory responses are returned separately, never as invented facts.
Candidate associations describe the draft's provenance, not verified findings.
"""
from __future__ import annotations

import hashlib
import re


_TERMINAL = re.compile(r"[。！？.!?][\"'”’）)]*\s*$")
_SECTION = re.compile(r"^(?:[一二三四五六七八九十]+[、．.]|第[一二三四五六七八九十\d]+[章节条]|综上[，,:：]|上述事实|经查[，,:：]|对上述.*(?:申辩|意见))")
_RESPONSE = re.compile(r"^(?:对(?:上述|当事人|其).*?(?:申辩|陈述|意见)|经(?:我会|我局|本局|本机关).*(?:复核|审查)).*(?:认为|复核|不予采纳|不予接受)|^(?:我会|我局|本局|本机关).*(?:申辩.*不予采纳|复核.*认为)")
_CLAIM_CONTINUATION = re.compile(r"^(?:其(?:请求|认为|提出|称|表示)|该(?:请求|申辩|理由|意见)|请求(?:减免|从轻|减轻|免予)|主要理由|理由[为是]|[一二三]是)")
_RESPONSE_CONTINUATION = re.compile(r"^(?:[（(]\d+[）)]|因此[，,].*(?:申辩|不予采纳)|据此[，,].*(?:申辩|不予采纳)|(?:我会|我局|本局|本机关)(?:不予(?:采纳|接受)|认为|经复核))")


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _span(start, end):
    return {"start": start, "end": end}


def exact_spans(source, quote):
    """Return every exact occurrence, including overlaps; do not infer a match."""
    if not isinstance(quote, str) or not quote.strip():
        return []
    result, offset = [], 0
    while True:
        start = source.find(quote, offset)
        if start < 0:
            return result
        result.append(_span(start, start + len(quote)))
        offset = start + 1


def chunk_spans(text, size=300, overlap=40):
    """Bound model input; a soft newline/table cell is never a preferred break.

    A sentence longer than the cap must still be split; its whole parent remains
    in context and the output explicitly records the incomplete input boundary.
    """
    if not isinstance(size, int) or not isinstance(overlap, int) or size <= overlap or overlap < 0:
        raise ValueError("chunk size must exceed nonnegative overlap")
    result, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            lower = start + max(overlap + 1, int(size * 0.65))
            breaks = [m.end() for m in re.finditer(r"[。！？]", text[lower:end])]
            if breaks:
                end = lower + breaks[-1]
        result.append((start, end))
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return result


def parent_spans(source):
    """Recover continuous parents without removing the source's soft wraps.

    Blank lines and explicit section starts bound paragraphs. Otherwise wrapped
    lines stay together until a sentence terminal except explicit claimant or
    authority continuation sentences. Tab/pipe rows retain their table block.
    This is deliberately structural rather than a semantic classifier.
    """
    result, begin, end, offset, table = [], None, 0, 0, False

    def finish():
        nonlocal begin, table
        if begin is not None:
            a, b = begin, end
            while a < b and source[a].isspace():
                a += 1
            while b > a and source[b - 1].isspace():
                b -= 1
            if a < b:
                result.append(_span(a, b))
            begin = None
            table = False

    for line in source.splitlines(keepends=True):
        content = line.strip()
        if not content:
            finish()
        else:
            row = "\t" in line or content.count("|") >= 2
            if begin is not None:
                previous = source[begin:end].strip()
                section_start = _SECTION.match(content) and not (table and row)
                continuation = (("申辩" in previous and not _RESPONSE.match(previous)
                                 and _CLAIM_CONTINUATION.match(content))
                                or (_RESPONSE.match(previous) and _RESPONSE_CONTINUATION.match(content)))
                if section_start or (not table and _TERMINAL.search(previous) and not continuation):
                    finish()
            if begin is None:
                begin = offset
            end = offset + len(line)
            table |= row
        offset += len(line)
    finish()
    return result


def _merge_spans(source, spans):
    unique = sorted({(s["start"], s["end"]) for s in spans})
    result = []
    for a, b in unique:
        if result and (a <= result[-1]["end"] or not source[result[-1]["end"]:a].strip()):
            result[-1]["end"] = max(b, result[-1]["end"])
        else:
            result.append(_span(a, b))
    return result


def _context_spans(source, positions, parents):
    contexts = []
    for position in positions:
        indices = [i for i, p in enumerate(parents)
                   if p["start"] < position["end"] and position["start"] < p["end"]]
        if not indices:
            contexts.append(dict(position))
            continue
        first, last = indices[0], indices[-1]
        parent_text = source[parents[first]["start"]:parents[last]["end"]]
        # Only an explicit adjacent response can extend a claimant's paragraph.
        if "申辩" in parent_text and not _RESPONSE.match(parent_text) and last + 1 < len(parents):
            following = source[parents[last + 1]["start"]:parents[last + 1]["end"]]
            if _RESPONSE.match(following):
                last += 1
                while last + 1 < len(parents):
                    following = source[parents[last + 1]["start"]:parents[last + 1]["end"]]
                    if not _RESPONSE_CONTINUATION.match(following):
                        break
                    last += 1
        contexts.append(_span(parents[first]["start"], parents[last]["end"]))
    return _merge_spans(source, contexts)


def behavior_quotes(behavior, coverage):
    """Only existing quotation fields; never summaries, values or risk labels."""
    quotes = [("finding", behavior.get("finding_quote"))]
    for key in ("risk_mechanism_quotes", "material_function_quotes"):
        quotes.extend(("support", q) for q in behavior.get(key, []) if isinstance(q, str))
    quotes.append(("product", behavior.get("product_quote")))
    for field, kind in (("conditions", "condition"), ("negations", "negation"),
                        ("exceptions", "exception"), ("uncertainties", "uncertainty"),
                        ("materials", "material"), ("factor_values", "support")):
        for entry in behavior.get(field, []):
            if isinstance(entry, dict):
                quotes.append((kind, entry.get("quote")))
                quotes.extend((kind, q) for q in entry.get("quotes", []) if isinstance(q, str))
                if field == "materials":
                    quotes.append((kind, entry.get("original_expression_quote")))
    for row in coverage:
        if behavior.get("local_key") in row.get("behavior_keys", []):
            quotes.append(("coverage", row.get("quote")))
    # A quote keeps all channel kinds in provenance without another model input.
    grouped = {}
    for kind, quote in quotes:
        if isinstance(quote, str) and quote.strip():
            grouped.setdefault(quote, [])
            if kind not in grouped[quote]:
                grouped[quote].append(kind)
    return grouped.items()


def project_document(file_id, full_text, draft, candidate_sha256, chunk_chars=300, overlap_chars=40):
    """Return deduplicated structured/raw units and source-integrity audit rows.

    Identical source bodies are indexed once per independent corpus. Scalar V1
    identifiers are compatibility representatives; use the plural IDs and
    associations for attribution, especially on ambiguous shared evidence.
    """
    chunk_spans("", chunk_chars, overlap_chars)  # Validate even an empty source.
    if not isinstance(full_text, str) or draft.get("file_id") != file_id:
        raise ValueError(f"Candidate file_id or source type mismatch: {file_id}")
    cases = {}
    for case in draft.get("cases", []):
        key = case.get("local_key")
        if not key or key in cases:
            raise ValueError(f"Invalid or duplicate case key: {file_id}: {key}")
        cases[key] = case
    seen_behaviors = set()
    for behavior in draft.get("behaviors", []):
        key = behavior.get("local_key")
        if not key or key in seen_behaviors or behavior.get("case_key") not in cases:
            raise ValueError(f"Invalid behavior/case reference: {file_id}: {key}/{behavior.get('case_key')}")
        seen_behaviors.add(key)
    source_sha = _sha(full_text)
    parents = parent_spans(full_text)
    units, audit, by_body, positions_cache = [], [], {}, {}

    def positions(text):
        if text not in positions_cache:
            positions_cache[text] = exact_spans(full_text, text)
        return positions_cache[text]

    def add(corpus, body, parent_positions=None, association=None, hard_split=False):
        body = body.strip()
        if not body:
            return
        key = (corpus, body)
        if key not in by_body:
            spans = positions(body)
            context_positions = _context_spans(full_text, spans, parents)
            by_body[key] = dict(
                unit_id=f"{corpus}:{file_id}:V2:{_sha(body)}", corpus=corpus,
                file_id=file_id, case_id=f"{file_id}:SOURCE", behavior_id=None, behavior_key=None,
                case_ids=[], behavior_ids=[], associations=[], evidence_kind="source", evidence_kinds=[],
                source_sha256=source_sha, candidate_sha256=candidate_sha256,
                semantic_status=draft.get("semantic_status", "candidate"),
                human_review_status=draft.get("human_review_status", "pending"),
                text=body, prefix="", prefix_source_spans=[], prefix_evidence_ambiguous=False,
                source_text=body, source_spans=[dict(s) for s in spans],
                parent_span=dict(context_positions[0]) if len(context_positions) == 1 else None,
                parent_source_spans=[dict(s) for s in context_positions], parent_id=f"{file_id}:SOURCE",
                context_spans=context_positions, context_segments=[], context_text="", context_source_text="",
                parent_source_text="", evidence_ambiguous=False, ambiguity_reason=None,
                context_ambiguous=False, context_long=False, input_hard_split=False,
                qualifier_quotes={"conditions": [], "negations": [], "exceptions": []},
                qualifier_source_links=[],
            )
            units.append(by_body[key])
        unit = by_body[key]
        if parent_positions:
            unit["context_spans"] = _merge_spans(full_text, unit["context_spans"] +
                                                _context_spans(full_text, parent_positions, parents))
        unit["input_hard_split"] |= hard_split
        if association is not None and association not in unit["associations"]:
            unit["associations"].append(association)
            qualifier_positions = []
            for link in association["qualifier_source_links"]:
                qualifier_positions.extend(link["source_spans"])
                if link not in unit["qualifier_source_links"]:
                    unit["qualifier_source_links"].append(link)
                if link["quote"] not in unit["qualifier_quotes"][link["field"]]:
                    unit["qualifier_quotes"][link["field"]].append(link["quote"])
            if qualifier_positions:
                unit["context_spans"] = _merge_spans(full_text, unit["context_spans"] +
                                                    _context_spans(full_text, qualifier_positions, parents))
            for field, value in (("case_ids", association["case_id"]),
                                 ("behavior_ids", association["behavior_id"])):
                if value not in unit[field]:
                    unit[field].append(value)
            for kind in association["evidence_kinds"]:
                if kind not in unit["evidence_kinds"]:
                    unit["evidence_kinds"].append(kind)

    # Source fallback cannot invent a party or an event. Each corpus is indexed independently.
    for parent in parents:
        text = full_text[parent["start"]:parent["end"]]
        for a, b in chunk_spans(text, chunk_chars, overlap_chars):
            hard_split = (a > 0 and text[a - 1] not in "。！？") or (b < len(text) and text[b - 1] not in "。！？")
            for corpus in ("structured", "raw"):
                add(corpus, text[a:b], hard_split=hard_split)

    for behavior in draft.get("behaviors", []):
        key, case_key = behavior["local_key"], behavior["case_key"]
        party = cases[case_key].get("party_quote")
        party_positions = positions(party) if isinstance(party, str) and party.strip() else []
        if party and not party_positions:
            audit.append(dict(file_id=file_id, behavior_key=key, kind="party", quote=party,
                              reason="not_exact_source_substring"))
        qualifier_links = []
        for field in ("conditions", "negations", "exceptions"):
            for entry in behavior.get(field, []):
                if not isinstance(entry, dict):
                    continue
                quoted = [entry.get("quote")] + [q for q in entry.get("quotes", []) if isinstance(q, str)]
                for quote in quoted:
                    if not isinstance(quote, str) or not quote.strip() or not positions(quote):
                        continue
                    link = dict(case_id=f"{file_id}:{case_key}", behavior_id=f"{file_id}:{key}",
                                field=field, quote=quote, source_spans=[dict(s) for s in positions(quote)],
                                linkage_status="candidate_behavior_link_not_verified")
                    if link not in qualifier_links:
                        qualifier_links.append(link)
        qualifier_ambiguous = any(len(link["source_spans"]) > 1 for link in qualifier_links)
        for quote, kinds in behavior_quotes(behavior, draft.get("coverage", [])):
            quote_positions = positions(quote)
            if not quote_positions:
                audit.append(dict(file_id=file_id, behavior_key=key, kind=kinds[0], quote=quote,
                                  reason="not_exact_source_substring"))
                continue
            if len(quote_positions) > 1:
                audit.append(dict(file_id=file_id, behavior_key=key, kind=kinds[0], quote=quote,
                                  reason="multiple_exact_occurrences", spans=[dict(s) for s in quote_positions]))
            association = dict(case_id=f"{file_id}:{case_key}", behavior_id=f"{file_id}:{key}",
                               case_key=case_key, behavior_key=key, actor_role=behavior.get("actor_role", "unknown"),
                               evidence_kind=kinds[0], evidence_kinds=list(kinds), quote=quote,
                               quote_source_spans=[dict(s) for s in quote_positions], party_quote=party,
                               party_source_spans=[dict(s) for s in party_positions],
                               qualifier_source_links=qualifier_links,
                               attribution_status="candidate_association_not_verified",
                               quote_position_ambiguous=len(quote_positions) > 1,
                               party_position_ambiguous=len(party_positions) > 1,
                               qualifier_position_ambiguous=qualifier_ambiguous,
                               source_position_ambiguous=(len(quote_positions) > 1 or len(party_positions) > 1
                                                          or qualifier_ambiguous),
                               semantic_status=draft.get("semantic_status", "candidate"),
                               human_review_status=draft.get("human_review_status", "pending"))
            for a, b in chunk_spans(quote, chunk_chars, overlap_chars):
                hard_split = (a > 0 and quote[a - 1] not in "。！？") or (b < len(quote) and quote[b - 1] not in "。！？")
                add("structured", quote[a:b], quote_positions, association, hard_split)

    for unit in units:
        unit["case_ids"].sort()
        unit["behavior_ids"].sort()
        unit["associations"].sort(key=lambda a: (a["case_id"], a["behavior_id"], a["quote"]))
        if unit["associations"]:
            unit["case_id"] = unit["case_ids"][0]
            unit["behavior_id"] = unit["behavior_ids"][0]
            unit["behavior_key"] = unit["associations"][0]["behavior_key"]
            unit["actor_role"] = (unit["associations"][0]["actor_role"]
                                  if len({a["actor_role"] for a in unit["associations"]}) == 1 else "unknown")
            unit["evidence_kind"] = unit["evidence_kinds"][0]
        spans = unit["context_spans"]
        segments = [{"text": full_text[s["start"]:s["end"]], "span": dict(s)} for s in spans]
        unit["context_segments"] = segments
        context = "".join(segment["text"] for segment in segments)
        unit["context_source_text"] = unit["parent_source_text"] = context
        unit["context_text"] = "\n\n[原文间隔，分段摘录]\n\n".join(segment["text"] for segment in segments)
        unit["parent_source_spans"] = [dict(s) for s in spans]
        unit["parent_span"] = dict(spans[0]) if len(spans) == 1 else None
        unit["context_long"] = len(unit["context_text"]) > chunk_chars
        reasons = []
        if len(unit["source_spans"]) > 1:
            reasons.append("multiple exact source occurrences; candidate positions do not prove subject attribution")
        if len(unit["case_ids"]) > 1:
            reasons.append("multiple candidate case associations; shared text does not prove each actor performed it")
        if any(a["party_position_ambiguous"] for a in unit["associations"]):
            reasons.append("multiple exact party quote occurrences; party position does not prove subject attribution")
        if any(a["qualifier_position_ambiguous"] for a in unit["associations"]):
            reasons.append("multiple exact qualifier quote occurrences; candidate linkage does not resolve source position")
        if unit["context_long"]:
            reasons.append("long_parent_or_combined_context; full returned display exceeds model input character cap")
        if unit["input_hard_split"]:
            reasons.append("source_boundary_inside_sentence; do not interpret excerpt without full context")
        if len(spans) > 1:
            reasons.append("multiple_context_blocks; concatenated exact source blocks do not imply event continuity")
        unit["evidence_ambiguous"] = bool(reasons)
        unit["ambiguity_reason"] = "; ".join(reasons) or None
        unit["context_ambiguous"] = (len(spans) > 1 or len(unit["case_ids"]) > 1
                                     or any(a["party_position_ambiguous"] or a["qualifier_position_ambiguous"]
                                            for a in unit["associations"]))
    return units, audit
