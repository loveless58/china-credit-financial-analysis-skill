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


def collect_allowed(payload: dict[str, Any]) -> set[tuple[str, bool]]:
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


def is_contextual_non_financial_number(draft: str, start: int, end: int, raw: str) -> bool:
    normalized = normalize_number(raw)
    before = draft[max(0, start - 12) : start]
    after = draft[end : min(len(draft), end + 12)]
    if normalized.isdigit():
        value = int(normalized)
        if 1900 <= value <= 2100 and any(token in after for token in ("年", "年度", "至", "月", "日")):
            return True
        if 0 <= value <= 50 and any(token in before for token in ("###", "##", "\n#", "表", "第", "事项", "包括：\n")):
            return True
        if 0 <= value <= 50 and any(token in after for token in ("。", ".", "、", " ")):
            line_start = draft.rfind("\n", 0, start) + 1
            line_prefix = draft[line_start:start].strip()
            if line_prefix in {"", "-", "*"}:
                return True
    return False


def audit_text(draft: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed: set[tuple[str, bool]] = set()
    for payload in payloads:
        allowed.update(collect_allowed(payload))

    findings = []
    for match in NUMBER_RE.finditer(draft):
        raw = match.group(0)
        if is_contextual_non_financial_number(draft, match.start(), match.end(), raw):
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
