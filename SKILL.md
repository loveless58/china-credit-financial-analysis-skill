---
name: china-credit-financial-analysis
description: Use when Codex needs to draft, update, replace, validate, or insert the financial analysis section of a Chinese bank credit review report from DOCX reports, official listed-company disclosures, audit reports, financial tables, metric packs, or user-provided financial data. Use for source hierarchy checks, unit locking, asset-liability summary table format preservation, DOCX backup/edit workflows, deterministic ratio calculation, and pending-verification lists. Do not use for credit approval decisions, credit limit recommendations, valuation, investment research, or market-price advice.
---

# China Credit Financial Analysis

## Overview

Draft or update the financial analysis section of a Chinese bank credit review report. Keep every number auditable: each value must come from a verified source, a metric pack, an extracted report table, or deterministic calculation.

## Hard Rules

1. Do not invent financial numbers, periods, units, ratios, reasons for changes, or conclusions.
2. Treat listed-company official disclosures, exchange announcements, audit reports, and user-provided original statements as primary sources. Third-party finance APIs are cross-check sources only unless the user explicitly accepts them as pending-verification data.
3. Lock the output unit to the source report template or user instruction. If the template says `万元`, do not write `亿元` in the financial section.
4. Preserve the original asset-liability summary table format when replacing that table. Clone the template table OOXML and replace cell text only whenever the template table exists.
5. Mark all inserted or replaced financial-section content with the configured change shading, default `FFF2CC`.
6. Calculate ratios and year-on-year changes with deterministic tooling; do not rely on mental math.
7. Exclude `unit_missing`, `conflict`, `missing`, and `llm_generated_blocked` metrics from正文; place them in the pending-verification list.
8. Treat `source_missing` as pending verification unless the user explicitly says it may be used with caveat language.
9. Use Chinese bank credit-review tone. Do not use investment-research wording such as `买入`, `加仓`, `估值便宜`, `安全边际`, or price-target language.
10. Do not output final approval conclusions such as `同意授信`, `风险可控`, `建议批复额度`, or equivalent wording.
11. Before writing any DOCX, create a timestamped backup. No backup means no write-back.
12. Replace an existing financial-analysis section only after section localization succeeds. If localization is uncertain, output a draft and pending-verification list instead.

## Required References

Read only the files needed for the current task:

- Source hierarchy: `references/source-priority.md`.
- Metric schema and calculation rules: `references/metric-schema.md`.
- Writing boundaries and review tone: `references/writing-rules.md`.
- DOCX backup and write-back safety: `references/docx-safety.md`.
- DOCX financial-section order, table format, font, unit, and shading contract: `references/docx-format-contract.md`.
- Listed-company official disclosure workflow: `references/listed-company-official-data.md`.

## Workflow

1. Identify inputs: DOCX path, target company, reporting periods, listed-company status, user-provided data files, write-back mode, and allowed workspace.
2. Copy outside-workspace DOCX files into the workspace before editing.
3. Extract the existing financial section and financial-looking tables from the DOCX. Detect the template unit, table order, table anchor text, and style samples.
4. Choose data sources by priority. For listed companies, prefer official exchange/company disclosure PDFs; use third-party APIs only for cross-checking or with caveat language.
5. Normalize data into a metric pack with `company_name`, `currency`, `source_unit`, `unit`, `conversion_factor`, `reporting_basis`, `periods`, `metrics`, and per-metric `source` and `status`.
6. Convert source units to the locked output unit with deterministic code.
7. Run deterministic calculations with `scripts/calculate_credit_metrics.py` or equivalent local tooling. Use calculated outputs as the only source for ratios and validation rows.
8. Draft the section from `templates/credit_financial_analysis_base.md`, adapting the bank and industry templates only when relevant.
9. If replacing DOCX content:
   - Back up the input DOCX.
   - Localize the financial-analysis section.
   - Preserve the source file order: `合并数据：` -> asset-liability summary table -> `本部财务数据：` -> `财务指标数据：` -> indicator table -> `合并财务情况分析：`.
   - Clone the original asset-liability summary table format when present; otherwise create a visually equivalent table and record the fallback.
   - Apply change shading to every inserted/replaced paragraph and table cell.
10. Run `scripts/validate_financial_docx.py` or an equivalent structural check before reporting completion.
11. Try visual render QA when the environment has Word/LibreOffice/render tools. If not available, explicitly say visual QA was not completed.

## Script Quick Start

Extract DOCX paragraphs and financial tables:

```bash
python scripts/extract_docx_financials.py report.docx --out-dir extracted
```

Fetch official SSE announcements:

```bash
python scripts/fetch_sse_announcements.py --stock-code 600519 --keywords "2025年年度报告,2024年年度报告,2026年第一季度报告" --out-dir official_sources
```

Extract official PDF metrics:

```bash
python scripts/extract_official_report_metrics.py --manifest official_sources/manifest.json --company-name 贵州茅台酒股份有限公司 --output-unit 万元 --out official_metric_pack.json
```

Calculate metrics and audit Markdown:

```bash
python scripts/calculate_credit_metrics.py input_metrics.json --out-dir outputs
```

Back up a DOCX:

```bash
python scripts/backup_docx.py report.docx
```

Preserve the template asset-liability table format while replacing values:

```bash
python scripts/preserve_financial_table_format.py report.docx rows.json --out report_table_replaced.docx --table-key asset_liability --anchor 资产负债简表 --mode replace-template
```

Validate the final DOCX:

```bash
python scripts/validate_financial_docx.py --docx report_updated.docx --target-unit 万元 --expected-shading FFF2CC --body-font 仿宋_GB2312 --body-size 14 --table-font 仿宋 --table-size 12
```

## Output Contract

Always distinguish:

- Data sources used, split into primary and auxiliary sources.
- Source unit, output unit, and conversion rule.
- Verified metrics and deterministic calculated metrics.
- Missing, conflicting, source-insufficient, or unit-unclear data.
- DOCX output path, backup path, write-back mode, and replacement range.
- Whether the asset-liability summary table format was cloned from the original template or recreated as fallback.
- Structural validation results.
- Pending human verification items.
- Limitations, including unavailable visual render QA.

## Common Mistakes

| Mistake | Required response |
|---|---|
| Using a third-party API as the main listed-company source | Replace with official disclosure data or mark as pending verification. |
| Template unit is `万元` but output uses `亿元` | Stop and regenerate with the locked template unit. |
| Recreating the asset-liability summary table with default formatting | Clone the original table OOXML and replace cell text only, or record why fallback was necessary. |
| Input numbers have no unit | Do not write them into正文; ask for unit or list them as pending verification. |
| Two sources conflict | Do not choose silently; list the conflict and request confirmation. |
| Reason for a financial movement is not sourced | State the trend only and write that the reason needs further verification. |
| Financial section cannot be located | Do not replace; use conservative insertion or output Markdown only. |
| Visual QA cannot run | State that only structural validation was completed. |
