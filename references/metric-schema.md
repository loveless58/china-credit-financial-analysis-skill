# Metric Schema

## Required Pack Shape

Use this shape whenever possible:

```json
{
  "company_name": "贵州茅台酒股份有限公司",
  "currency": "CNY",
  "source_unit": "元",
  "unit": "万元",
  "conversion_factor": "0.0001",
  "reporting_basis": "合并口径",
  "periods": ["2023", "2024", "2025", "2026Q1"],
  "sources": {
    "annual_2025": {
      "name": "贵州茅台2025年年度报告（上交所公告PDF）",
      "file": "official_sources/贵州茅台2025年年度报告.pdf",
      "type": "official_disclosure"
    }
  },
  "metrics": {
    "total_assets": {
      "2025": {
        "raw_value": "303834844021.44",
        "raw_unit": "元",
        "value": "30383484.40",
        "unit": "万元",
        "source": "贵州茅台2025年年度报告（上交所公告PDF）",
        "status": "verified"
      }
    }
  }
}
```

## Status Values

| Status | Meaning |正文 use |
|---|---|---|
| `verified` | Source, period, unit, and basis are clear | Yes |
| `calculated` | Deterministic calculation from verified values | Yes |
| `source_missing` | No traceable source | No, except caveat |
| `unit_missing` | Unit unclear | No |
| `conflict` | Sources disagree | No |
| `missing` | Could not extract | No |
| `llm_generated_blocked` | Would require guessing | No |

## Unit Conversion

Keep raw source values and display values.

Common CNY conversions:

| Source unit | Output unit | Factor |
|---|---:|---:|
| 元 | 万元 | 0.0001 |
| 元 | 亿元 | 0.00000001 |
| 万元 | 元 | 10000 |
| 亿元 | 万元 | 10000 |

Do not convert by mental math. Use Decimal or spreadsheet formulas.

## Common Metrics

Balance sheet:

- monetary_funds
- accounts_receivable
- inventory
- total_current_assets
- fixed_assets
- total_non_current_assets
- total_assets
- short_term_borrowings
- accounts_payable
- contract_liabilities
- total_current_liabilities
- long_term_borrowings
- total_non_current_liabilities
- total_liabilities
- share_capital
- capital_reserve
- surplus_reserve
- undistributed_profit
- minority_equity
- total_equity
- liabilities_and_equity

Income statement:

- total_operating_income
- operating_revenue
- operating_cost
- taxes_and_surcharges
- selling_expenses
- administrative_expenses
- rd_expenses
- financial_expenses
- investment_income
- operating_profit
- total_profit
- net_profit
- parent_net_profit

Cash flow:

- cash_inflow_operating
- net_cash_operating
- cash_received_investment
- investment_income_cash
- cash_paid_long_assets
- cash_paid_investment
- net_cash_investing
- cash_received_borrowings
- cash_paid_debt
- cash_paid_dividend_interest
- net_cash_financing
- cash_equiv_net_increase

Ratios:

- revenue_yoy
- parent_net_profit_yoy
- asset_liability_ratio
- gross_margin
- net_margin
- operating_cashflow_to_parent_net_profit
- monetary_funds_to_assets
- accounts_receivable_to_assets
- inventory_to_assets
