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
CREDIT_SEMANTICS = r"(?:授信(?:审批)?|信贷)"
AFFIRMATIVE_DECISIONS = r"(?:同意|给予|予以|批准|核准|批复)"
NEGATIVE_DECISIONS = r"(?:不建议|不同意|不予|拒绝|否决|不通过)"
PASS_DECISIONS = r"(?:通过|批准|核准)"
AMOUNT_DECISIONS = r"(?:建议|拟定|核定|确定|决定|批准|核准|批复|给予|予以)"
MONEY_AMOUNT = r"(?:人民币)?\d+(?:\.\d+)?(?:亿元|万元|元)"
CREDIT_LIMIT_SEMANTICS = r"(?:额度|限额)"
TEXT_WINDOW_SEPARATOR = re.compile(r"[。！？!?；;\r\n]+")
CREDIT_SEMANTICS_PATTERN = re.compile(CREDIT_SEMANTICS)
AMOUNT_DECISIONS_PATTERN = re.compile(AMOUNT_DECISIONS)
MONEY_AMOUNT_PATTERN = re.compile(MONEY_AMOUNT)
CREDIT_LIMIT_SEMANTICS_PATTERN = re.compile(CREDIT_LIMIT_SEMANTICS)
FORBIDDEN_CONCLUSION_PATTERNS = {
    "同意": re.compile(
        rf"{AFFIRMATIVE_DECISIONS}.{{0,8}}{CREDIT_SEMANTICS}|"
        rf"{CREDIT_SEMANTICS}.{{0,8}}{AFFIRMATIVE_DECISIONS}"
    ),
    "否决": re.compile(
        rf"{NEGATIVE_DECISIONS}.{{0,8}}{CREDIT_SEMANTICS}|"
        rf"{CREDIT_SEMANTICS}.{{0,8}}{NEGATIVE_DECISIONS}"
    ),
    "通过": re.compile(
        rf"{PASS_DECISIONS}.{{0,8}}{CREDIT_SEMANTICS}|"
        rf"{CREDIT_SEMANTICS}.{{0,8}}{PASS_DECISIONS}"
    ),
    "风险结论": re.compile(r"风险可控"),
}


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def object_contract_errors(value: Any, contract: dict[str, Any], prefix: str) -> list[str]:
    """Apply a contract object's required and additionalProperties rules."""
    if not isinstance(value, dict):
        return [f"{prefix} must be an object"]

    required = set(contract["required"])
    properties = set(contract["properties"])
    errors = [
        f"{prefix} missing field: {name}" for name in sorted(required - value.keys())
    ]
    if contract.get("additionalProperties") is False:
        errors.extend(
            f"{prefix} unknown field: {name}"
            for name in sorted(value.keys() - properties)
        )
    return errors


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


