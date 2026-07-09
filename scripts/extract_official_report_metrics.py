#!/usr/bin/env python3
"""Extract a metric pack from official listed-company report PDFs."""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import fitz


NUM_TOKEN_RE = re.compile(r"-?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+)")

BALANCE_METRICS = {
    "monetary_funds": "货币资金",
    "trading_financial_assets": "交易性金融资产",
    "notes_receivable": "应收票据",
    "accounts_receivable": "应收账款",
    "prepayments": "预付款项",
    "other_receivables": "其他应收款",
    "inventory": "存货",
    "other_current_assets": "其他流动资产",
    "total_current_assets": "流动资产合计",
    "long_term_equity_investment": "长期股权投资",
    "investment_property": "投资性房地产",
    "fixed_assets": "固定资产",
    "construction_in_progress": "在建工程",
    "intangible_assets": "无形资产",
    "goodwill": "商誉",
    "long_term_prepaid_expense": "长期待摊费用",
    "deferred_tax_assets": "递延所得税资产",
    "total_non_current_assets": "非流动资产合计",
    "total_assets": "资产总计",
    "short_term_borrowings": "短期借款",
    "notes_payable": "应付票据",
    "accounts_payable": "应付账款",
    "advance_receipts": "预收款项",
    "contract_liabilities": "合同负债",
    "employee_benefits_payable": "应付职工薪酬",
    "taxes_payable": "应交税费",
    "other_payables": "其他应付款",
    "current_portion_noncurrent_liabilities": "一年内到期的非流动负债",
    "total_current_liabilities": "流动负债合计",
    "long_term_borrowings": "长期借款",
    "deferred_tax_liabilities": "递延所得税负债",
    "total_non_current_liabilities": "非流动负债合计",
    "total_liabilities": "负债合计",
    "share_capital": "实收资本（或股本）",
    "capital_reserve": "资本公积",
    "surplus_reserve": "盈余公积",
    "undistributed_profit": "未分配利润",
    "minority_equity": "少数股东权益",
    "total_equity": "所有者权益（或股东权益）合计",
    "liabilities_and_equity": "负债和所有者权益（或股东权益）总计",
}

INCOME_METRICS = {
    "total_operating_income": "一、营业总收入",
    "operating_revenue": "其中：营业收入",
    "operating_cost": "其中：营业成本",
    "taxes_and_surcharges": "税金及附加",
    "selling_expenses": "销售费用",
    "administrative_expenses": "管理费用",
    "rd_expenses": "研发费用",
    "financial_expenses": "财务费用",
    "investment_income": "投资收益",
    "operating_profit": "三、营业利润",
    "total_profit": "四、利润总额",
    "net_profit": "五、净利润",
    "parent_net_profit": "1.归属于母公司股东的净利润",
}

CASHFLOW_METRICS = {
    "cash_inflow_operating": "经营活动现金流入小计",
    "net_cash_operating": "经营活动产生的现金流量净额",
    "cash_received_investment": "收回投资收到的现金",
    "investment_income_cash": "取得投资收益收到的现金",
    "cash_paid_long_assets": "购建固定资产、无形资产和其他长期资产支付的现金",
    "cash_paid_investment": "投资支付的现金",
    "net_cash_investing": "投资活动产生的现金流量净额",
    "cash_received_borrowings": "取得借款收到的现金",
    "cash_paid_debt": "偿还债务支付的现金",
    "cash_paid_dividend_interest": "分配股利、利润或偿付利息支付的现金",
    "net_cash_financing": "筹资活动产生的现金流量净额",
    "cash_equiv_net_increase": "五、现金及现金等价物净增加额",
}

METRICS = {**BALANCE_METRICS, **INCOME_METRICS, **CASHFLOW_METRICS}


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def amount_tokens(line: str) -> list[Decimal]:
    return [Decimal(token.replace(",", "")) for token in NUM_TOKEN_RE.findall(line)]


def lines_from_pdf(path: Path) -> list[str]:
    doc = fitz.open(path)
    return "\n".join(page.get_text("text") for page in doc).splitlines()


