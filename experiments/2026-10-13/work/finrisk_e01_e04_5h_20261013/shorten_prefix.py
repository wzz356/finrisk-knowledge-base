"""One pre-run source-grounded correction for an oversized redundant prefix."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/FinRisk_E01-E04五小时实验_20261013"
TARGET = OUT / "scope_units.jsonl"


def main():
    original = TARGET.read_bytes()
    before = hashlib.sha256(original).hexdigest()
    if before != "c728c6424d91416dd4ae917f11ba2a3c0dc222738c6a0910898c8aa80ac561c6":
        raise ValueError("Unexpected source candidate version")
    backup = OUT / "scope_units_initial.jsonl"
    if backup.exists():
        raise FileExistsError(backup)
    rows = [json.loads(s) for s in original.decode("utf-8").splitlines() if s.strip()]
    row = next(r for r in rows if r["file_id"] == "F001345")
    first = row["segments"][0]
    quote = "平安产险"
    offset = first["text"].index(quote)
    row["prefix_claims"] = [{"label": "片段主体", "quote": quote,
                            "span": {"start": first["span"]["start"] + offset, "end": first["span"]["start"] + offset + len(quote)},
                            "link_reason": "源内当事人名称定义的机构简称，当前倒签单事实同段明示该简称；仅身份，行为原话已在scope段保留。"}]
    row["prefix_text"] = "片段主体：" + quote
    row["prefix_chars"] = len(row["prefix_text"])
    row["notes"].append("Root运行前tokenizer检查发现重复长背景超512；仅缩短为源内机构简称，scope及其全部事实/责任/条件未改。须另行独立复核并绑定新SHA。")
    backup.write_bytes(original)
    TARGET.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    after = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    notes = OUT / "scope_notes.md"
    with notes.open("a", encoding="utf-8") as handle:
        handle.write("\n## 运行前最小修正\n\nRoot实际阅读F001345全文后，将154字符的重复背景缩为9字符的源内身份“片段主体：平安产险”。S1范围及原文段落未改。原因是实际tokenizer预检C2为640 tokens，不能静默截断。原候选保存在scope_units_initial.jsonl；当前scope_units SHA为`" + after + "`，原作者初始SHA保留作历史。最终model_review须重新绑定当前文件。\n")
    print(json.dumps({"before": before, "after": after, "new_prefix_chars": len(row["prefix_text"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
