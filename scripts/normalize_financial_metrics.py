#!/usr/bin/env python3
"""Normalize simple row/period financial tables into the metric-pack shape."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

METRIC_ALIASES = {
    "营业收入": "revenue",
    "营业总收入": "revenue",
    "营业成本": "operating_cost",
    "净利润": "net_profit",
    "经营活动产生现金流量净额": "operating_cash_flow",
    "经营活动现金流量净额": "operating_cash_flow",
    "资产总计": "total_assets",
    "总资产": "total_assets",
    "负债合计": "total_liabilities",
    "总负债": "total_liabilities",
    "货币资金": "cash",
    "应收账款": "accounts_receivable",
    "存货": "inventory",
    "销售费用": "selling_expense",
    "管理费用": "admin_expense",
    "研发费用": "rd_expense",
    "财务费用": "finance_expense",
}


def parse_number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "—", "不适用"}:
        return None
    if text.endswith("%"):
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("rows_json", type=Path, help="JSON file containing rows as a 2D array")
    parser.add_argument("--rows-key", default="rows")
    parser.add_argument("--company-name", default="")
    parser.add_argument("--currency", default="CNY")
    parser.add_argument("--unit", default="万元")
    parser.add_argument("--reporting-basis", default="合并口径")
    parser.add_argument("--source", default="用户提供或报告抽取表格")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.rows_json.read_text(encoding="utf-8-sig"))
    rows = data.get(args.rows_key, data if isinstance(data, list) else None)
    if not isinstance(rows, list) or len(rows) < 2:
        raise SystemExit("rows_json must contain a 2D table with a header row")

    header = [str(x).strip() for x in rows[0]]
    periods = [h for h in header[1:] if h]
    pack = {
        "company_name": args.company_name,
        "currency": args.currency,
        "unit": args.unit,
        "reporting_basis": args.reporting_basis,
        "periods": periods,
        "metrics": {},
    }

    for row in rows[1:]:
        if not row:
            continue
        label = str(row[0]).strip()
        metric = METRIC_ALIASES.get(label)
        if not metric:
            continue
        pack["metrics"].setdefault(metric, {})
        for period, raw in zip(periods, row[1:]):
            value = parse_number(raw)
            status = "verified" if value is not None else "missing"
            pack["metrics"][metric][period] = {"value": value, "source": args.source, "status": status}

    args.out.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"periods": len(periods), "metrics": len(pack["metrics"]), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