def section(lines: list[str], start_anchor: str, end_anchors: tuple[str, ...]) -> list[str]:
    start = next((i for i, line in enumerate(lines) if start_anchor in line), None)
    if start is None:
        return []
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if any(anchor in lines[i] for anchor in end_anchors):
            end = i
            break
    return lines[start:end]


def locate(lines: list[str], label: str) -> int | None:
    compact = norm(label)
    for i, line in enumerate(lines):
        if norm(line) == compact:
            return i
    for i in range(len(lines)):
        if norm("".join(lines[i : i + 4])).startswith(compact):
            return i
    return None


def amounts_after(lines: list[str], label: str, count: int = 2) -> list[Decimal | None]:
    index = locate(lines, label)
    if index is None:
        return [None] * count
    values: list[Decimal] = []
    for line in lines[index + 1 : index + 18]:
        for value in amount_tokens(line):
            values.append(value)
            if len(values) == count:
                return values
    return values + [None] * (count - len(values))


def infer_columns(title: str) -> list[str]:
    year_match = re.search(r"(20\d{2})", title or "")
    year = int(year_match.group(1)) if year_match else None
    if year and "第一季度" in title:
        return [f"{year}Q1", f"{year - 1}Q1"]
    if year and "年度报告" in title:
        return [str(year), str(year - 1)]
    return ["current", "previous"]


def factor_to_output(source_unit: str, output_unit: str) -> Decimal:
    units = {
        ("元", "万元"): Decimal("0.0001"),
        ("元", "亿元"): Decimal("0.00000001"),
        ("万元", "万元"): Decimal("1"),
        ("万元", "元"): Decimal("10000"),
        ("亿元", "万元"): Decimal("10000"),
        ("亿元", "亿元"): Decimal("1"),
    }
    try:
        return units[(source_unit, output_unit)]
    except KeyError as exc:
        raise SystemExit(f"unsupported unit conversion: {source_unit} -> {output_unit}") from exc


def convert(value: Decimal | None, factor: Decimal) -> str | None:
    if value is None:
        return None
    return str((value * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def extract_report(record: dict) -> dict:
    path = Path(record["file"])
    lines = lines_from_pdf(path)
    balance = section(lines, "合并资产负债表", ("母公司资产负债表", "合并利润表"))
    income = section(lines, "合并利润表", ("母公司利润表", "合并现金流量表"))
    cashflow = section(lines, "合并现金流量表", ("母公司现金流量表", "公司负责人"))
    sections = {"balance": balance, "income": income, "cashflow": cashflow}
    extracted = {}
    for metric, label in BALANCE_METRICS.items():
        extracted[metric] = amounts_after(balance, label)
    for metric, label in INCOME_METRICS.items():
        extracted[metric] = amounts_after(income, label)
    for metric, label in CASHFLOW_METRICS.items():
        extracted[metric] = amounts_after(cashflow, label)
    return {"columns": infer_columns(record.get("title", "")), "metrics": extracted, "sections": {k: len(v) for k, v in sections.items()}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--output-unit", default="万元")
    parser.add_argument("--source-unit", default="元")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    factor = factor_to_output(args.source_unit, args.output_unit)
    pack = {
        "company_name": args.company_name,
        "currency": "CNY",
        "source_unit": args.source_unit,
        "unit": args.output_unit,
        "conversion_factor": str(factor),
        "reporting_basis": "合并口径",
        "periods": [],
        "sources": {},
        "metrics": {metric: {} for metric in METRICS},
    }

    for source_index, record in enumerate(manifest):
        source_id = f"source_{source_index + 1}"
        source_name = record.get("title") or Path(record["file"]).name
        pack["sources"][source_id] = {**record, "name": source_name}
        extracted = extract_report(record)
        for col_index, period in enumerate(extracted["columns"]):
            if period not in pack["periods"]:
                pack["periods"].append(period)
            for metric in METRICS:
                raw = extracted["metrics"][metric][col_index]
                pack["metrics"][metric][period] = {
                    "raw_value": str(raw) if raw is not None else None,
                    "raw_unit": args.source_unit,
                    "value": convert(raw, factor),
                    "unit": args.output_unit,
                    "source": source_name,
                    "status": "verified" if raw is not None else "missing",
                }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(args.out), "periods": pack["periods"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
