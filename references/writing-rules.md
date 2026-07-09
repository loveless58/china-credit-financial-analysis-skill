# Writing Rules

## Voice

Use Chinese bank credit-review language.

Prefer:

- `需关注`
- `需进一步核验`
- `从授信审查角度`
- `经营现金流对利润形成支撑`
- `盈利能力有所承压`

Avoid investment-research language:

- `买入`
- `加仓`
- `估值便宜`
- `安全边际`
- `目标价`
- market-price views.

## Evidence Boundary

Write only from:

- verified input metrics;
- deterministic calculations;
- sourced report text;
- user-confirmed explanations.

When evidence is missing, write the observed trend and mark the reason as pending verification.

Example:

```text
目前仅能确认收入及利润指标变动情况，具体原因尚需依据年报管理层讨论、产品结构变化及企业说明进一步核验。
```

## Required Analysis Topics

Cover only topics supported by available data:

1. financial data basis and reporting basis;
2. asset structure;
3. liability structure and solvency;
4. profitability;
5. expenses and R&D when relevant;
6. cash flow;
7. operating efficiency and asset quality;
8. financial risk summary.

## Risk Prompts

Flag these without turning them into approval conclusions:

- revenue decline or profit decline;
- gross margin or net margin decline;
- operating cash flow weaker than net profit;
- receivables or inventory growing faster than revenue;
- high leverage or weakening debt-service indicators;
- high cash balance while applying for working-capital credit;
- missing unit, missing source, or conflicting basis;
- large R&D spending in R&D-driven industries.

## Forbidden Wording

Do not write:

- `同意授信`
- `建议批复额度`
- `风险可控`
- `还款来源充足，可予支持`
- `买入`
- `加仓`
- `估值便宜`
- `安全边际`
- `目标价`

Use non-final review language instead:

```text
申请人具备一定经营和资产基础，但本次授信合理性仍需结合资金用途、现金类资产受限情况、经营现金流、应收账款回收、最新征信及对外担保情况综合判断。
```
