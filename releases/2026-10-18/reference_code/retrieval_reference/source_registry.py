"""Acquire public official documents; never reads credentials or executes text."""
import hashlib
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_法规库V1_20261017"
PLAN = ROOT / "outputs/FinRisk_法规库实施规划_20261017/法规来源清单.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path, value, jsonl=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        if jsonl:
            for row in value:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        else:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def validate_url(url, allowed_hosts):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts or parsed.username or parsed.password:
        raise ValueError("URL is not a registered official HTTPS source")
    return url


def extract_html(raw, encoding):
    from lxml import html
    document = html.fromstring(raw.decode(encoding, errors="strict"))
    for node in document.xpath("//script|//style|//nav|//header|//footer|//form|//noscript"):
        node.drop_tree()
    candidates = document.xpath("//article|//div[contains(concat(' ',normalize-space(@class),' '),' TRS_Editor ')]")
    root = candidates[0] if candidates else document
    from lxml import etree
    parts = []
    blocks = {"p", "div", "article", "section", "br", "li", "tr", "h1", "h2", "h3", "h4"}
    for event, node in etree.iterwalk(root, events=("start", "end")):
        tag = str(node.tag).lower()
        if event == "start":
            if tag in blocks:
                parts.append("\n")
            if node.text:
                parts.append(node.text)
        else:
            if tag in blocks:
                parts.append("\n")
            if node.tail:
                parts.append(node.tail)
    return "\n".join(line.strip() for line in "".join(parts).splitlines() if line.strip())


def validate_text(text, title):
    if len(text) < 500 or title not in text or not re.search(r"第[一二三四五六七八九十百0-9]+条|（一）|\(一\)", text):
        raise ValueError("not a complete recognizable regulation body")
    if text.count("\ufffd") or not re.search("[\u4e00-\u9fff]", text):
        raise ValueError("bad document decoding")
    return True


def extract_pdf(raw):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(raw))
    pages, pieces, offset = [], [], 0
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        pages.append(dict(page=number, start=offset, end=offset + len(text)))
        pieces.append(text)
        offset += len(text) + 1
    return "\n".join(pieces), pages


def acquire(specification, allowed_hosts):
    sid = specification["source_id"]
    marker = OUT / "collection" / (sid + ".json")
    if marker.exists():
        return read(marker)
    urls = list(dict.fromkeys(specification[k] for k in
                ("verified_text_url", "official_url", "alternative_official_url") if specification.get(k)))
    attempts = []
    for ordinal, url in enumerate(urls, 1):
        try:
            validate_url(url, allowed_hosts)
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/pdf"})
            with urllib.request.urlopen(request, timeout=20) as response:
                validate_url(response.url, allowed_hosts)
                raw = response.read(20_000_001)
                if len(raw) > 20_000_000:
                    raise ValueError("official document exceeds 20 MB limit")
                content_type = response.headers.get("Content-Type", "")
                final_url = response.url
            pdf = raw.startswith(b"%PDF")
            raw_path = OUT / "sources/raw" / f"{sid}_{ordinal}.{'pdf' if pdf else 'html'}"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(raw)
            if pdf:
                text, pages = extract_pdf(raw)
                encoding = None
            else:
                charset = re.search(rb"charset\s*=\s*['\"]?([a-zA-Z0-9_-]+)", raw[:10000])
                encoding = charset.group(1).decode() if charset else "utf-8"
                text, pages = extract_html(raw, encoding), []
            validate_text(text, specification["title"])
            text_path = OUT / "sources/extracted" / (sid + ".txt")
            text_path.parent.mkdir(parents=True, exist_ok=True)
            text_path.write_text(text, encoding="utf-8")
            record = dict(**specification, collection_status="collected", retrieval_url=url,
                          final_url=final_url, retrieved_at=datetime.now(timezone.utc).isoformat(),
                          raw_path=raw_path.relative_to(OUT).as_posix(), raw_sha256=sha(raw),
                          text_path=text_path.relative_to(OUT).as_posix(), text_sha256=sha(text.encode()),
                          text_characters=len(text), content_type=content_type, encoding=encoding,
                          page_spans=pages, attempts=attempts,
                          extraction_policy="lxml block text; script/style/nav removed; line-edge whitespace stripped" if not pdf else "pypdf text extraction, page spans preserved",
                          legal_status="pending_review", review_status="not_yet_reviewed")
            save(marker, record)
            return record
        except (urllib.error.URLError, TimeoutError, ValueError, UnicodeError, OSError) as error:
            attempts.append(dict(url=url, error=type(error).__name__, message=str(error)[:400]))
    record = dict(**specification, collection_status="pending", attempts=attempts,
                  legal_status="pending_review", review_status="not_yet_reviewed")
    save(marker, record)
    return record


def main():
    from concurrent.futures import ThreadPoolExecutor
    specification = read(PLAN)["sources"]
    core = [s for s in specification if s["selected_articles"]]
    hosts = {urllib.parse.urlsplit(s[k]).hostname for s in specification for k in
             ("official_url", "verified_text_url", "alternative_official_url") if s.get(k)}
    with ThreadPoolExecutor(max_workers=4) as executor:
        result = list(executor.map(lambda item: acquire(item, hosts), core))
    destination = OUT / "collection_summary.json"
    save(destination, dict(status="collection_complete" if all(r["collection_status"] == "collected" for r in result) else "partial",
                           collected=sum(r["collection_status"] == "collected" for r in result), records=result))
    print(json.dumps({"collected": sum(r["collection_status"] == "collected" for r in result),
                      "sources": [{"id": r["source_id"], "status": r["collection_status"],
                                   "characters": r.get("text_characters"), "attempts": len(r["attempts"])} for r in result]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
