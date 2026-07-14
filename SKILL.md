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
- Bundle contract: read `references/financial-analysis-bundle.md` whenever producing an analysis-only handoff or preparing a DOCX write-back.
- Capability request/result contract: read `references/financial-capability-contract.md` whenever an orchestrator, Codex task, or command-line run will perform formal DOCX write-back.

## Workflow

1. Identify inputs: read-only DOCX path, target company, reporting periods, listed-company status, user-provided data files, requested mode, and an output directory outside the Skill repository.
2. Extract the existing financial section and financial-looking tables from the DOCX. Detect the template unit, table order, table anchor text, and style samples without modifying the source file.
3. Choose data sources by priority. For listed companies, prefer official exchange/company disclosure PDFs; use third-party APIs only for cross-checking or with caveat language.
4. Normalize data into a metric pack with `company_name`, `currency`, `source_unit`, `unit`, `conversion_factor`, `reporting_basis`, `periods`, `metrics`, and per-metric `source` and `status`.
5. Convert source units and calculate ratios and year-on-year changes with deterministic code. Use deterministic outputs as the only source for calculated bundle values.
6. Read `references/financial-analysis-bundle.md`, draft `docx_write_plan.analysis_markdown`, and assemble the complete `financial_analysis_bundle.json`. This bundle is the only public handoff interface before write-back; downstream audit and DOCX operations must not consume temporary calculation files.
7. Validate the assembled bundle with `scripts/validate_financial_analysis_bundle.py`. Do not continue to DOCX write-back unless validation exits successfully.
8. In analysis-only mode, deliver the validated `financial_analysis_bundle.json` and its validation result without creating or updating a DOCX.
9. For formal DOCX write-back, assemble `capability_request.json` according to `references/financial-capability-contract.md` and call only `scripts/run_financial_analysis_capability.py`. Relative paths are resolved from the request file; the artifact directory must be outside the Skill repository and absent or empty.
10. Treat `capability_result.json` as the machine-readable execution receipt. Report its `status`, `errors`, source-integrity result, metrics, and artifact paths. Do not infer success from process output or the presence of a DOCX alone.
11. The unified runner delegates DOCX work to `scripts/update_financial_docx.py`. That internal updater remains the sole owner of backup creation, section localization, format-preserving replacement, number audit, structural validation, change log, and pending-verification output.
12. Keep the bundle, validation results, backups, updated DOCX files, audits, Markdown deliverables, renders, and all other run artifacts in the declared output directory outside the Skill repository.
13. Try visual render QA when the environment has Word/LibreOffice/render tools. If not available, explicitly say visual QA was not completed.

## Script Quick Start

Extract DOCX paragraphs and financial tables:

```powershell
python -B scripts/extract_docx_financials.py C:\tmp\source.docx --out-dir C:\tmp\financial-analysis-extracted
```

Fetch official SSE announcements:

```powershell
python -B scripts/fetch_sse_announcements.py --stock-code 600519 --keywords "2025年年度报告,2024年年度报告,2026年第一季度报告" --out-dir C:\tmp\financial-analysis-official-sources
```

Extract official PDF metrics:

```powershell
python -B scripts/extract_official_report_metrics.py --manifest C:\tmp\financial-analysis-official-sources\manifest.json --company-name 贵州茅台酒股份有限公司 --output-unit 万元 --out C:\tmp\official_metric_pack.json
```

Calculate metrics and audit Markdown:

```powershell
python -B scripts/calculate_credit_metrics.py C:\tmp\input_metrics.json --out-dir C:\tmp\financial-analysis-calculated
```

Validate the public bundle before any write-back:

```powershell
python -B scripts/validate_financial_analysis_bundle.py C:\tmp\financial_analysis_bundle.json --schema schemas\financial_analysis_bundle.schema.json --out C:\tmp\bundle_validation.json
```

Formally write back a validated bundle through the public capability entry point:

```powershell
python -B scripts/run_financial_analysis_capability.py C:\tmp\capability_request.json
```

Exit code `0` means `success`, `2` means a governed `blocked` result, and `3` means execution failure or an untrusted request. Read the emitted `capability_result.json`; do not use the exit code as the complete audit record.

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
- The validated `financial_analysis_bundle.json` path and bundle validation result; these may be the complete deliverable in analysis-only mode.
- For formal write-back, the `capability_result.json` path, stable status, errors, source before/after hashes, audit metrics, and descriptors for every generated artifact.
- Confirmation that every run artifact path is outside the Skill repository.

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
