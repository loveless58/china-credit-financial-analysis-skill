# Source Priority

## Core Rule

Use the strongest available source. Every metric written into正文 must have source, unit, reporting basis, and status.

## Priority Levels

| Level | Source type |正文 use |
|---|---|---|
| P0 primary | Exchange announcement PDF, listed-company annual/quarterly report, audit report, user-provided original financial statements, source DOCX/Excel/PDF tables | May be `verified` if unit and basis are clear |
| P1 accepted with note | Company official website disclosure page, complete report downloaded from company site, user-confirmed internal data pack | May be `verified` if the source is traceable |
| P2 cross-check only | Eastmoney, Tonghuashun, Wind page/API, Xueqiu, media article, research report, extracted summary page | Do not use as primary listed-company source unless user explicitly accepts caveat treatment |

## Listed-Company Rule

For a listed company, default to P0 official disclosures. If a third-party interface is used before official disclosures are checked, treat it as a process failure and redo the data pack.

## Source Status

- `verified`: source, unit, period, and reporting basis are clear.
- `calculated`: deterministic calculation from verified values.
- `source_missing`: value has no traceable source.
- `unit_missing`: value has no clear unit.
- `conflict`: two sources disagree and no source is user-confirmed as controlling.
- `missing`: value could not be extracted.
- `llm_generated_blocked`: value would require guessing or model invention.

## Required Output Notes

The modification note must list:

- primary source files/URLs;
- auxiliary sources, if any;
- whether third-party data was used only for cross-checking;
- source unit and output unit;
- unresolved source gaps.
