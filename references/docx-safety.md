# DOCX Safety Rules

## File Boundary

- Edit only files in the current workspace or in a user-approved writable directory.
- If the user provides a DOCX outside the workspace, create a workspace copy and edit the copy.
- Never overwrite the only original file by default.
- Create a timestamped backup before any write-back.

## Backup Name

Use:

```text
{original-stem}.backup-{YYYYMMDD-HHMMSS}.docx
```

The backup must not overwrite an existing file.

## Output Name

Default:

```text
{original-stem}_财务分析更新稿.docx
```

For company-specific replacements, include the target company or version suffix in the output name.

## Replacement Rules

Use replacement mode only when all are true:

- the user requested replacement or the task clearly requires replacing the financial section;
- the financial-analysis section is localized;
- the end boundary is localized;
- a backup exists;
- output path is known.

If localization is uncertain, do not replace. Output Markdown or use conservative insertion.

## Section Anchors

Common start anchors:

- `财务分析`
- `财务状况`
- `资产负债`
- `盈利能力`
- `现金流`

Common end anchors:

- next same-level heading;
- `行业分析`;
- `担保分析`;
- `风险分析`.

## Change Log

After writing DOCX, create a modification note with:

- original file path;
- backup path;
- output path;
- write-back mode;
- replacement range;
- old-text summary;
- new-text summary;
- primary and auxiliary data sources;
- source unit and output unit;
- table-format preservation result;
- validation result;
- unresolved and pending-verification items.
