#!/usr/bin/env python3
"""Audit report draft numbers against an allowed metric/calculation payload."""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


NUMBER_RE = re.compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?%?")
BODY_STATUSES = {"verified", "calculated"}


def normalize_number(text: str) -> str:
    numeric_text = text.strip().replace(",", "").rstrip("%")
    return format(Decimal(numeric_text).normalize(), "f")


def number_key(text: str) -> tuple[str, bool] | None:
    raw = text.strip()
    if not NUMBER_RE.fullmatch(raw):
        return None
    try:
        return normalize_number(raw), raw.endswith("%")
    except (InvalidOperation, ValueError):
        return None


def is_bundle_payload(payload: dict[str, Any]) -> bool:
    return payload.get("schema_version") == "1.0" and isinstance(
        payload.get("financial_tables"), dict
    )


def collect_bundle_allowed(payload: dict[str, Any]) -> set[tuple[str, bool]]:
    allowed: set[tuple[str, bool]] = set()
    for table in payload.get("financial_tables", {}).values():
        if not isinstance(table, dict):
            continue
        for row in table.get("rows", []):
            if not isinstance(row, dict):
                continue
            for item in row.get("values", {}).values():
                if not isinstance(item, dict) or item.get("status") not in BODY_STATUSES:
                    continue
                value_key = number_key(str(item.get("value", "")))
                if value_key is not None:
                    allowed.add(value_key)
    for ratio in payload.get("ratios", {}).values():
        if not isinstance(ratio, dict) or ratio.get("status") not in BODY_STATUSES:
            continue
        for field in ("value", "display"):
            value_key = number_key(str(ratio.get(field, "")))
            if value_key is not None:
                allowed.add(value_key)
    for period in payload.get("periods", []):
        period_key = number_key(str(period))
        if period_key is not None:
            allowed.add(period_key)
    return allowed


def collect_allowed(payload: dict[str, Any]) -> set[tuple[str, bool]]:
    if is_bundle_payload(payload):
        return collect_bundle_allowed(payload)

    allowed: set[tuple[str, bool]] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"value", "display"} and value not in (None, ""):
                    key_value = number_key(str(value))
                    if key_value is not None:
                        allowed.add(key_value)
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    for key in ("metrics", "calculated_metrics", "financial_tables", "ratios"):
        visit(payload.get(key, {}))
    for period in payload.get("periods", []):
        period_key = number_key(str(period))
        if period_key is not None:
            allowed.add(period_key)
    return allowed


def canonical_period_year(period: Any) -> str | None:
    match = re.fullmatch(r"(\d{4})(?:Q[1-4])?", str(period).strip())
    return match.group(1) if match is not None else None


def is_structural_number(draft: str, start: int, end: int) -> bool:
    line_start = draft.rfind("\n", 0, start) + 1
    line_prefix = draft[line_start:start]
    after = draft[end : min(len(draft), end + 2)]

    if re.fullmatch(r"[ \t]*(?:[-*+][ \t]+)?", line_prefix) and re.match(
        r"[.、．)）]", after
    ):
        return True
    if re.fullmatch(r"[ \t]*#{1,6}[ \t]+", line_prefix) and (
        not after or after[0].isspace()
    ):
        return True
    if start > 0 and draft[start - 1] == "表":
        return end == len(draft) or bool(re.match(r"[：:\s、，,）)\]】]", draft[end:]))
    return (
        start > 0
        and draft[start - 1] == "第"
        and end < len(draft)
        and draft[end] in "章节项"
    )


def is_contextual_non_financial_number(
    draft: str,
    start: int,
    end: int,
    raw: str,
    declared_bundle_years: set[str] | None = None,
) -> bool:
    normalized = normalize_number(raw)
    if normalized.isdigit():
        if is_contextual_year(draft, start, end, raw):
            return declared_bundle_years is None or normalized in declared_bundle_years
        return is_structural_number(draft, start, end)
    return False


def is_contextual_year(draft: str, start: int, end: int, raw: str) -> bool:
    normalized = normalize_number(raw)
    if not normalized.isdigit() or not 1900 <= int(normalized) <= 2100:
        return False
    after = draft[end : min(len(draft), end + 12)]
    return any(token in after for token in ("年", "年度", "至", "月", "日"))


def audit_text(draft: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed: set[tuple[str, bool]] = set()
    bundle_payloads = [payload for payload in payloads if is_bundle_payload(payload)]
    declared_bundle_years = (
        {
            year
            for payload in bundle_payloads
            for period in payload.get("periods", [])
            if (year := canonical_period_year(period)) is not None
        }
        if bundle_payloads
        else None
    )
    for payload in payloads:
        allowed.update(collect_allowed(payload))

    findings = []
    for match in NUMBER_RE.finditer(draft):
        raw = match.group(0)
        if (
            declared_bundle_years is not None
            and is_contextual_year(draft, match.start(), match.end(), raw)
            and normalize_number(raw) not in declared_bundle_years
        ):
            findings.append(
                {
                    "number": raw,
                    "offset": match.start(),
                    "status": "not_in_allowed_payload",
                }
            )
            continue
        if is_contextual_non_financial_number(
            draft,
            match.start(),
            match.end(),
            raw,
            declared_bundle_years,
        ):
            continue
        key = number_key(raw)
        if key is None or key not in allowed:
            findings.append(
                {
                    "number": raw,
                    "offset": match.start(),
                    "status": "not_in_allowed_payload",
                }
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft_md", type=Path)
    parser.add_argument("allowed_json", type=Path)
    parser.add_argument("--extra-allowed-json", action="append", default=[], type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    draft = args.draft_md.read_text(encoding="utf-8-sig")
    payload = json.loads(args.allowed_json.read_text(encoding="utf-8-sig"))
    payloads = [payload]
    for extra_path in args.extra_allowed_json:
        payloads.append(json.loads(extra_path.read_text(encoding="utf-8-sig")))
    findings = audit_text(draft, payloads)

    args.out.write_text(json.dumps({"findings": findings}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"findings": len(findings), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