def validate_sources(sources: Any, sources_contract: dict[str, Any]) -> list[str]:
    if not isinstance(sources, dict):
        return ["sources must be an object"]

    source_contract = sources_contract["additionalProperties"]
    errors: list[str] = []
    for source_id, source in sources.items():
        prefix = f"sources.{source_id}"
        errors.extend(object_contract_errors(source, source_contract, prefix))
        if not isinstance(source, dict):
            continue
        for field in ("name", "type", "file"):
            if not is_non_empty_string(source.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
    return errors


def validate_financial_tables(
    financial_tables: Any,
    sources: Any,
    financial_tables_contract: dict[str, Any],
) -> list[str]:
    if not isinstance(financial_tables, dict):
        return ["financial_tables must be an object"]

    table_contract = financial_tables_contract["additionalProperties"]
    row_contract = table_contract["properties"]["rows"]["items"]
    value_contract = row_contract["properties"]["values"]["additionalProperties"]
    errors: list[str] = []
    for table_name, table in financial_tables.items():
        prefix = f"financial_tables.{table_name}"
        errors.extend(object_contract_errors(table, table_contract, prefix))
        if not isinstance(table, dict):
            continue
        rows = table.get("rows")
        if not isinstance(rows, list):
            errors.append(f"{prefix}.rows must be an array")
            continue
        for row_index, row in enumerate(rows):
            row_prefix = f"{prefix}.rows[{row_index}]"
            errors.extend(object_contract_errors(row, row_contract, row_prefix))
            if not isinstance(row, dict):
                continue
            for field in ("metric", "label"):
                if not is_non_empty_string(row.get(field)):
                    errors.append(f"{row_prefix}.{field} must be a non-empty string")
            values = row.get("values")
            if not isinstance(values, dict):
                errors.append(f"{row_prefix}.values must be an object")
                continue
            for period, item in values.items():
                item_prefix = f"{row_prefix}.values.{period}"
                errors.extend(object_contract_errors(item, value_contract, item_prefix))
                if not isinstance(item, dict):
                    continue
                status = item.get("status")
                if status not in ALLOWED_STATUSES:
                    errors.append(f"{item_prefix}.status must be an allowed status")
                errors.extend(
                    validate_source_refs(
                        item.get("source_refs"),
                        sources,
                        item_prefix,
                        require_non_empty=status == "verified",
                    )
                )
    return errors


def validate_ratios(ratios: Any, ratios_contract: dict[str, Any]) -> list[str]:
    if not isinstance(ratios, dict):
        return ["ratios must be an object"]

    ratio_contract = ratios_contract["additionalProperties"]
    input_contract = ratio_contract["properties"]["inputs"]["items"]
    errors: list[str] = []
    for ratio_name, ratio in ratios.items():
        prefix = f"ratios.{ratio_name}"
        errors.extend(object_contract_errors(ratio, ratio_contract, prefix))
        if not isinstance(ratio, dict):
            continue
        for field in ("label", "period", "formula", "display"):
            if not is_non_empty_string(ratio.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        if ratio.get("status") != "calculated":
            errors.append(f"{prefix}.status must equal calculated")

        inputs = ratio.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            errors.append(f"{prefix}.inputs must be a non-empty array")
            continue
        for input_index, input_item in enumerate(inputs):
            input_prefix = f"{prefix}.inputs[{input_index}]"
            errors.extend(object_contract_errors(input_item, input_contract, input_prefix))
            if not isinstance(input_item, dict):
                continue
            for field in ("metric", "period"):
                if not is_non_empty_string(input_item.get(field)):
                    errors.append(f"{input_prefix}.{field} must be a non-empty string")
    return errors


def text_windows(text: str) -> list[str]:
    """Keep decision terms within their sentence, semicolon, or line window."""
    return [window.strip() for window in TEXT_WINDOW_SEPARATOR.split(text) if window.strip()]


def contains_forbidden_amount_decision(text: str) -> bool:
    for window in text_windows(text):
        if not CREDIT_SEMANTICS_PATTERN.search(window):
            continue
        if not AMOUNT_DECISIONS_PATTERN.search(window):
            continue
        if MONEY_AMOUNT_PATTERN.search(window) or CREDIT_LIMIT_SEMANTICS_PATTERN.search(
            window
        ):
            return True
    return False


def forbidden_conclusion_categories(text: Any) -> list[str]:
    if not is_non_empty_string(text):
        return []
    categories = [
        category
        for category, pattern in FORBIDDEN_CONCLUSION_PATTERNS.items()
        if pattern.search(text)
    ]
    if contains_forbidden_amount_decision(text):
        categories.append("额度")
    return categories


def validate_risk_points(
    risk_points: Any,
    sources: Any,
    risk_points_contract: dict[str, Any],
) -> list[str]:
    if not isinstance(risk_points, list):
        return ["risk_points must be an array"]

    risk_point_contract = risk_points_contract["items"]
    errors: list[str] = []
    for index, risk_point in enumerate(risk_points):
        prefix = f"risk_points[{index}]"
        errors.extend(object_contract_errors(risk_point, risk_point_contract, prefix))
        if not isinstance(risk_point, dict):
            continue
        for field in ("category", "statement"):
            if not is_non_empty_string(risk_point.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        categories = forbidden_conclusion_categories(risk_point.get("statement"))
        if categories:
            errors.append(
                f"{prefix}.statement contains forbidden conclusion categories: {', '.join(categories)}"
            )
        errors.extend(
            validate_source_refs(
                risk_point.get("evidence_refs"), sources, prefix, require_non_empty=True
            )
        )
    return errors


def validate_pending(
    pending_verification: Any,
    pending_contract: dict[str, Any],
) -> list[str]:
    if not isinstance(pending_verification, list):
        return ["pending_verification must be an array"]

    pending_item_contract = pending_contract["items"]
    allowed_pending_statuses = ALLOWED_STATUSES - BODY_STATUSES
    errors: list[str] = []
    for index, pending_item in enumerate(pending_verification):
        prefix = f"pending_verification[{index}]"
        errors.extend(object_contract_errors(pending_item, pending_item_contract, prefix))
        if not isinstance(pending_item, dict):
            continue
        if not is_non_empty_string(pending_item.get("issue")):
            errors.append(f"{prefix}.issue must be a non-empty string")
        if pending_item.get("status") not in allowed_pending_statuses:
            errors.append(f"{prefix}.status must be a non-body status")
    return errors


def validate_docx_write_plan(
    docx_write_plan: Any,
    docx_write_plan_contract: dict[str, Any],
) -> list[str]:
    errors = object_contract_errors(
        docx_write_plan, docx_write_plan_contract, "docx_write_plan"
    )
    if not isinstance(docx_write_plan, dict):
        return errors

    if docx_write_plan.get("mode") not in {"insert", "replace"}:
        errors.append("docx_write_plan.mode must be insert or replace")
    for field in (
        "section_start",
        "analysis_anchor",
        "section_end",
        "analysis_markdown",
        "target_unit",
    ):
        if not is_non_empty_string(docx_write_plan.get(field)):
            errors.append(f"docx_write_plan.{field} must be a non-empty string")
    categories = forbidden_conclusion_categories(docx_write_plan.get("analysis_markdown"))
    if categories:
        errors.append(
            "docx_write_plan.analysis_markdown contains forbidden conclusion "
            f"categories: {', '.join(categories)}"
        )

    table_rows = docx_write_plan.get("table_rows")
    if not isinstance(table_rows, dict):
        errors.append("docx_write_plan.table_rows must be an object")
    else:
        for table_name, rows in table_rows.items():
            if not isinstance(rows, list):
                errors.append(f"docx_write_plan.table_rows.{table_name} must be an array")
                continue
            for row_index, row in enumerate(rows):
                if not isinstance(row, list) or not all(
                    isinstance(cell, str) for cell in row
                ):
                    errors.append(
                        f"docx_write_plan.table_rows.{table_name}[{row_index}] "
                        "must be an array of strings"
                    )

    if docx_write_plan.get("require_backup") is not True:
        errors.append("docx_write_plan.require_backup must equal true")
    if not isinstance(docx_write_plan.get("preserve_asset_liability_table"), bool):
        errors.append("docx_write_plan.preserve_asset_liability_table must be a boolean")
    change_shading = docx_write_plan.get("change_shading")
    if not is_non_empty_string(change_shading) or not re.fullmatch(
        r"[0-9A-Fa-f]{6}", change_shading
    ):
        errors.append("docx_write_plan.change_shading must be a six-digit hexadecimal color")
    output_filename = docx_write_plan.get("output_filename")
    if not is_non_empty_string(output_filename) or not output_filename.endswith(".docx"):
        errors.append("docx_write_plan.output_filename must end with .docx")
    return errors


def validate_bundle(bundle: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    if not isinstance(bundle, dict):
        return ["bundle must be a JSON object"]
    if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
        return ["schema is missing top-level contract"]

    properties = schema["properties"]
    try:
        sources_contract = properties["sources"]
        financial_tables_contract = properties["financial_tables"]
        ratios_contract = properties["ratios"]
        risk_points_contract = properties["risk_points"]
        pending_contract = properties["pending_verification"]
        docx_write_plan_contract = properties["docx_write_plan"]
        required = set(schema["required"])
    except (KeyError, TypeError):
        return ["schema is missing top-level contract"]

    errors = object_contract_errors(bundle, schema, "top-level")
    errors = [
        error.replace("top-level missing field: ", "missing top-level field: ").replace(
            "top-level unknown field: ", "unknown top-level field: "
        )
        for error in errors
    ]
    if bundle.get("schema_version") != "1.0":
        errors.append("schema_version must equal 1.0")
    for name in ("company_name", "reporting_basis", "currency", "unit"):
        if not is_non_empty_string(bundle.get(name)):
            errors.append(f"{name} must be a non-empty string")
    periods = bundle.get("periods")
    if not isinstance(periods, list) or not periods or not all(
        is_non_empty_string(period) for period in periods
    ):
        errors.append("periods must be a non-empty array of non-empty strings")
    errors.extend(validate_sources(bundle.get("sources"), sources_contract))
    errors.extend(
        validate_financial_tables(
            bundle.get("financial_tables"),
            bundle.get("sources", {}),
            financial_tables_contract,
        )
    )
    errors.extend(validate_ratios(bundle.get("ratios"), ratios_contract))
    errors.extend(
        validate_risk_points(
            bundle.get("risk_points"), bundle.get("sources", {}), risk_points_contract
        )
    )
    errors.extend(validate_pending(bundle.get("pending_verification"), pending_contract))
    errors.extend(
        validate_docx_write_plan(bundle.get("docx_write_plan"), docx_write_plan_contract)
    )
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
