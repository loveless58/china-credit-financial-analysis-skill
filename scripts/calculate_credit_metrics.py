#!/usr/bin/env python3
"""Calculate credit-review financial metrics from a JSON metric pack."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, DivisionByZero, InvalidOperation, getcontext
from pathlib import Path
from typing import Any

getcontext().prec = 28

ALLOWED_SOURCE_STATUSES = {"verified", "calculated", "source_missing"}
BLOCKED_STATUSES = {"unit_missing", "conflict", "missing", "llm_generated_blocked"}

METRIC_LABELS = {
    "revenue": "营业收入",
    "operating_cost": "营业成本",
    "net_profit": "净利润",
    "net_profit_attributable": "归母净利润",
    "deducted_net_profit_attributable": "扣非归母净利润",
    "operating_cash_flow": "经营活动现金流量净额",
    "total_assets": "总资产",
    "total_liabilities": "总负债",
    "cash": "货币资金",
    "accounts_receivable": "应收账款",
    "inventory": "存货",
    "current_assets": "流动资产",
    "current_liabilities": "流动负债",
    "interest_bearing_debt": "有息负债",
    "short_interest_bearing_debt": "短期有息债务",
    "ebitda": "EBITDA",
    "interest_expense": "利息费用",
}

CALCULATIONS = {
    "revenue_yoy": ("营业收入同比", "current / previous - 1", "yoy", ("revenue",)),
    "net_profit_yoy": ("净利润同比", "current / previous - 1", "yoy", ("net_profit",)),
    "np_attributable_yoy": ("归母净利润同比", "current / previous - 1", "yoy", ("net_profit_attributable",)),
    "deducted_np_attributable_yoy": ("扣非归母净利润同比", "current / previous - 1", "yoy", ("deducted_net_profit_attributable",)),
    "debt_asset_ratio": ("资产负债率", "total_liabilities / total_assets", "ratio", ("total_liabilities", "total_assets")),
    "net_margin": ("净利率", "net_profit / revenue", "ratio", ("net_profit", "revenue")),
    "gross_margin": ("毛利率", "(revenue - operating_cost) / revenue", "gross_margin", ("revenue", "operating_cost")),
    "ocf_np_ratio": ("经营现金流/净利润", "operating_cash_flow / net_profit", "ratio", ("operating_cash_flow", "net_profit")),
    "cash_asset_ratio": ("货币资金占总资产比重", "cash / total_assets", "ratio", ("cash", "total_assets")),
    "ar_asset_ratio": ("应收账款占总资产比重", "accounts_receivable / total_assets", "ratio", ("accounts_receivable", "total_assets")),
    "inventory_asset_ratio": ("存货占总资产比重", "inventory / total_assets", "ratio", ("inventory", "total_assets")),
    "current_ratio": ("流动比率", "current_assets / current_liabilities", "multiple", ("current_assets", "current_liabilities")),
    "quick_ratio": ("速动比率", "(current_assets - inventory) / current_liabilities", "quick_ratio", ("current_assets", "inventory", "current_liabilities")),
    "ar_turnover": ("应收账款周转率", "revenue / average(accounts_receivable)", "turnover", ("revenue", "accounts_receivable")),
    "inventory_turnover": ("存货周转率", "operating_cost / average(inventory)", "turnover", ("operating_cost", "inventory")),
    "interest_bearing_debt_ratio": ("有息负债率", "interest_bearing_debt / total_assets", "ratio", ("interest_bearing_debt", "total_assets")),
    "cash_short_debt_coverage": ("货币资金覆盖短债倍数", "cash / short_interest_bearing_debt", "multiple", ("cash", "short_interest_bearing_debt")),
    "ebitda_interest_coverage": ("EBITDA利息保障倍数", "ebitda / interest_expense", "multiple", ("ebitda", "interest_expense")),
}

P1_METRICS = {
    "current_ratio",
    "quick_ratio",
    "ar_turnover",
    "inventory_turnover",
    "interest_bearing_debt_ratio",
    "cash_short_debt_coverage",
    "ebitda_interest_coverage",
}


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def metric_entry(pack: dict[str, Any], metric: str, period: str) -> dict[str, Any]:
    return pack.get("metrics", {}).get(metric, {}).get(period, {"value": None, "status": "missing", "source": None})


def usable(entry: dict[str, Any]) -> tuple[bool, str | None]:
    status = entry.get("status", "missing")
    if status in BLOCKED_STATUSES:
        return False, f"status={status}"
    if status not in ALLOWED_SOURCE_STATUSES:
        return False, f"status={status}"
    if decimal_or_none(entry.get("value")) is None:
        return False, "value missing or non-numeric"
    return True, None


def value(pack: dict[str, Any], metric: str, period: str) -> tuple[Decimal | None, str | None, dict[str, Any]]:
    entry = metric_entry(pack, metric, period)
    ok, reason = usable(entry)
    if not ok:
        return None, reason, entry
    return decimal_or_none(entry.get("value")), None, entry


def divide(numerator: Decimal, denominator: Decimal) -> tuple[Decimal | None, str | None]:
    if denominator == 0:
        return None, "division by zero"
    try:
        return numerator / denominator, None
    except (DivisionByZero, InvalidOperation) as exc:
        return None, str(exc)


def display_ratio(v: Decimal | None) -> str:
    if v is None:
        return ""
    return f"{(v * Decimal('100')).quantize(Decimal('0.01'))}%"


def display_multiple(v: Decimal | None) -> str:
    if v is None:
        return ""
    return f"{v.quantize(Decimal('0.01'))}倍"


def display_number(v: Decimal | None) -> str:
    if v is None:
        return ""
    return str(v.quantize(Decimal("0.0001")).normalize())


def average_value(pack: dict[str, Any], metric: str, idx: int, periods: list[str]) -> tuple[Decimal | None, str | None, list[dict[str, Any]]]:
    if idx <= 0:
        return None, "previous period missing", []
    current_period = periods[idx]
    previous_period = periods[idx - 1]
    current, current_reason, current_entry = value(pack, metric, current_period)
    previous, previous_reason, previous_entry = value(pack, metric, previous_period)
    if current is None:
        return None, current_reason, [current_entry, previous_entry]
    if previous is None:
        return None, previous_reason, [current_entry, previous_entry]
    return (current + previous) / Decimal("2"), None, [current_entry, previous_entry]


def calculate_one(pack: dict[str, Any], metric_id: str, idx: int, periods: list[str]) -> dict[str, Any]:
    label, formula, kind, inputs = CALCULATIONS[metric_id]
    period = periods[idx]
    source_inputs: list[dict[str, Any]] = []

    def blocked(reason: str) -> dict[str, Any]:
        return {
            "metric": metric_id,
            "label": label,
            "period": period,
            "formula": formula,
            "value": None,
            "display": "",
            "status": "missing",
            "reason": reason,
            "inputs": source_inputs,
        }

    if kind == "yoy":
        if idx <= 0:
            return blocked("previous period missing")
        current, reason, entry = value(pack, inputs[0], period)
        source_inputs.append({"metric": inputs[0], "period": period, **entry})
        if current is None:
            return blocked(reason or "current value missing")
        previous_period = periods[idx - 1]
        previous, reason, entry = value(pack, inputs[0], previous_period)
        source_inputs.append({"metric": inputs[0], "period": previous_period, **entry})
        if previous is None:
            return blocked(reason or "previous value missing")
        result, reason = divide(current, previous)
        if result is None:
            return blocked(reason or "calculation failed")
        result -= Decimal("1")
        return result_row(metric_id, label, period, formula, result, display_ratio(result), source_inputs)

    if kind in {"ratio", "multiple"}:
        numerator, reason, entry = value(pack, inputs[0], period)
        source_inputs.append({"metric": inputs[0], "period": period, **entry})
        if numerator is None:
            return blocked(reason or "numerator missing")
        denominator, reason, entry = value(pack, inputs[1], period)
        source_inputs.append({"metric": inputs[1], "period": period, **entry})
        if denominator is None:
            return blocked(reason or "denominator missing")
        result, reason = divide(numerator, denominator)
        if result is None:
            return blocked(reason or "calculation failed")
        display = display_ratio(result) if kind == "ratio" else display_multiple(result)
        return result_row(metric_id, label, period, formula, result, display, source_inputs)

    if kind == "gross_margin":
        revenue, reason, entry = value(pack, "revenue", period)
        source_inputs.append({"metric": "revenue", "period": period, **entry})
        if revenue is None:
            return blocked(reason or "revenue missing")
        cost, reason, entry = value(pack, "operating_cost", period)
        source_inputs.append({"metric": "operating_cost", "period": period, **entry})
        if cost is None:
            return blocked(reason or "operating cost missing")
        result, reason = divide(revenue - cost, revenue)
        if result is None:
            return blocked(reason or "calculation failed")
        return result_row(metric_id, label, period, formula, result, display_ratio(result), source_inputs)

    if kind == "quick_ratio":
        current_assets, reason, entry = value(pack, "current_assets", period)
        source_inputs.append({"metric": "current_assets", "period": period, **entry})
        if current_assets is None:
            return blocked(reason or "current assets missing")
        inventory, reason, entry = value(pack, "inventory", period)
        source_inputs.append({"metric": "inventory", "period": period, **entry})
        if inventory is None:
            return blocked(reason or "inventory missing")
        current_liabilities, reason, entry = value(pack, "current_liabilities", period)
        source_inputs.append({"metric": "current_liabilities", "period": period, **entry})
        if current_liabilities is None:
            return blocked(reason or "current liabilities missing")
        result, reason = divide(current_assets - inventory, current_liabilities)
        if result is None:
            return blocked(reason or "calculation failed")
        return result_row(metric_id, label, period, formula, result, display_multiple(result), source_inputs)

    if kind == "turnover":
        base_metric = inputs[1]
        numerator_metric = inputs[0]
        numerator, reason, entry = value(pack, numerator_metric, period)
        source_inputs.append({"metric": numerator_metric, "period": period, **entry})
        if numerator is None:
            return blocked(reason or "turnover numerator missing")
        avg, reason, entries = average_value(pack, base_metric, idx, periods)
        for offset, entry in enumerate(entries):
            source_period = periods[idx - offset] if idx - offset >= 0 else period
            source_inputs.append({"metric": base_metric, "period": source_period, **entry})
        if avg is None:
            return blocked(reason or "average denominator missing")
        result, reason = divide(numerator, avg)
        if result is None:
            return blocked(reason or "calculation failed")
        return result_row(metric_id, label, period, formula, result, display_multiple(result), source_inputs)

    return blocked(f"unknown calculation kind: {kind}")


def result_row(metric_id: str, label: str, period: str, formula: str, value_: Decimal, display: str, inputs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "metric": metric_id,
        "label": label,
        "period": period,
        "formula": formula,
        "value": str(value_),
        "display": display,
        "status": "calculated",
        "reason": "",
        "inputs": inputs,
    }


def pending_items(pack: dict[str, Any], calculated: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for metric, periods in pack.get("metrics", {}).items():
        for period, entry in periods.items():
            status = entry.get("status", "missing")
            if status in {"source_missing", *BLOCKED_STATUSES}:
                items.append({
                    "metric": metric,
                    "label": METRIC_LABELS.get(metric, metric),
                    "period": str(period),
                    "status": status,
                    "issue": entry.get("note") or entry.get("source") or "需进一步核验",
                })
    for row in calculated:
        if row["status"] != "calculated":
            if row["reason"] == "previous period missing":
                continue
            items.append({
                "metric": row["metric"],
                "label": row["label"],
                "period": row["period"],
                "status": row["status"],
                "issue": row["reason"],
            })
    return items


def write_markdown(out_dir: Path, pack: dict[str, Any], calculated: list[dict[str, Any]], pending: list[dict[str, str]]) -> None:
    validation = ["# 财务指标校验表", "", "| 指标 | 期间 | 公式 | 结果 | 状态 | 说明 |", "|---|---|---|---:|---|---|"]
    for row in calculated:
        validation.append(
            f"| {row['label']} | {row['period']} | `{row['formula']}` | {row['display']} | {row['status']} | {row['reason']} |"
        )
    (out_dir / "财务指标校验表.md").write_text("\n".join(validation) + "\n", encoding="utf-8")

    pending_lines = ["# 待核验清单", "", "| 指标 | 期间 | 状态 | 事项 |", "|---|---|---|---|"]
    for item in pending:
        pending_lines.append(f"| {item['label']} | {item['period']} | {item['status']} | {item['issue']} |")
    if not pending:
        pending_lines.append("| 无 | - | - | 当前指标包未发现阻断项 |")
    (out_dir / "待核验清单.md").write_text("\n".join(pending_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("metric_pack", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    parser.add_argument("--include-p1", action="store_true", help="Also calculate P1 extended metrics")
    args = parser.parse_args()

    pack = json.loads(args.metric_pack.read_text(encoding="utf-8-sig"))
    periods = [str(period) for period in pack.get("periods", [])]
    if not periods:
        raise SystemExit("metric pack must include non-empty periods")

    calculated = []
    for idx in range(len(periods)):
        for metric_id in CALCULATIONS:
            if metric_id in P1_METRICS and not args.include_p1:
                continue
            calculated.append(calculate_one(pack, metric_id, idx, periods))

    pending = pending_items(pack, calculated)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "company_name": pack.get("company_name"),
        "currency": pack.get("currency"),
        "unit": pack.get("unit"),
        "reporting_basis": pack.get("reporting_basis"),
        "periods": periods,
        "calculated_metrics": calculated,
        "pending_items": pending,
    }
    (args.out_dir / "calculated_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(args.out_dir, pack, calculated, pending)
    print(json.dumps({"out_dir": str(args.out_dir), "calculated": len(calculated), "pending": len(pending)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
