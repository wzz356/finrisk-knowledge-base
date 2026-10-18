"""Independent, local-only retrieval experiment. No production index writes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
WORKSPACE = HERE.parent.parent
DEFAULT_SRC = Path("C:/Users/11051/Desktop/金融比赛/复赛/FinRisk_复赛改进/src")
DEFAULT_EMBEDDING = Path("C:/Users/11051/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5/snapshots/7999e1d3359715c523056ef9478215996d62a620")
DEFAULT_RERANKER = Path("C:/Users/11051/.cache/huggingface/hub/models--BAAI--bge-reranker-base/snapshots/2cfc18c9415c912f9d8155881c133215df768a70")
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："
ROLE_TEXT = {
    "institution_violation": "机构行为记录",
    "responsible_person": "责任人员记录（不扩张责任层次）",
    "direct_person_violation": "个人行为记录",
    "unknown": "责任层次未知",
}


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_runner_hash(expected):
    if sha_file(__file__) != expected:
        raise RuntimeError("runner.py changed during this process; refusing to claim completed provenance")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def read_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def latest_candidates(root):
    selected = {}
    revisions = {}
    for path in sorted(Path(root).rglob("*.json")):
        match = re.fullmatch(r"(F\d{6})_r0(?:_fix(\d+))?\.json", path.name)
        if not match:
            continue
        fid, revision = match[1], int(match[2] or 0)
        if fid in revisions and revision == revisions[fid]:
            if sha_file(path) != sha_file(selected[fid]):
                raise ValueError(f"Conflicting latest candidate: {fid}, revision {revision}")
        if fid not in selected or revision > revisions[fid]:
            selected[fid], revisions[fid] = path, revision
    return dict(sorted(selected.items()))


def chunk_spans(text, size=300, overlap=40):
    if size <= overlap or overlap < 0:
        raise ValueError("chunk size must exceed nonnegative overlap")
    spans = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            lower = start + max(overlap + 1, int(size * 0.65))
            breaks = [m.end() for m in re.finditer(r"[\n。！？；]", text[lower:end])]
            if breaks:
                end = lower + breaks[-1]
        spans.append((start, end))
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return spans


def exact_spans(source, quote):
    if not isinstance(quote, str) or not quote.strip():
        return []
    result, offset = [], 0
    while True:
        start = source.find(quote, offset)
        if start < 0:
            break
        result.append({"start": start, "end": start + len(quote)})
        offset = start + 1
    return result


def behavior_quotes(behavior, coverage):
    # Values, summaries, risk labels and inferred scene descriptions are never projected.
    quoted = [("finding", behavior.get("finding_quote"))]
    for key in ("risk_mechanism_quotes", "material_function_quotes"):
        quoted.extend(("support", q) for q in behavior.get(key, []) if isinstance(q, str))
    quoted.append(("product", behavior.get("product_quote")))
    for field, kind in (("conditions", "condition"), ("negations", "negation"),
                        ("exceptions", "exception"), ("uncertainties", "uncertainty"),
                        ("materials", "material"), ("factor_values", "support")):
        for entry in behavior.get(field, []):
            if isinstance(entry, dict):
                quoted.append((kind, entry.get("quote")))
                quoted.extend((kind, q) for q in entry.get("quotes", []) if isinstance(q, str))
                if field == "materials":
                    quoted.append((kind, entry.get("original_expression_quote")))
    for row in coverage:
        if behavior.get("local_key") in row.get("behavior_keys", []):
            quoted.append(("coverage", row.get("quote")))
    seen = set()
    for kind, quote in quoted:
        if isinstance(quote, str) and quote.strip() and quote not in seen:
            seen.add(quote)
            yield kind, quote


def project_document(fid, source, candidate, candidate_sha, size=300, overlap=40):
    if candidate.get("file_id") != fid:
        raise ValueError(f"Candidate file_id mismatch: {fid}")
    source_sha = sha_text(source)
    units, audit = [], []
    cases = {case["local_key"]: case for case in candidate.get("cases", [])}
    base = dict(file_id=fid, source_sha256=source_sha, candidate_sha256=candidate_sha)
    for corpus in ("structured", "raw"):
        for i, (start, end) in enumerate(chunk_spans(source, size, overlap)):
            if not source[start:end].strip():
                continue
            units.append(dict(base, unit_id=f"{corpus}:{fid}:SOURCE:{i:05d}", case_id=f"{fid}:SOURCE",
                              behavior_id=None, behavior_key=None, corpus=corpus, prefix="",
                              source_text=source[start:end], text=source[start:end],
                              source_spans=[dict(start=start, end=end)], evidence_kind="source",
                              parent_id=f"{fid}:SOURCE", parent_source_text=source,
                              parent_source_spans=[dict(start=0, end=len(source))]))
    for behavior in candidate.get("behaviors", []):
        local_key, case_key = behavior.get("local_key"), behavior.get("case_key")
        if not local_key or case_key not in cases:
            raise ValueError(f"Invalid behavior/case reference: {fid}: {local_key}/{case_key}")
        case = cases[case_key]
        party_quote = case.get("party_quote")
        party_spans = exact_spans(source, party_quote)
        if party_quote and not party_spans:
            audit.append(dict(file_id=fid, behavior_key=local_key, kind="party", quote=party_quote,
                              reason="not_exact_source_substring"))
        role = ROLE_TEXT.get(behavior.get("actor_role"), "责任层次未知")
        prefix_parts = []
        prefix_spans = []
        if party_spans:
            # The metadata explicitly marks this as a source quotation, not a guessed name.
            prefix_parts.append("原文主体：" + party_quote)
            prefix_spans.extend(party_spans)
        prefix_parts.append("角色元数据：" + role)
        finding = behavior.get("finding_quote")
        finding_spans = exact_spans(source, finding)
        if finding_spans:
            # Short exact background; full finding remains in parent metadata and quote units.
            context = finding[:100]
            prefix_parts.append("原文行为背景：" + context)
            prefix_spans.extend(dict(start=position["start"], end=position["start"] + len(context)) for position in finding_spans)
        prefix = "\n".join(prefix_parts)
        for qi, (kind, quote) in enumerate(behavior_quotes(behavior, candidate.get("coverage", []))):
            positions = exact_spans(source, quote)
            if not positions:
                audit.append(dict(file_id=fid, behavior_key=local_key, kind=kind, quote=quote,
                                  reason="not_exact_source_substring"))
                continue
            if len(positions) > 1:
                audit.append(dict(file_id=fid, behavior_key=local_key, kind=kind, quote=quote,
                                  reason="multiple_exact_occurrences", spans=positions))
            for ci, (start, end) in enumerate(chunk_spans(quote, size, overlap)):
                if not quote[start:end].strip():
                    continue
                absolute = [dict(start=position["start"] + start, end=position["start"] + end) for position in positions]
                units.append(dict(base, unit_id=f"structured:{fid}:{local_key}:{qi:03d}:{ci:04d}",
                                  case_id=f"{fid}:{case_key}", behavior_id=f"{fid}:{local_key}",
                                  behavior_key=local_key, corpus="structured", prefix=prefix,
                                  prefix_source_spans=prefix_spans, actor_role=behavior.get("actor_role", "unknown"),
                                  source_text=quote[start:end], text=prefix + "\n" + quote[start:end],
                                  source_spans=absolute, evidence_kind=kind,
                                  evidence_ambiguous=len(positions) > 1,
                                  ambiguity_reason="multiple exact source occurrences; candidate positions do not prove subject attribution" if len(positions) > 1 else None,
                                  prefix_evidence_ambiguous=len(party_spans) > 1 or len(finding_spans) > 1,
                                  parent_id=f"{fid}:{local_key}:quote:{qi:03d}", parent_source_text=quote,
                                  parent_source_spans=positions,
                                  qualifier_quotes={field: [e.get("quote") for e in behavior.get(field, [])
                                                            if isinstance(e, dict) and exact_spans(source, e.get("quote"))]
                                                    for field in ("conditions", "negations", "exceptions")}))
    return units, audit


def ordered_text_sha(units):
    digest = hashlib.sha256()
    for unit in units:
        value = json.dumps([unit["unit_id"], unit["text"]], ensure_ascii=False, separators=(",", ":"))
        digest.update(value.encode("utf-8") + b"\n")
    return digest.hexdigest()


def cache_key(text_sha, config):
    return sha_text(json.dumps(dict(text_sha=text_sha, config=config), sort_keys=True, ensure_ascii=False))


def write_token_audit(handle, rows, *, corpus, cache_hit, cache_key):
    for row in rows:
        handle.write(json.dumps(row | dict(corpus=corpus, cache_hit=cache_hit, cache_key=cache_key)) + "\n")
    handle.flush()


def validate_token_audit(rows, expected_ids, max_length):
    if not isinstance(rows, list) or len(rows) != len(expected_ids):
        raise ValueError("Cached token audit count mismatch")
    if [row.get("id") for row in rows] != list(expected_ids):
        raise ValueError("Cached token audit input order mismatch")
    for row in rows:
        before, used = row.get("input_tokens"), row.get("used_tokens")
        if not isinstance(before, int) or not isinstance(used, int) or not 0 < used <= min(before, max_length):
            raise ValueError("Invalid cached token lengths")
        if row.get("truncated") != (before > max_length):
            raise ValueError("Invalid cached truncation flag")


def ranked_rows(rows):
    return [dict(row, rank=i) for i, row in enumerate(rows, 1)]


def rrf(routes, k=60, top_k=200):
    scores = {}
    for route in routes:
        seen = set()
        rank = 0
        for row in route:
            uid = row["unit_id"]
            if uid in seen:
                continue
            seen.add(uid)
            rank += 1
            scores[uid] = scores.get(uid, 0.0) + 1 / (k + rank)
    pairs = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))[:top_k]
    return ranked_rows([dict(unit_id=uid, score=score) for uid, score in pairs])


def evidence_row(unit, score):
    return {key: unit[key] for key in ("file_id", "unit_id", "text", "prefix", "source_text", "behavior_id", "source_spans")} | {
        "score": float(score), "evidence_ambiguous": unit.get("evidence_ambiguous", False),
        "ambiguity_reason": unit.get("ambiguity_reason"), "prefix_evidence_ambiguous": unit.get("prefix_evidence_ambiguous", False)}


def aggregate(ranked, unit_map, top_k=20):
    case_map, file_map = {}, {}
    seen_units = set()
    for hit in ranked:
        uid = hit["unit_id"]
        if uid in seen_units:
            continue
        seen_units.add(uid)
        unit, score = unit_map[uid], float(hit["score"])
        cid, fid = unit["case_id"], unit["file_id"]
        is_source = cid == f"{fid}:SOURCE"
        if not is_source and (cid not in case_map or score > case_map[cid]["score"]):
            case_map[cid] = dict(evidence_row(unit, score), case_id=cid)
        if fid not in file_map:
            file_map[fid] = dict(evidence_row(unit, score), case_ids=[])
        if not is_source and cid not in file_map[fid]["case_ids"]:
            file_map[fid]["case_ids"].append(cid)
        if score > file_map[fid]["score"]:
            case_ids = file_map[fid]["case_ids"]
            file_map[fid] = dict(evidence_row(unit, score), case_ids=case_ids)
    cases = sorted(case_map.values(), key=lambda row: (-row["score"], row["case_id"]))
    files = sorted(file_map.values(), key=lambda row: (-row["score"], row["file_id"]))
    return ranked_rows(cases[:top_k]), ranked_rows(files[:top_k])


def prepare(args):
    started = time.perf_counter()
    runner_sha = RUNNER_SHA256
    check_runner_hash(runner_sha)
    selected = latest_candidates(args.authored)
    if len(selected) != args.expected_files:
        raise ValueError(f"Expected {args.expected_files} latest candidates, found {len(selected)}")
    args.prepared.mkdir(parents=True, exist_ok=True)
    write_json(args.prepared / "manifest.json", dict(status="preparing", expected_files=args.expected_files))
    handles = {corpus: (args.prepared / f"{corpus}.jsonl").open("w", encoding="utf-8") for corpus in ("structured", "raw")}
    audit_handle = (args.prepared / "projection_audit.jsonl").open("w", encoding="utf-8")
    sources, counts, audit_counts = [], Counter(), Counter()
    try:
        for index, (fid, candidate_path) in enumerate(selected.items(), 1):
            task_path = args.tasks / f"{fid}.json"
            task, candidate = read_json(task_path), read_json(candidate_path)
            source = task.get("full_text")
            if not isinstance(source, str) or not source.strip():
                raise ValueError(f"Missing original full_text: {task_path}")
            if task.get("file_id") != fid:
                raise ValueError(f"Task file_id mismatch: {task_path}")
            candidate_sha = sha_file(candidate_path)
            units, audit = project_document(fid, source, candidate, candidate_sha, args.chunk_chars, args.overlap_chars)
            for unit in units:
                handles[unit["corpus"]].write(json.dumps(unit, ensure_ascii=False, separators=(",", ":")) + "\n")
                counts[unit["corpus"]] += 1
                counts[f'{unit["corpus"]}:{unit["evidence_kind"]}'] += 1
            for row in audit:
                audit_handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                audit_counts[row["reason"]] += 1
            sources.append(dict(file_id=fid, candidate_path=str(candidate_path.resolve()), candidate_sha256=candidate_sha,
                                source_path=str(task_path.resolve()), task_sha256=sha_file(task_path), source_sha256=sha_text(source)))
            if index % 500 == 0:
                print(json.dumps(dict(event="prepare_progress", files=index, units=dict(counts)), ensure_ascii=True), flush=True)
    finally:
        for handle in handles.values():
            handle.close()
        audit_handle.close()
    corpus_manifest = {}
    for corpus in handles:
        path = args.prepared / f"{corpus}.jsonl"
        corpus_manifest[corpus] = dict(path=str(path.resolve()), sha256=sha_file(path), count=counts[corpus],
                                       ordered_unit_text_sha256=ordered_text_sha(read_jsonl(path)))
    check_runner_hash(runner_sha)
    manifest = dict(status="complete", source_files=len(sources), source_manifest=sources, corpora=corpus_manifest,
                    projection=dict(chunk_chars=args.chunk_chars, overlap_chars=args.overlap_chars,
                                    quotes="contiguous exact original substring", source_fallback="fid:SOURCE",
                                    prefix="exact party_quote, conservative role metadata, exact finding prefix <=100 chars",
                                    counts=dict(counts), audit_counts=dict(audit_counts)),
                    prepare_seconds=time.perf_counter() - started, runner_sha256=runner_sha)
    write_json(args.prepared / "manifest.json", manifest)
    print(json.dumps(dict(event="prepare_complete", files=len(sources), counts=dict(counts), seconds=manifest["prepare_seconds"])), flush=True)


def model_fingerprint(path):
    path = Path(path).resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Local model missing: {path}")
    files = []
    for item in sorted(path.rglob("*")):
        if item.is_file():
            files.append(dict(path=item.relative_to(path).as_posix(), size=item.stat().st_size, sha256=sha_file(item)))
    if not files:
        raise ValueError(f"Empty local model directory: {path}")
    return dict(path=str(path), revision=path.name, files=files,
                cache_sha256=sha_text(json.dumps(files, sort_keys=True)))


class LocalModels:
    def __init__(self, args):
        load_started = time.perf_counter()
        # Import only for --run; never network, remote code, pickled vector cache, or fallback.
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        import numpy as np
        import torch
        import transformers
        from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer
        self.np, self.torch, self.args = np, torch, args
        if args.device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but unavailable")
        if args.precision == "float16" and args.device != "cuda":
            raise ValueError("float16 requires CUDA")
        self.embedding_info = model_fingerprint(args.embedding_model)
        self.reranker_info = model_fingerprint(args.reranker_model)
        self.embed_tokenizer = AutoTokenizer.from_pretrained(str(args.embedding_model), local_files_only=True, trust_remote_code=False)
        self.rerank_tokenizer = AutoTokenizer.from_pretrained(str(args.reranker_model), local_files_only=True, trust_remote_code=False)
        dtype = torch.float16 if args.precision == "float16" else torch.float32
        self.embedding = AutoModel.from_pretrained(str(args.embedding_model), local_files_only=True, trust_remote_code=False, torch_dtype=dtype)
        self.reranker = AutoModelForSequenceClassification.from_pretrained(str(args.reranker_model), local_files_only=True, trust_remote_code=False, torch_dtype=dtype)
        self.embedding.to(args.device).eval()
        self.reranker.to(args.device).eval()
        self.log = dict(python=sys.version, platform=platform.platform(), cpu=platform.processor(), cpu_count=os.cpu_count(),
                        torch=torch.__version__, transformers=transformers.__version__, numpy=np.__version__,
                        torch_cpu_threads=torch.get_num_threads(), torch_interop_threads=torch.get_num_interop_threads(),
                        device=args.device, precision=args.precision,
                        gpu=torch.cuda.get_device_name(0) if args.device == "cuda" else None,
                        cuda_runtime=torch.version.cuda, embedding=self.embedding_info, reranker=self.reranker_info,
                        query_instruction=QUERY_INSTRUCTION, truncation=[], cache_events=[],
                        model_load_seconds=time.perf_counter()-load_started)
        self.args.output.parent.mkdir(parents=True, exist_ok=True)
        self.token_handle = (Path(str(args.output) + ".token_audit.jsonl")).open("w", encoding="utf-8")

    def encode(self, rows, kind, corpus):
        started = time.perf_counter()
        texts = [(QUERY_INSTRUCTION + row["text"]) if kind == "query" else row["text"] for row in rows]
        binding = dict(model=self.embedding_info, tokenizer_class=type(self.embed_tokenizer).__name__,
                       token_audit_schema_version=2,
                       max_length=self.args.max_length, query_instruction=QUERY_INSTRUCTION if kind == "query" else "",
                       pooling="CLS", normalization="L2", torch=self.log["torch"], transformers=self.log["transformers"],
                       precision=self.args.precision, kind=kind)
        text_sha = ordered_text_sha([dict(unit_id=row.get("unit_id", row.get("query_id")), text=text) for row, text in zip(rows, texts)])
        key = cache_key(text_sha, binding)
        self.args.cache.mkdir(parents=True, exist_ok=True)
        vector_path = self.args.cache / f"{key}.npy"
        meta_path = self.args.cache / f"{key}.json"
        if vector_path.exists() and meta_path.exists():
            metadata = read_json(meta_path)
            if metadata.get("key") != key or metadata.get("npy_sha256") != sha_file(vector_path):
                raise ValueError(f"Invalid vector cache: {key}")
            vectors = self.np.load(vector_path, allow_pickle=False)
            if vectors.ndim != 2 or vectors.shape[0] != len(rows):
                raise ValueError(f"Invalid vector shape: {vectors.shape}")
            audit = metadata.get("token_audit")
            validate_token_audit(audit, [row.get("unit_id", row.get("query_id")) for row in rows], self.args.max_length)
            write_token_audit(self.token_handle, audit, corpus=corpus, cache_hit=True, cache_key=key)
            self.log["cache_events"].append(dict(corpus=corpus, kind=kind, key=key, hit=True,
                                                 seconds=time.perf_counter()-started))
            self.log["truncation"].append(metadata["token_summary"] | dict(corpus=corpus, cache_hit=True))
            return vectors
        batches, total_truncated, maximum, token_audit = [], 0, 0, []
        for start in range(0, len(texts), self.args.batch_size):
            batch = texts[start:start + self.args.batch_size]
            unlimited = self.embed_tokenizer(batch, truncation=False, padding=False)
            lengths = [len(ids) for ids in unlimited["input_ids"]]
            tokens = self.embed_tokenizer(batch, padding=True, truncation=True, max_length=self.args.max_length, return_tensors="pt")
            used = tokens["attention_mask"].sum(dim=1).tolist()
            for row, length, actual in zip(rows[start:start + self.args.batch_size], lengths, used):
                truncated = length > self.args.max_length
                total_truncated += truncated
                maximum = max(maximum, length)
                token_audit.append(dict(stage="embedding", corpus=corpus, kind=kind,
                                        id=row.get("unit_id", row.get("query_id")),
                                        input_tokens=length, used_tokens=actual, truncated=truncated,
                                        truncated_tokens=max(0, length-actual), max_length=self.args.max_length))
            tokens = {key: value.to(self.args.device) for key, value in tokens.items()}
            with self.torch.inference_mode():
                hidden = self.embedding(**tokens).last_hidden_state[:, 0]
                vectors = self.torch.nn.functional.normalize(hidden.float(), p=2, dim=1)
            batches.append(vectors.cpu().numpy())
            if start and start % (self.args.batch_size * 250) == 0:
                print(json.dumps(dict(event="encode_progress", corpus=corpus, kind=kind, rows=start, total=len(texts))), flush=True)
        vectors = self.np.concatenate(batches, axis=0).astype("float32")
        self.np.save(vector_path, vectors, allow_pickle=False)
        summary = dict(stage="embedding", kind=kind, inputs=len(rows), truncated_inputs=total_truncated,
                       max_input_tokens=maximum, max_length=self.args.max_length)
        metadata = dict(key=key, binding=binding, ordered_unit_text_sha256=text_sha, npy_sha256=sha_file(vector_path),
                        shape=list(vectors.shape), token_summary=summary, token_audit=token_audit)
        write_json(meta_path, metadata)
        self.log["truncation"].append(summary | dict(corpus=corpus, cache_hit=False))
        self.log["cache_events"].append(dict(corpus=corpus, kind=kind, key=key, hit=False,
                                             seconds=time.perf_counter()-started))
        write_token_audit(self.token_handle, token_audit, corpus=corpus, cache_hit=False, cache_key=key)
        return vectors

    def rerank(self, query, candidates, unit_map, corpus, query_id):
        scores = []
        truncated_count, max_tokens = 0, 0
        for start in range(0, len(candidates), self.args.batch_size):
            rows = candidates[start:start + self.args.batch_size]
            docs = [unit_map[row["unit_id"]]["text"] for row in rows]
            queries = [query] * len(docs)
            lengths = [len(ids) for ids in self.rerank_tokenizer(queries, docs, truncation=False, padding=False)["input_ids"]]
            tokens = self.rerank_tokenizer(queries, docs, padding=True, truncation=True, max_length=self.args.max_length, return_tensors="pt")
            used = tokens["attention_mask"].sum(dim=1).tolist()
            for row, length, actual in zip(rows, lengths, used):
                truncated = length > self.args.max_length
                truncated_count += truncated
                max_tokens = max(max_tokens, length)
                self.token_handle.write(json.dumps(dict(stage="rerank", corpus=corpus, query_id=query_id,
                                                       unit_id=row["unit_id"], input_tokens=length, used_tokens=actual,
                                                       truncated=truncated, max_length=self.args.max_length)) + "\n")
            tokens = {key: value.to(self.args.device) for key, value in tokens.items()}
            with self.torch.inference_mode():
                logits = self.reranker(**tokens).logits
            if logits.ndim != 2 or logits.shape[1] != 1:
                raise ValueError(f"Expected single reranker logit, got {tuple(logits.shape)}")
            scores.extend(logits[:, 0].float().cpu().tolist())
        self.log["truncation"].append(dict(stage="rerank", corpus=corpus, query_id=query_id, inputs=len(candidates),
                                            truncated_inputs=truncated_count, max_input_tokens=max_tokens, max_length=self.args.max_length))
        self.token_handle.flush()
        return ranked_rows(sorted([dict(unit_id=row["unit_id"], score=float(score)) for row, score in zip(candidates, scores)],
                                  key=lambda row: (-row["score"], row["unit_id"])))


def run(args):
    started = time.perf_counter()
    runner_sha = RUNNER_SHA256
    check_runner_hash(runner_sha)
    if args.output.exists():
        raise FileExistsError(f"Output already exists: {args.output}")
    if not 1 <= args.max_length <= 512:
        raise ValueError("max-length must be between 1 and 512")
    manifest = read_json(args.prepared / "manifest.json")
    if manifest.get("status") != "complete" or manifest["source_files"] != args.expected_files:
        raise ValueError("Prepared corpus is incomplete or has wrong file count")
    queries = list(read_jsonl(args.queries))
    if not queries or len({row["query_id"] for row in queries}) != len(queries):
        raise ValueError("Query IDs must be unique and query input nonempty")
    for row in queries:
        if not isinstance(row.get("text"), str) or not row["text"].strip():
            raise ValueError(f"Empty query: {row.get('query_id')}")
    sparse_path = args.project_src / "retrieval/sparse.py"
    tokenization_path = args.project_src / "retrieval/tokenization.py"
    if not sparse_path.is_file() or not tokenization_path.is_file():
        raise FileNotFoundError(f"Read-only desktop BM25 source missing: {args.project_src}")
    sys.path.insert(0, str(args.project_src.resolve()))
    from retrieval.sparse import RetrievalDocument, SparseRetrievalIndex
    models = None
    enabled = {corpus: args.arms or (["bm25", "dense", "rrf", "rrf_rerank"] if corpus == "structured" else ["bm25", "rrf_rerank"]) for corpus in args.corpora}
    if any(arm != "bm25" for arms in enabled.values() for arm in arms):
        models = LocalModels(args)
        query_vectors = models.encode(queries, "query", "shared")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Refuse overwrite: partial failures remain visibly separate from completed result files.
    partial = Path(str(args.output) + ".partial")
    completed_rows = 0
    log = dict(status="running", parameters={key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
               queries_sha256=sha_file(args.queries), runner_sha256=runner_sha,
               manifest_sha256=sha_file(args.prepared / "manifest.json"), bm25_source_sha256=sha_file(sparse_path),
               tokenizer_source_sha256=sha_file(tokenization_path), versions={"python":sys.version},
               bm25=dict(k1=1.5, b=0.75, weight=1.0), rrf=dict(k=60, ranks_start=1, equal_weights=True,
                                                                        route_top_k=100, union_max=200, rerank_top_k=100))
    log_path = Path(str(args.output) + ".run.json")
    try:
        with partial.open("w", encoding="utf-8") as output:
            for corpus, arms in enabled.items():
                corpus_path = args.prepared / f"{corpus}.jsonl"
                if sha_file(corpus_path) != manifest["corpora"][corpus]["sha256"]:
                    raise ValueError(f"Prepared corpus hash mismatch: {corpus}")
                units = list(read_jsonl(corpus_path))
                unit_map = {unit["unit_id"]: unit for unit in units}
                if len(unit_map) != len(units):
                    raise ValueError(f"Duplicate units: {corpus}")
                if ordered_text_sha(units) != manifest["corpora"][corpus]["ordered_unit_text_sha256"]:
                    raise ValueError(f"Prepared ordered text hash mismatch: {corpus}")
                index_start = time.perf_counter()
                sparse = SparseRetrievalIndex([RetrievalDocument(unit_id=unit["unit_id"], case_ids=(unit["case_id"],),
                                                                 text=unit["text"], source=corpus, weight=1.0) for unit in units])
                index_seconds = time.perf_counter() - index_start
                if models:
                    doc_vectors = models.encode(units, "document", corpus)
                print(json.dumps(dict(event="index_ready", corpus=corpus, units=len(units), bm25_index_seconds=index_seconds)), flush=True)
                for qi, query in enumerate(queries):
                    query_started = time.perf_counter()
                    t = time.perf_counter()
                    bm25 = [dict(unit_id=hit.document.unit_id, score=float(hit.score), rank=hit.rank) for hit in sparse.search(query["text"], top_k=100)]
                    bm25_seconds = time.perf_counter() - t
                    stages = {"bm25": bm25}
                    dense_seconds, rrf_seconds, rerank_seconds = 0.0, 0.0, 0.0
                    if any(arm != "bm25" for arm in arms):
                        t = time.perf_counter()
                        scores = doc_vectors @ query_vectors[qi]
                        order = models.np.lexsort((models.np.arange(len(scores)), -scores))[:100]
                        dense = ranked_rows([dict(unit_id=units[int(i)]["unit_id"], score=float(scores[i])) for i in order])
                        dense_seconds = time.perf_counter() - t
                        stages["dense"] = dense
                        t = time.perf_counter()
                        union = rrf([bm25, dense], k=60, top_k=200)
                        fused = union[:100]
                        rrf_seconds = time.perf_counter() - t
                        stages.update(rrf_union=union, rrf_top100=fused)
                    if "rrf_rerank" in arms:
                        t = time.perf_counter()
                        reranked = models.rerank(query["text"], fused, unit_map, corpus, query["query_id"])
                        rerank_seconds = time.perf_counter() - t
                        stages["rerank"] = reranked
                    for arm in arms:
                        final = {"bm25": bm25}.get(arm)
                        if arm == "dense":
                            final = dense
                        elif arm == "rrf":
                            final = fused
                        elif arm == "rrf_rerank":
                            final = reranked
                        cases, files = aggregate(final, unit_map)
                        arm_stage_names = ["bm25"] if arm == "bm25" else (["dense"] if arm == "dense" else (["bm25", "dense", "rrf_union", "rrf_top100"] + (["rerank"] if arm == "rrf_rerank" else [])))
                        record = dict(corpus=corpus, arm=arm, query_id=query["query_id"], text=query["text"], files=files, cases=cases,
                                      stages={key: stages[key] for key in arm_stage_names},
                                      timing=dict(bm25_seconds=bm25_seconds, dense_seconds=dense_seconds, rrf_seconds=rrf_seconds,
                                                  rerank_seconds=rerank_seconds if arm == "rrf_rerank" else 0,
                                                  shared_query_seconds=time.perf_counter()-query_started, bm25_index_seconds=index_seconds))
                        output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                        completed_rows += 1
                    output.flush()
                    print(json.dumps(dict(event="query_complete", corpus=corpus, query_id=query["query_id"], arms=arms,
                                          seconds=time.perf_counter()-query_started)), flush=True)
        expected = len(queries) * sum(len(arms) for arms in enabled.values())
        if completed_rows != expected:
            raise RuntimeError(f"Incomplete run: {completed_rows}/{expected}")
        check_runner_hash(runner_sha)
        log.update(status="complete", result_rows=completed_rows, elapsed_seconds=time.perf_counter()-started,
                   output_sha256=sha_file(partial))
        partial.replace(args.output)
    except BaseException as exc:
        log.update(status="failed", error=f"{type(exc).__name__}: {exc}", completed_rows=completed_rows,
                   elapsed_seconds=time.perf_counter()-started)
        raise
    finally:
        if models:
            models.token_handle.close()
            log["models"] = models.log
        write_json(log_path, log)
    print(json.dumps(dict(event="run_complete", rows=completed_rows, seconds=log["elapsed_seconds"], output=str(args.output))), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--authored", type=Path, default=WORKSPACE / "outputs/FinRisk_剩余全量运行_v2_20261011/authored")
    parser.add_argument("--tasks", type=Path, default=WORKSPACE / "outputs/FinRisk_剩余全量准备_20261011/tasks")
    parser.add_argument("--prepared", type=Path, default=HERE / "prepared")
    parser.add_argument("--queries", type=Path, default=HERE / "queries.jsonl")
    parser.add_argument("--output", type=Path, default=HERE / "results.jsonl")
    parser.add_argument("--cache", type=Path, default=HERE / "vector_cache")
    parser.add_argument("--project-src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--embedding-model", type=Path, default=DEFAULT_EMBEDDING)
    parser.add_argument("--reranker-model", type=Path, default=DEFAULT_RERANKER)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--precision", choices=("float32", "float16"), default="float32")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--chunk-chars", type=int, default=300)
    parser.add_argument("--overlap-chars", type=int, default=40)
    parser.add_argument("--expected-files", type=int, default=8509)
    parser.add_argument("--corpora", nargs="+", choices=("structured", "raw"), default=["structured", "raw"])
    parser.add_argument("--arms", nargs="+", choices=("bm25", "dense", "rrf", "rrf_rerank"), default=None)
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("batch-size must be positive")
    started = time.time()
    try:
        (prepare if args.prepare else run)(args)
    except BaseException as exc:
        if args.run:
            log_path = Path(str(args.output) + ".run.json")
            if args.output.exists():
                log_path = Path(str(args.output) + ".failure.json")
            if not log_path.exists() or log_path.stat().st_mtime < started:
                write_json(log_path, dict(status="failed", error=f"{type(exc).__name__}: {exc}",
                                          parameters={key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
                                          runner_sha256=RUNNER_SHA256, runtime_initialized=False))
        print(json.dumps(dict(event="failed", mode="prepare" if args.prepare else "run", error=f"{type(exc).__name__}: {exc}")), file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    main()
