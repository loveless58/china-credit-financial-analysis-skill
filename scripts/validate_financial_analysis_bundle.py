"""Validate the public financial_analysis_bundle 1.0 contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ALLOWED_STATUSES = {
    "verified",
    "calculated",
    "source_missing",
    "unit_missing",
    "conflict",
    "missing",
    "llm_generated_blocked",
}
BODY_STATUSES = {"verified", "calculated"}
FORBIDDEN_CONCLUSIONS = (
    "同意授信",
    "风险可控",
    "建议批复额度",
    "建议同意授信",
)


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_source_refs(
    source_refs: Any,
    sources: Any,
    prefix: str,
    require_non_empty: bool = False,
) -> list[str]:
    if not isinstance(source_refs, list):
        return [f"{prefix}.source_refs must be an array"]
    if require_non_empty and not source_refs:
        return [f"{prefix}.source_refs must be non-empty"]

    errors: list[str] = []
    for index, source_ref in enumerate(source_refs):
        if not is_non_empty_string(source_ref):
            errors.append(f"{prefix}.source_refs[{index}] must be a non-empty string")
        elif not isinstance(sources, dict) or source_ref not in sources:
            errors.append(f"{prefix}.source_refs[{index}] is not defined in sources")
    return errors


def validate_financial_tables(financial_tables: Any, sources: Any) -> list[str]:
    if not isinstance(financial_tables, dict):
        return ["financial_tables must be an object"]

    errors: list[str] = []
    for table_name, table in financial_tables.items():
        prefix = f"financial_tables.{table_name}"
        if not isinstance(table, dict):
            errors.append(f"{prefix} must be an object")
            continue
        rows = table.get("rows")
        if not isinstance(rows, list):
            errors.append(f"{prefix}.rows must be an array")
            continue
        for row_index, row in enumerate(rows):
            row_prefix = f"{prefix}.rows[{row_index}]"
            if not isinstance(row, dict):
                errors.append(f"{row_prefix} must be an object")
                continue
            values = row.get("values")
            if not isinstance(values, dict):
                errors.append(f"{row_prefix}.values must be an object")
                continue
            for period, item in values.items():
                item_prefix = f"{row_prefix}.values.{period}"
                if not isinstance(item, dict):
                    errors.append(f"{item_prefix} must be an object")
                    continue
                for field in ("value", "status", "source_refs"):
                    if field not in item:
                        errors.append(f"{item_prefix} missing field: {field}")
                status = item.get("status")
                if status not in ALLOWED_STATUSES:
                    errors.append(f"{item_prefix}.status must be an allowed status")
                source_refs = item.get("source_refs")
                errors.extend(
                    validate_source_refs(
                        source_refs,
                        sources,
                        item_prefix,
                        require_non_empty=status == "verified",
                    )
                )
    return errors


def validate_ratios(ratios: Any) -> list[str]:
    if not isinstance(ratios, dict):
        return ["ratios must be an object"]

    errors: list[str] = []
    for ratio_name, ratio in ratios.items():
        prefix = f"ratios.{ratio_name}"
        if not isinstance(ratio, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("formula", "value", "display", "status", "inputs"):
            if field not in ratio:
                errors.append(f"{prefix} missing field: {field}")
        if not is_non_empty_string(ratio.get("formula")):
            errors.append(f"{prefix}.formula must be a non-empty string")
        if ratio.get("value") in (None, ""):
            errors.append(f"{prefix}.value must be present")
        if not is_non_empty_string(ratio.get("display")):
            errors.append(f"{prefix}.display must be a non-empty string")
        if ratio.get("status") != "calculated":
            errors.append(f"{prefix}.status must equal calculated")

        inputs = ratio.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            errors.append(f"{prefix}.inputs must be a non-empty array")
            continue
        for input_index, input_item in enumerate(inputs):
            input_prefix = f"{prefix}.inputs[{input_index}]"
            if not isinstance(input_item, dict):
                errors.append(f"{input_prefix} must be an object")
                continue
            for field in ("metric", "period"):
                if not is_non_empty_string(input_item.get(field)):
                    errors.append(f"{input_prefix}.{field} must be a non-empty string")
    return errors


def contains_forbidden_conclusion(text: Any) -> bool:
    return is_non_empty_string(text) and any(
        phrase in text for phrase in FORBIDDEN_CONCLUSIONS
    )


def validate_risk_points(risk_points: Any, sources: Any) -> list[str]:
    if not isinstance(risk_points, list):
        return ["risk_points must be an array"]

    errors: list[str] = []
    for index, risk_point in enumerate(risk_points):
        prefix = f"risk_points[{index}]"
        if not isinstance(risk_point, dict):
            errors.append(f"{prefix} must be an object")
            continue
        statement = risk_point.get("statement")
        if not is_non_empty_string(statement):
            errors.append(f"{prefix}.statement must be a non-empty string")
        elif contains_forbidden_conclusion(statement):
            errors.append(f"{prefix}.statement contains a forbidden conclusion")
        errors.extend(
            validate_source_refs(
                risk_point.get("evidence_refs"), sources, prefix, require_non_empty=True
            )
        )
    return errors


def validate_pending(pending_verification: Any) -> list[str]:
    if not isinstance(pending_verification, list):
        return ["pending_verification must be an array"]

    errors: list[str] = []
    allowed_pending_statuses = ALLOWED_STATUSES - BODY_STATUSES
    for index, pending_item in enumerate(pending_verification):
        prefix = f"pending_verification[{index}]"
        if not isinstance(pending_item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not is_non_empty_string(pending_item.get("issue")):
            errors.append(f"{prefix}.issue must be a non-empty string")
        if pending_item.get("status") not in allowed_pending_statuses:
            errors.append(f"{prefix}.status must be a non-body status")
    return errors


def validate_docx_write_plan(docx_write_plan: Any, schema: dict[str, Any]) -> list[str]:
    if not isinstance(docx_write_plan, dict):
        return ["docx_write_plan must be an object"]

    try:
        plan_schema = schema["properties"]["docx_write_plan"]
        required = set(plan_schema["required"])
        properties = set(plan_schema["properties"])
    except (KeyError, TypeError):
        return ["schema is missing docx_write_plan contract"]

    errors = [
        f"docx_write_plan missing field: {name}"
        for name in sorted(required - docx_write_plan.keys())
    ]
    errors.extend(
        f"docx_write_plan unknown field: {name}"
        for name in sorted(docx_write_plan.keys() - properties)
    )

    if docx_write_plan.get("mode") not in {"insert", "replace"}:
        errors.append("docx_write_plan.mode must be insert or replace")
    for field in ("section_start", "analysis_anchor", "section_end", "analysis_markdown", "target_unit"):
        if not is_non_empty_string(docx_write_plan.get(field)):
            errors.append(f"docx_write_plan.{field} must be a non-empty string")
    if contains_forbidden_conclusion(docx_write_plan.get("analysis_markdown")):
        errors.append("docx_write_plan.analysis_markdown contains a forbidden conclusion")

    table_rows = docx_write_plan.get("table_rows")
    if not isinstance(table_rows, dict):
        errors.append("docx_write_plan.table_rows must be an object")
    else:
        for table_name, rows in table_rows.items():
            if not isinstance(rows, list):
                errors.append(f"docx_write_plan.table_rows.{table_name} must be an array")
                continue
            for row_index, row in enumerate(rows):
                if not isinstance(row, list) or not all(isinstance(cell, str) for cell in row):
                    errors.append(
                        f"docx_write_plan.table_rows.{table_name}[{row_index}] must be an array of strings"
                    )

    if docx_write_plan.get("require_backup") is not True:
        errors.append("docx_write_plan.require_backup must equal true")
    if not isinstance(docx_write_plan.get("preserve_asset_liability_table"), bool):
        errors.append("docx_write_plan.preserve_asset_liability_table must be a boolean")
    if not is_non_empty_string(docx_write_plan.get("change_shading")) or not re.fullmatch(
        r"[0-9A-Fa-f]{6}", docx_write_plan.get("change_shading", "")
    ):
        errors.append("docx_write_plan.change_shading must be a six-digit hexadecimal color")
    output_filename = docx_write_plan.get("output_filename")
    if not is_non_empty_string(output_filename) or not output_filename.endswith(".docx"):
        errors.append("docx_write_plan.output_filename must end with .docx")
    return errors


def validate_bundle(bundle: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    if not isinstance(bundle, dict):
        return ["bundle must be a JSON object"]

    try:
        required = set(schema["required"])
        properties = set(schema["properties"])
    except (KeyError, TypeError):
        return ["schema is missing top-level contract"]

    errors: list[str] = []
    errors.extend(
        f"missing top-level field: {name}"
        for name in sorted(required - bundle.keys())
    )
    errors.extend(
        f"unknown top-level field: {name}"
        for name in sorted(bundle.keys() - properties)
    )
    for name in ("company_name", "reporting_basis", "currency", "unit"):
        if not is_non_empty_string(bundle.get(name)):
            errors.append(f"{name} must be a non-empty string")
    if bundle.get("schema_version") != "1.0":
        errors.append("schema_version must equal 1.0")
    periods = bundle.get("periods")
    if not isinstance(periods, list) or not periods or not all(
        is_non_empty_string(period) for period in periods
    ):
        errors.append("periods must be a non-empty array of non-empty strings")
    errors.extend(
        validate_financial_tables(bundle.get("financial_tables"), bundle.get("sources", {}))
    )
    errors.extend(validate_ratios(bundle.get("ratios")))
    errors.extend(validate_risk_points(bundle.get("risk_points"), bundle.get("sources", {})))
    errors.extend(validate_pending(bundle.get("pending_verification")))
    errors.extend(validate_docx_write_plan(bundle.get("docx_write_plan"), schema))
    return errors


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def write_result(path: Path, valid: bool, errors: list[str]) -> None:
    path.write_text(
        json.dumps({"valid": valid, "errors": errors}, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="UTF-8 financial_analysis_bundle JSON")
    parser.add_argument("--schema", type=Path, required=True, help="bundle contract schema")
    parser.add_argument("--out", type=Path, required=True, help="validation result JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        bundle = load_json(args.bundle)
        schema = load_json(args.schema)
        if not isinstance(schema, dict):
            raise ValueError("schema root must be a JSON object")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors = [f"file/JSON error: {error}"]
        try:
            write_result(args.out, False, errors)
        except OSError as output_error:
            print(f"file/JSON error: {output_error}", file=sys.stderr)
        return 2

    errors = validate_bundle(bundle, schema)
    try:
        write_result(args.out, not errors, errors)
    except OSError as error:
        print(f"file/JSON error: {error}", file=sys.stderr)
        return 2
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
