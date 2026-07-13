#!/usr/bin/env python3
"""End-to-end self-test for the safe financial DOCX update workflow."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt


ROOT = Path(__file__).resolve().parent.parent
UPDATER = ROOT / "scripts" / "update_financial_docx.py"
SCHEMA = ROOT / "schemas" / "financial_analysis_bundle.schema.json"
SECTION_START = "（五）、财务分析"
ANALYSIS_ANCHOR = "合并财务情况分析："
SECTION_END = "（六）、行业分析"
OUTPUT_FILENAME = "某测试公司_财务分析更新稿.docx"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_borders(table) -> None:
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "8")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "00AA00")
        borders.append(element)
    table._tbl.tblPr.append(borders)


def east_asia_font(run) -> str | None:
    r_fonts = run._element.get_or_add_rPr().rFonts
    return r_fonts.get(qn("w:eastAsia")) if r_fonts is not None else None


def cell_fill(cell) -> str | None:
    shd = cell._tc.get_or_add_tcPr().find(qn("w:shd"))
    return shd.get(qn("w:fill")) if shd is not None else None


def paragraph_fill(paragraph) -> str | None:
    shd = paragraph._p.get_or_add_pPr().find(qn("w:shd"))
    return shd.get(qn("w:fill")) if shd is not None else None


def table_rows() -> list[list[str]]:
    rows = [
        ["资产负债简表（合并口径，单位：万元）", "", ""],
        ["项目", "2024", "2025"],
        ["资产总计", "100.00", "120.00"],
    ]
    rows.extend([["待核验项目", "", ""] for _ in range(17)])
    return rows


def make_source_docx(path: Path) -> None:
    document = Document()
    document.add_paragraph(SECTION_START)
    table = document.add_table(rows=20, cols=3)
    table.style = "Table Grid"
    set_borders(table)
    source_rows = table_rows()
    source_rows[2][2] = "110.00"
    for row_index, row in enumerate(source_rows):
        for col_index, text in enumerate(row):
            cell = table.cell(row_index, col_index)
            set_cell_shading(cell, "D9EAD3")
            run = cell.paragraphs[0].add_run(text)
            run.font.name = "仿宋"
            run.font.size = Pt(11)
            run._element.get_or_add_rPr().get_or_add_rFonts().set(
                qn("w:eastAsia"), "仿宋"
            )
    document.add_paragraph(ANALYSIS_ANCHOR)
    document.add_paragraph("旧财务分析内容。")
    document.add_paragraph(SECTION_END)
    document.save(path)


def valid_bundle() -> dict:
    return {
        "schema_version": "1.0",
        "company_name": "某测试公司",
        "reporting_basis": "合并口径",
        "currency": "CNY",
        "unit": "万元",
        "periods": ["2024", "2025"],
        "sources": {
            "annual_2025": {
                "name": "某测试公司2025年审计报告",
                "type": "audit_report",
                "file": "source/annual_2025.pdf",
            }
        },
        "financial_tables": {
            "asset_liability": {
                "rows": [
                    {
                        "metric": "total_assets",
                        "label": "资产总计",
                        "values": {
                            "2024": {
                                "value": "100.00",
                                "status": "verified",
                                "source_refs": ["annual_2025"],
                            },
                            "2025": {
                                "value": "120.00",
                                "status": "verified",
                                "source_refs": ["annual_2025"],
                            },
                        },
                    }
                ]
            }
        },
        "ratios": {},
        "risk_points": [
            {
                "category": "偿债能力",
                "statement": "需关注债务期限结构与经营现金流匹配情况。",
                "evidence_refs": ["annual_2025"],
            }
        ],
        "pending_verification": [
            {"issue": "核验受限资产明细。", "status": "source_missing"}
        ],
        "docx_write_plan": {
            "mode": "replace",
            "section_start": SECTION_START,
            "analysis_anchor": ANALYSIS_ANCHOR,
            "section_end": SECTION_END,
            "analysis_markdown": "总资产为120.00万元。",
            "table_rows": {"asset_liability": table_rows()},
            "target_unit": "万元",
            "require_backup": True,
            "preserve_asset_liability_table": True,
            "change_shading": "FFF2CC",
            "output_filename": OUTPUT_FILENAME,
        },
    }


def run_updater(source: Path, bundle: dict, out_dir: Path) -> subprocess.CompletedProcess[str]:
    bundle_path = out_dir.parent / f"{out_dir.name}.bundle.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(UPDATER),
            str(source),
            str(bundle_path),
            "--schema",
            str(SCHEMA),
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def assert_replace_success(source: Path, source_hash_before: str, tmp_path: Path) -> None:
    out_dir = tmp_path / "replace-output"
    result = run_updater(source, valid_bundle(), out_dir)
    assert result.returncode == 0, result.stderr or result.stdout
    summary = json.loads(result.stdout)

    updated_docx = out_dir / OUTPUT_FILENAME
    assert Path(summary["output"]) == updated_docx.resolve()
    assert sha256(source) == source_hash_before
    assert len(list(out_dir.glob("*.backup-*.docx"))) == 1
    assert updated_docx.exists()

    output_document = Document(str(updated_docx))
    output_text = "\n".join(paragraph.text for paragraph in output_document.paragraphs)
    assert "旧财务分析内容" not in output_text
    assert "总资产为120.00万元" in output_text
    output_table = output_document.tables[0]
    assert output_table.cell(2, 2).text == "120.00"
    output_run = output_table.cell(2, 2).paragraphs[0].runs[0]
    assert east_asia_font(output_run) == "仿宋"
    assert output_run.font.size.pt == 11
    assert cell_fill(output_table.cell(2, 2)) == "D9EAD3"
    assert "00AA00" in output_table._tbl.tblPr.xml
    assert json.loads((out_dir / "number_audit.json").read_text(encoding="utf-8"))["findings"] == []
    assert json.loads((out_dir / "validation_result.json").read_text(encoding="utf-8"))["failed"] == []
    assert (out_dir / "change_log.md").exists()
    assert (out_dir / "待核验清单.md").exists()


def assert_number_audit_failure(source: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "audit-failure-output"
    bundle = valid_bundle()
    bundle["docx_write_plan"]["analysis_markdown"] = "总资产为999.00万元。"
    result = run_updater(source, bundle, out_dir)
    assert result.returncode != 0
    audit = json.loads((out_dir / "number_audit.json").read_text(encoding="utf-8"))
    assert [finding["number"] for finding in audit["findings"]] == ["999.00"]
    assert len(list(out_dir.glob("*.backup-*.docx"))) == 1
    assert not (out_dir / OUTPUT_FILENAME).exists()


def assert_insert_success(source: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "insert-output"
    bundle = copy.deepcopy(valid_bundle())
    bundle["docx_write_plan"]["mode"] = "insert"
    result = run_updater(source, bundle, out_dir)
    assert result.returncode == 0, result.stderr or result.stdout

    output_document = Document(str(out_dir / OUTPUT_FILENAME))
    paragraphs = output_document.paragraphs
    texts = [paragraph.text for paragraph in paragraphs]
    anchor_index = texts.index(ANALYSIS_ANCHOR)
    assert texts[anchor_index + 1] == "【Codex财务分析更新建议】"
    assert texts[anchor_index + 2] == "总资产为120.00万元。"
    assert "旧财务分析内容。" in texts
    assert paragraph_fill(paragraphs[anchor_index + 1]) == "FFF2CC"
    assert paragraph_fill(paragraphs[anchor_index + 2]) == "FFF2CC"
    validation = json.loads(
        (out_dir / "validation_result.json").read_text(encoding="utf-8")
    )
    assert validation["failed"] == []
    assert validation["checks"]["codex_marker_absent"] is False


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "source.docx"
        make_source_docx(source)
        source_hash_before = sha256(source)

        assert_replace_success(source, source_hash_before, tmp_path)
        assert_number_audit_failure(source, tmp_path)
        assert_insert_success(source, tmp_path)
        assert sha256(source) == source_hash_before

    print("financial DOCX update self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
