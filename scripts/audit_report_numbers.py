#!/usr/bin/env python3
"""Audit report draft numbers against an allowed metric/calculation payload."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


NUMBER_RE = re.compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?%?")


def normalize_number(text: str) -> str:
    return text.replace(",", "").rstrip("%")


def collect_allowed(payload: dict) -> set[str]:
    allowed: set[str] = set()
    for metric_periods in payload.get("metrics", {}).values():
        for entry in metric_periods.values():
            value = entry.get("value")
            if value is not None:
                allowed.add(normalize_number(str(value)))
    for row in payload.get("calculated_metrics", []):
        for key in ("value", "display"):
            value = row.get(key)
            if value:
                allowed.add(normalize_number(str(value)))
                if str(value).endswith("%"):
                    allowed.add(normalize_number(str(value).replace("%", "")))
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft_md", type=Path)
    parser.add_argument("allowed_json", type=Path)
    parser.add_argument("--extra-allowed-json", action="append", default=[], type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    draft = args.draft_md.read_text(encoding="utf-8-sig")
    payload = json.loads(args.allowed_json.read_text(encoding="utf-8-sig"))
    allowed = collect_allowed(payload)
    for extra_path in args.extra_allowed_json:
        allowed.update(collect_allowed(json.loads(extra_path.read_text(encoding="utf-8-sig"))))
    findings = []
    for match in NUMBER_RE.finditer(draft):
        raw = match.group(0)
        normalized = normalize_number(raw)
        if is_contextual_non_financial_number(draft, match.start(), match.end(), raw):
            continue
        if normalized not in allowed:
            findings.append({"number": raw, "offset": match.start(), "status": "not_in_allowed_payload"})

    args.out.write_text(json.dumps({"findings": findings}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"findings": len(findings), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
