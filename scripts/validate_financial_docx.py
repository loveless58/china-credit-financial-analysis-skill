#!/usr/bin/env python3
"""Validate a DOCX financial-analysis replacement structurally."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


def para_shade(paragraph) -> str | None:
    shd = paragraph._p.get_or_add_pPr().find(qn("w:shd"))
    return shd.get(qn("w:fill")) if shd is not None else None


def cell_shade(cell) -> str | None:
    shd = cell._tc.get_or_add_tcPr().find(qn("w:shd"))
    return shd.get(qn("w:fill")) if shd is not None else None


def east_asia_font(run) -> str | None:
    r_fonts = run._element.get_or_add_rPr().rFonts
    return r_fonts.get(qn("w:eastAsia")) if r_fonts is not None else None


def table_text(table) -> str:
    return "\n".join(cell.text for row in table.rows for cell in row.cells)


def find_section(paragraphs: list[str], start_anchor: str, end_anchor: str) -> tuple[int, int]:
    start = next((i for i, text in enumerate(paragraphs) if start_anchor in text), None)
    if start is None:
        raise ValueError(f"section start not found: {start_anchor}")
    end = next((i for i, text in enumerate(paragraphs[start + 1 :], start + 1) if end_anchor in text), None)
    if end is None:
        raise ValueError(f"section end not found after start: {end_anchor}")
    return start, end


def first_run_in_table(table):
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                if paragraph.runs:
                    return paragraph.runs[0]
    return None


def dominant_table_font(table) -> str | None:
    values = []
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    font = east_asia_font(run)
                    if font:
                        values.append(font)
    return Counter(values).most_common(1)[0][0] if values else None


def dominant_table_size(table) -> float | None:
    values = []
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    if run.font.size is not None:
                        values.append(run.font.size.pt)
    return Counter(values).most_common(1)[0][0] if values else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx", type=Path, required=True)
    parser.add_argument("--section-start", default="财务分析")
    parser.add_argument("--section-end", default="行业分析")
    parser.add_argument("--target-unit", default="万元")
    parser.add_argument("--forbidden-unit", action="append", default=["亿元"])
    parser.add_argument("--expected-shading", default="FFF2CC")
    parser.add_argument("--body-font")
    parser.add_argument("--body-size", type=float)
    parser.add_argument("--table-font")
    parser.add_argument("--table-size", type=float)
    parser.add_argument("--min-asset-table-rows", type=int, default=20)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    doc = Document(str(args.docx))
    para_texts = [paragraph.text for paragraph in doc.paragraphs]
    start, end = find_section(para_texts, args.section_start, args.section_end)
    section_text = "\n".join(para_texts[start:end])
    financial_tables = [table for table in doc.tables if any(anchor in table_text(table) for anchor in ("资产负债简表", "资产总计", "财务指标"))]
    asset_tables = [table for table in financial_tables if "资产负债简表" in table_text(table) or "资产总计" in table_text(table)]
    indicator_tables = [table for table in financial_tables if "财务指标" in table_text(table)]

    body_run = next((run for paragraph in doc.paragraphs[start:end] for run in paragraph.runs if run.text.strip()), None)
    table_run = first_run_in_table(asset_tables[0]) if asset_tables else None
    table_font = dominant_table_font(asset_tables[0]) if asset_tables else None
    table_size = dominant_table_size(asset_tables[0]) if asset_tables else None

    checks: dict[str, object] = {
        "docx_exists": args.docx.exists(),
        "financial_section_found": start < end,
        "target_unit_present": args.target_unit in section_text or any(args.target_unit in table_text(t) for t in financial_tables),
        "forbidden_unit_absent_in_section": not any(unit in section_text for unit in args.forbidden_unit),
        "asset_liability_table_found": bool(asset_tables),
        "asset_liability_table_rows": len(asset_tables[0].rows) if asset_tables else 0,
        "asset_liability_table_cols": len(asset_tables[0].columns) if asset_tables else 0,
        "asset_liability_table_not_too_simple": bool(asset_tables) and len(asset_tables[0].rows) >= args.min_asset_table_rows,
        "indicator_table_found": bool(indicator_tables),
        "codex_marker_absent": "Codex" not in section_text,
        "section_shaded_paragraphs": sum(1 for paragraph in doc.paragraphs[start:end] if para_shade(paragraph) == args.expected_shading),
        "asset_table_first_cell_shading": cell_shade(asset_tables[0].cell(0, 0)) if asset_tables else None,
        "body_font_sample": east_asia_font(body_run) if body_run else None,
        "body_size_sample": body_run.font.size.pt if body_run is not None and body_run.font.size is not None else None,
        "table_font_sample": table_font or (east_asia_font(table_run) if table_run else None),
        "table_size_sample": table_size or (table_run.font.size.pt if table_run is not None and table_run.font.size is not None else None),
    }
    if args.body_font:
        checks["body_font_matches"] = checks["body_font_sample"] == args.body_font
    if args.body_size:
        checks["body_size_matches"] = checks["body_size_sample"] == args.body_size
    if args.table_font:
        checks["table_font_matches"] = checks["table_font_sample"] == args.table_font
    if args.table_size:
        checks["table_size_matches"] = checks["table_size_sample"] == args.table_size

    required = [
        "docx_exists",
        "financial_section_found",
        "target_unit_present",
        "forbidden_unit_absent_in_section",
        "asset_liability_table_found",
        "asset_liability_table_not_too_simple",
        "codex_marker_absent",
    ]
    failed = [key for key in required if not checks.get(key)]
    result = {"checks": checks, "failed": failed}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
