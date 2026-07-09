# Listed-Company Official Data

## Purpose

Use this reference when the target company is listed and the user asks for financial analysis based on public disclosure.

## Workflow

1. Identify stock code, exchange, company name, and required periods.
2. Prefer official announcement PDFs:
   - annual reports for full-year statements;
   - prior annual reports when a three-year comparison needs the oldest year;
   - quarterly reports for latest interim data.
3. Save downloaded PDFs and a manifest in the workspace.
4. Extract statements from the official PDFs.
5. Keep the original PDF unit and convert to the locked output unit.
6. Mark fields that cannot be stably extracted as `missing`.
7. Use third-party data only for cross-checking unless the user explicitly accepts it.

## SSE Notes

SSE announcement search uses `https://query.sse.com.cn/security/stock/queryCompanyBulletin.do` with a `Referer` header. PDF downloads are under `https://www.sse.com.cn`.

SSE PDF downloads may return:

- gzip-compressed content;
- an HTML JavaScript challenge that sets `acw_sc__v2`.

The bundled `scripts/fetch_sse_announcements.py` handles both cases. If it fails, ask the user for local official PDFs rather than falling back to third-party APIs as the primary source.

## PDF Extraction Notes

Official PDFs are not uniform. A statement line may appear as:

```text
营业收入
44
168,838,102,514.79
170,899,152,276.34
```

or:

```text
营业收入
44
170,899,152,276.34 147,693,604,994.14
```

Extraction should find all amount tokens after a label, skip note numbers, and support labels split across adjacent lines.

## Data Pack Requirements

Each metric period must carry:

- raw source value;
- source unit;
- converted output value;
- output unit;
- source name/file;
- status.

Do not write `missing`, `conflict`, `unit_missing`, or `source_missing` values into正文 except as caveats or pending-verification items.
