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

## Asset-Liability Summary Table Preservation

The asset-liability summary table is format-sensitive. When the original report has an asset-liability summary table:

1. Locate it by anchors such as `资产负债简表`, `资产总计`, `负债合计`, `利润及利润分配表`, or `现金流量简表`.
2. Clone the original table OOXML.
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
5. If row/column counts are incompatible, stop and either adapt the row matrix to the template or explicitly record fallback creation.

Fallback creation is allowed only when the original template table cannot be found or is structurally incompatible. The fallback must still match the standard:

- financial-section change shading: default `FFF2CC`;
-正文 font: `仿宋_GB2312`, 14 pt unless template sampling shows otherwise;
- table font: `仿宋`, 12 pt unless template sampling shows otherwise;
- centered table cells;
- black single-line borders;
- title contains reporting basis and unit.

## Change Marking

Apply change shading to every inserted or replaced paragraph and every cell in inserted/replaced tables. Default shading is `FFF2CC`.

## Validation

Before completion, verify:

- financial section localized;
- target unit appears;
- forbidden non-target unit does not appear in the financial section;
- asset-liability summary table exists;
- table title contains the unit;
- table shape is not trivially simplified;
- change shading exists on paragraphs and tables;
- fonts are written in OOXML `w:eastAsia` when Python `font.name` cannot read Chinese font names;
- sample amounts match the metric pack.
