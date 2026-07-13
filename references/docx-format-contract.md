# DOCX Format Contract

## Financial Section Order

When replacing an existing financial-analysis section, preserve the source report's reading order:

1. financial-analysis heading;
2. data basis note;
3. `合并数据：`;
4. asset-liability summary table;
5. `本部财务数据：`;
6. parent-company table or parent-company data-gap note;
7. `财务指标数据：`;
8. financial indicator table;
9. `合并财务情况分析：`;
10. analysis paragraphs.

Do not insert a separate Codex recommendation block unless the user asks for an inserted note rather than replacement.

## Unit Locking

1. Detect the original template unit from table titles and nearby text, for example `单位：万元`.
2. If the user specifies a unit, user instruction controls.
3. If the template unit exists and the user did not override it, output tables and正文 must use the template unit.
4. If source reports use another unit, convert deterministically and record the conversion.
5. Validate the financial section does not contain a non-target unit such as `亿元` when target unit is `万元`.
6. Validate the target asset-liability table title itself contains the target unit. A unit appearing only in analysis paragraphs cannot satisfy the table-title unit check.

## Asset-Liability Summary Table Preservation

The asset-liability summary table is format-sensitive. When the original report has an asset-liability summary table:

1. Use OOXML body order to locate it between the configured financial-section start and nearest following end anchor. When `preceding_anchor` is supplied, apply that context filter before deciding uniqueness, even when only one anchored table exists. The target table's nearest preceding non-empty paragraph must exactly match `合并数据` after trimming surrounding whitespace and an optional trailing Chinese or ASCII colon. A parent-company table whose nearest context is `本部财务数据` therefore blocks the write. After section, table, and context filters are applied, zero or multiple candidates block the write.
2. Reuse the original table OOXML in place.
3. Replace cell text only.
4. Preserve:
   - table style and width;
   - row heights and column widths where present;
   - merged cells;
   - borders;
   - cell shading;
   - paragraph alignment;
   - run-level Chinese font and size;
   - bold settings.
5. If row/column counts are incompatible, stop and record the failure in `待核验清单.md`; Phase 1 does not create a fallback table.

## Financial Body Localization

Locate replacement or insertion anchors in this order:

1. locate `section_start`;
2. locate the nearest following `section_end`;
3. require exactly one `analysis_anchor` inside that bounded interval.

An analysis anchor after the nearest end anchor or multiple analysis anchors inside the interval block the write before any DOCX is saved.

## Change Marking

Apply change shading to every inserted or replaced analysis paragraph. Default shading is `FFF2CC`. Text-only updates to the existing asset-liability table retain the original cell shading and all other table formatting; `change_shading` is not applied to those cells.

## Validation

Before completion, verify:

- financial section localized;
- target unit appears in the scoped financial-section paragraphs or the shared target asset-liability table;
- forbidden non-target unit does not appear in those scoped paragraphs or the target table;
- asset-liability summary table exists;
- target asset-liability table title contains the target unit independently of body text;
- table shape is not trivially simplified;
- change shading exists on inserted or replaced analysis paragraphs;
- the target table's before/after format fingerprint covers every unique OOXML `_tc` cell, including cells whose planned value is empty, and remains unchanged;
- every planned empty output cell is explicitly verified to contain no non-empty text node;
- fonts are written in OOXML `w:eastAsia` when Python `font.name` cannot read Chinese font names;
- sample amounts match the metric pack.

## Staging And Atomic Publication

1. Save the modified document to a uniquely named staging DOCX in the final output directory.
2. Reopen the staging DOCX for all format-fingerprint, text-format, structure, unit, and planned-empty-cell checks.
3. Publish the staging DOCX to the final output filename with an atomic same-directory replace only after every check passes.
4. On any failure after backup creation, delete staging and do not leave a final-named updated DOCX. Preserve the backup, `number_audit.json`, `validation_result.json`, and `待核验清单.md` as failure evidence.
