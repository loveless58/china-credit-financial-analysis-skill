#!/usr/bin/env python3
"""Safely update a credit-review financial-analysis DOCX from a bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from docx import Document

if __package__:
    from .audit_report_numbers import audit_text
    from .backup_docx import backup_path, create_backup
    from .export_change_log import write_change_log
    from .insert_financial_analysis import (
        insert_analysis_body,
        replace_analysis_body,
    )
    from .preserve_financial_table_format import fill_table, find_table
    from .validate_financial_analysis_bundle import validate_bundle
    from .validate_financial_docx import validate_financial_docx
else:
    from audit_report_numbers import audit_text
    from backup_docx import backup_path, create_backup
    from export_change_log import write_change_log
    from insert_financial_analysis import insert_analysis_body, replace_analysis_body
    from preserve_financial_table_format import fill_table, find_table
    from validate_financial_analysis_bundle import validate_bundle
    from validate_financial_docx import validate_financial_docx


SKILL_ROOT = Path(__file__).resolve().parent.parent


class UpdateBlocked(RuntimeError):
    """Raised before a writable DOCX can be safely produced."""

    def __init__(self, message: str, details: list[Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or []


class UpdateFailed(RuntimeError):
    """Raised when the produced DOCX fails structural validation."""

    def __init__(self, message: str, details: list[Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or []


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as file_handle:
        return json.load(file_handle)


def write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def reject_out_dir_inside_skill_repo(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    if resolved == SKILL_ROOT or SKILL_ROOT in resolved.parents:
        raise UpdateBlocked(
            "output directory must be outside the Skill repository",
            [str(resolved)],
        )


def write_pending_markdown(path: Path, pending: list[dict[str, Any]]) -> Path:
    lines = ["# 待核验清单", ""]
    if pending:
        lines.extend(
            f"- [{item['status']}] {item['issue']}" for item in pending
        )
    else:
        lines.append("- 无")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _safe_output_path(out_dir: Path, output_filename: str, source: Path) -> Path:
    filename = Path(output_filename)
    if filename.is_absolute() or filename.name != output_filename:
        raise UpdateBlocked("output_filename must be a DOCX basename", [output_filename])
    output = (out_dir / filename).resolve()
    if output == source.resolve():
        raise UpdateBlocked("refusing to overwrite original DOCX", [str(output)])
    return output


def update_financial_docx(
    source_docx: Path,
    bundle_path: Path,
    schema_path: Path,
    out_dir: Path,
) -> dict[str, str]:
    bundle = load_json(bundle_path)
    schema = load_json(schema_path)
    errors = validate_bundle(bundle, schema)
    if errors:
        raise UpdateBlocked("bundle validation failed", errors)

    reject_out_dir_inside_skill_repo(out_dir)
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    source_docx = source_docx.resolve()
    backup = create_backup(source_docx, backup_path(source_docx, out_dir))

    plan = bundle["docx_write_plan"]
    findings = audit_text(plan["analysis_markdown"], [bundle])
    table_text = "\n".join(
        str(cell)
        for rows in plan["table_rows"].values()
        for row in rows
        for cell in row
    )
    findings.extend(audit_text(table_text, [bundle]))
    number_audit = write_json(out_dir / "number_audit.json", {"findings": findings})
    if findings:
        raise UpdateBlocked("number audit failed", findings)

    output = _safe_output_path(out_dir, plan["output_filename"], source_docx)
    document = Document(str(source_docx))
    if "asset_liability" in plan["table_rows"]:
        _, table = find_table(document, ["资产负债简表", "资产总计"])
        fill_table(table, plan["table_rows"]["asset_liability"])

    if plan["mode"] == "replace":
        location = replace_analysis_body(
            document=document,
            section_start=plan["section_start"],
            analysis_anchor=plan["analysis_anchor"],
            section_end=plan["section_end"],
            analysis_markdown=plan["analysis_markdown"],
            shading=plan["change_shading"],
        )
    else:
        location = insert_analysis_body(
            document=document,
            section_start=plan["section_start"],
            analysis_anchor=plan["analysis_anchor"],
            section_end=plan["section_end"],
            analysis_markdown=plan["analysis_markdown"],
            shading=plan["change_shading"],
        )
    document.save(str(output))

    validation = validate_financial_docx(
        docx=output,
        section_start=plan["section_start"],
        section_end=plan["section_end"],
        target_unit=plan["target_unit"],
        forbidden_units=["亿元"] if plan["target_unit"] == "万元" else [],
        expected_shading=plan["change_shading"],
        body_font="仿宋_GB2312",
        body_size=14,
        min_asset_table_rows=20,
        allow_codex_marker=plan["mode"] == "insert",
    )
    validation_result = write_json(
        out_dir / "validation_result.json", validation
    )
    pending_path = write_pending_markdown(
        out_dir / "待核验清单.md", bundle["pending_verification"]
    )
    change_log = write_change_log(
        out=out_dir / "change_log.md",
        original=source_docx,
        workspace_copy=source_docx,
        backup=backup,
        output=output,
        mode=plan["mode"],
        location=location,
        sources=[source["name"] for source in bundle["sources"].values()],
        pending=[item["issue"] for item in bundle["pending_verification"]],
        table_preservation="original OOXML text-only update",
        validation_failed=list(validation["failed"]),
    )
    if validation["failed"]:
        raise UpdateFailed("DOCX validation failed", list(validation["failed"]))

    return {
        "backup": str(backup.resolve()),
        "output": str(output.resolve()),
        "number_audit": str(number_audit.resolve()),
        "validation_result": str(validation_result.resolve()),
        "change_log": str(change_log.resolve()),
        "pending_verification": str(pending_path.resolve()),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_docx", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = update_financial_docx(
            source_docx=args.source_docx,
            bundle_path=args.bundle,
            schema_path=args.schema,
            out_dir=args.out_dir,
        )
    except (UpdateBlocked, UpdateFailed) as error:
        print(
            json.dumps(
                {"error": str(error), "details": error.details},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
