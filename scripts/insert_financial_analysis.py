#!/usr/bin/env python3
"""Insert or replace a financial-analysis update in a DOCX file."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from docx import Document
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("python-docx is required: pip install python-docx") from exc

SECTION_KEYWORDS = ("财务分析", "财务状况", "资产负债", "盈利能力", "现金流")


def find_anchor(document: Document) -> int | None:
    for idx, paragraph in enumerate(document.paragraphs):
        text = paragraph.text.strip()
        if any(keyword in text for keyword in SECTION_KEYWORDS):
            return idx
    return None


def add_paragraph_after(paragraph, text: str):
    from docx.oxml import OxmlElement
    from docx.text.paragraph import Paragraph

    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    inserted = Paragraph(new_p, paragraph._parent)
    inserted.add_run(text)
    return inserted


def insert_block(document: Document, anchor_idx: int | None, update_text: str) -> str:
    marker = "【Codex财务分析更新建议】"
    pending_marker = "【待核验事项】"
    lines = [marker, *update_text.splitlines()]
    if pending_marker not in update_text:
        lines.extend(["", pending_marker, "详见待核验清单。"])

    if anchor_idx is None:
        for line in lines:
            document.add_paragraph(line)
        return "document-end"

    anchor = document.paragraphs[anchor_idx]
    current = anchor
    for line in lines:
        current = add_paragraph_after(current, line)
    return f"after paragraph {anchor_idx + 1}: {anchor.text[:80]}"


def replace_section(document: Document, anchor_idx: int | None, update_text: str) -> str:
    if anchor_idx is None:
        raise SystemExit("financial-analysis section not found; replacement is blocked")
    paragraphs = document.paragraphs
    start = anchor_idx
    end = len(paragraphs)
    for idx in range(anchor_idx + 1, len(paragraphs)):
        style_name = getattr(paragraphs[idx].style, "name", "")
        text = paragraphs[idx].text.strip()
        if idx > start + 1 and (style_name.startswith("Heading") or text.startswith(("一、", "二、", "三、", "四、", "五、", "六、"))):
            end = idx
            break

    for idx in range(end - 1, start, -1):
        element = paragraphs[idx]._element
        element.getparent().remove(element)

    paragraphs[start].text = ""
    current = paragraphs[start]
    for line in update_text.splitlines():
        if not current.text:
            current.add_run(line)
        else:
            current = add_paragraph_after(current, line)
    return f"replaced paragraphs {start + 1}-{end}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("update_markdown", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("insert", "replace"), default="insert")
    parser.add_argument("--confirm-replace", action="store_true")
    args = parser.parse_args()

    if args.docx.suffix.lower() != ".docx":
        raise SystemExit("only .docx files are supported")
    if args.out.exists() and args.out.resolve() == args.docx.resolve():
        raise SystemExit("refusing to overwrite original path; write to a new file or back up explicitly")
    if args.mode == "replace" and not args.confirm_replace:
        raise SystemExit("replacement requires --confirm-replace")

    document = Document(str(args.docx))
    update_text = args.update_markdown.read_text(encoding="utf-8-sig").strip()
    anchor_idx = find_anchor(document)

    if args.mode == "insert":
        location = insert_block(document, anchor_idx, update_text)
    else:
        location = replace_section(document, anchor_idx, update_text)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(args.out))
    print(location)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
