# 财务分析叶子模块第一阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为现有 `china-credit-financial-analysis` Skill 增加稳定的结构化 bundle、确定性校验和完整的 DOCX 安全写回闭环，同时保持业务产物与源码仓库分离。

**Architecture:** 保留当前 `SKILL.md + references + templates + scripts` 结构。`financial_analysis_bundle.json` 是唯一新增公开接口；标准库校验器读取 Schema 并执行字段、状态、来源和禁用结论检查；`update_financial_docx.py` 只编排现有备份、表格保留、正文写入、数字审计、DOCX 校验和修改说明能力。

**Tech Stack:** Python 3.13、Python 标准库、python-docx 1.2.0、JSON Schema Draft 2020-12 文件、现有 Markdown 模板和 OOXML 工具。

## Global Constraints

- 第一阶段复杂度上限：一个公开 bundle、一个 bundle 校验器、一个 DOCX 安全写回入口、复用现有确定性脚本。
- 不引入 `jsonschema`、工作流引擎、状态机、事件日志、MCP、commands、hooks 或 Agent。
- 所有金额和比率必须来自 `verified` 数据或确定性 `calculated` 结果。
- 单位缺失、来源冲突、数据缺失和 `llm_generated_blocked` 数据不得进入正式正文。
- DOCX 写回前必须创建时间戳备份；不得覆盖唯一原件。
- 替换模式必须准确定位 `section_start`、`analysis_anchor` 和 `section_end`。
- 原资产负债表存在时，只替换单元格文本并保留原 OOXML 格式。
- 所有真实业务输入、备份、更新稿、渲染图和审计产物必须写到仓库外目录。
- 不得输出“同意授信”“风险可控”“建议批复额度”等最终审批结论。
- 每个任务按红灯、绿灯、重构的 TDD 顺序执行并单独提交。

---

## File Map

**新增：**

- `schemas/financial_analysis_bundle.schema.json`：bundle 1.0 的公开机器契约。
- `references/financial-analysis-bundle.md`：字段语义和生产、消费约束。
- `scripts/validate_financial_analysis_bundle.py`：无第三方依赖的结构和业务校验器。
- `scripts/selftest_financial_analysis_bundle.py`：bundle 正反例自测试。
- `scripts/selftest_report_number_audit.py`：bundle 数字审计自测试。
- `scripts/update_financial_docx.py`：DOCX 安全写回薄编排入口。
- `scripts/selftest_financial_docx_update.py`：合成 DOCX 端到端自测试。

**修改：**

- `scripts/backup_docx.py`：导出 `create_backup()`。
- `scripts/audit_report_numbers.py`：导出 `audit_text()` 并识别 bundle。
- `scripts/insert_financial_analysis.py`：增加显式锚点、正文替换和格式应用函数。
- `scripts/validate_financial_docx.py`：导出 `validate_financial_docx()`。
- `scripts/export_change_log.py`：导出 `write_change_log()`。
- `SKILL.md`：将 bundle 设为写回前必经接口。
- `.gitignore`：忽略仓库根目录的运行目录。

---

### Task 1: 建立 bundle 1.0 契约和校验器

**Files:**

- Create: `schemas/financial_analysis_bundle.schema.json`
- Create: `references/financial-analysis-bundle.md`
- Create: `scripts/validate_financial_analysis_bundle.py`
- Create: `scripts/selftest_financial_analysis_bundle.py`

**Interfaces:**

- Consumes: UTF-8 JSON object，`schema_version` 必须为 `1.0`。
- Produces: `validate_bundle(bundle: dict[str, Any], schema: dict[str, Any]) -> list[str]`。
- CLI: `python -B scripts/validate_financial_analysis_bundle.py BUNDLE --schema SCHEMA --out RESULT_JSON`。
- Exit codes: `0` valid，`1` invalid，`2` file/JSON error。

- [ ] **Step 1: 写失败的 bundle 自测试**

创建 `scripts/selftest_financial_analysis_bundle.py`。合法样例必须包含以下结构：

```python
def valid_bundle() -> dict:
    return {
        "schema_version": "1.0",
        "company_name": "某测试公司",
        "reporting_basis": "合并口径",
        "currency": "CNY",
        "unit": "万元",
        "periods": ["2024", "2025"],
        "sources": {
            "annual_2025": {
                "name": "某测试公司2025年审计报告",
                "type": "audit_report",
                "file": "source/annual_2025.pdf",
            }
        },
        "financial_tables": {
            "asset_liability": {
                "rows": [{
                    "metric": "total_assets",
                    "label": "资产总计",
                    "values": {
                        "2024": {
                            "value": "100.00",
                            "status": "verified",
                            "source_refs": ["annual_2025"],
                        },
                        "2025": {
                            "value": "120.00",
                            "status": "verified",
                            "source_refs": ["annual_2025"],
                        }
                    },
                }]
            }
        },
        "ratios": {
            "asset_liability_ratio": {
                "label": "资产负债率",
                "period": "2025",
                "formula": "total_liabilities / total_assets",
                "value": "0.5",
                "display": "50.00%",
                "status": "calculated",
                "inputs": [
                    {"metric": "total_liabilities", "period": "2025"},
                    {"metric": "total_assets", "period": "2025"},
                ],
            }
        },
        "risk_points": [{
            "category": "偿债能力",
            "statement": "需关注债务期限结构与经营现金流匹配情况。",
            "evidence_refs": ["annual_2025"],
        }],
        "pending_verification": [],
        "docx_write_plan": {
            "mode": "replace",
            "section_start": "财务分析",
            "analysis_anchor": "合并财务情况分析",
            "section_end": "行业分析",
            "analysis_markdown": "截至2025年末，公司总资产为120.00万元，资产负债率为50.00%。",
            "table_rows": {
                "asset_liability": [
                    ["资产负债简表（合并口径，单位：万元）", "", ""],
                    ["项目", "2024", "2025"],
                    ["资产总计", "100.00", "120.00"],
                ]
            },
            "target_unit": "万元",
            "require_backup": True,
            "preserve_asset_liability_table": True,
            "change_shading": "FFF2CC",
            "output_filename": "某测试公司_财务分析更新稿.docx",
        },
    }
```

用 `tempfile.TemporaryDirectory()` 写入并调用 CLI，覆盖：

```python
cases = [
    ("valid", valid_bundle(), 0),
    ("missing_unit", {**valid_bundle(), "unit": ""}, 1),
    ("unknown_top_level", {**valid_bundle(), "unexpected": True}, 1),
    ("forbidden_conclusion", {
        **valid_bundle(),
        "risk_points": [{
            "category": "结论",
            "statement": "建议同意授信。",
            "evidence_refs": ["annual_2025"],
        }],
    }, 1),
]
```

合法样例断言返回 `0`；非法样例断言返回 `1` 且结果 JSON 的 `errors` 非空。

- [ ] **Step 2: 运行红灯**

Run:

```powershell
python -B scripts/selftest_financial_analysis_bundle.py
```

Expected: FAIL，原因是 validator 尚不存在。

- [ ] **Step 3: 创建公开 Schema**

`schemas/financial_analysis_bundle.schema.json` 使用 Draft 2020-12，顶层设置 `additionalProperties: false`，并要求以下字段：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://local.bank-rm/schemas/financial_analysis_bundle-1.0.json",
  "title": "Financial Analysis Bundle 1.0",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version", "company_name", "reporting_basis", "currency", "unit",
    "periods", "sources", "financial_tables", "ratios", "risk_points",
    "pending_verification", "docx_write_plan"
  ]
}
```

`properties` 必须精确定义：

- `schema_version.const = "1.0"`；
- 四个标识字段为非空字符串；
- `periods` 为非空字符串数组；
- `sources`、`financial_tables`、`ratios` 为 object；
- `risk_points`、`pending_verification` 为 array；
- `pending_verification[*]` 必填非空 `issue` 与合法 `status`，供待核验清单和修改说明直接消费；
- `docx_write_plan` 不允许未知字段，必填 `mode`、三个锚点、`analysis_markdown`、`table_rows`、`target_unit`、两个布尔字段、`change_shading`、`output_filename`；
- `mode` 只允许 `insert`、`replace`；
- `require_backup.const = true`；
- `change_shading` 匹配六位十六进制颜色；
- `output_filename` 必须以 `.docx` 结尾。

- [ ] **Step 4: 实现标准库校验器**

在 `scripts/validate_financial_analysis_bundle.py` 实现：

```python
ALLOWED_STATUSES = {
    "verified", "calculated", "source_missing", "unit_missing",
    "conflict", "missing", "llm_generated_blocked",
}
BODY_STATUSES = {"verified", "calculated"}
FORBIDDEN_CONCLUSIONS = (
    "同意授信", "风险可控", "建议批复额度", "建议同意授信",
)


def validate_bundle(bundle: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(schema["required"])
    properties = set(schema["properties"])
    errors.extend(
        f"missing top-level field: {name}"
        for name in sorted(required - bundle.keys())
    )
    errors.extend(
        f"unknown top-level field: {name}"
        for name in sorted(bundle.keys() - properties)
    )
    for name in ("company_name", "reporting_basis", "currency", "unit"):
        if not isinstance(bundle.get(name), str) or not bundle[name].strip():
            errors.append(f"{name} must be a non-empty string")
    if bundle.get("schema_version") != "1.0":
        errors.append("schema_version must equal 1.0")
    if not isinstance(bundle.get("periods"), list) or not bundle["periods"]:
        errors.append("periods must be a non-empty array")
    errors.extend(validate_financial_tables(bundle.get("financial_tables"), bundle.get("sources", {})))
    errors.extend(validate_ratios(bundle.get("ratios")))
    errors.extend(validate_risk_points(bundle.get("risk_points"), bundle.get("sources", {})))
    errors.extend(validate_pending(bundle.get("pending_verification")))
    errors.extend(validate_docx_write_plan(bundle.get("docx_write_plan"), schema))
    return errors
```

辅助函数执行以下确定规则：

- `financial_tables.*.rows[*].values.*` 每个条目必须有 `value`、合法 `status` 和 `source_refs`。
- `verified` 条目的 `source_refs` 必须存在于顶层 `sources`。
- `ratios.*` 必须有公式、值、展示值、`status: calculated` 和非空 `inputs`。
- `risk_points[*]` 必须有非空 `statement` 与 `evidence_refs`，并拦截禁用结论。
- `pending_verification[*]` 必须有非空 `issue`，且 `status` 只能是非正文状态。
- `docx_write_plan` 按 Schema 的字段集合、类型、常量和枚举校验。
- `docx_write_plan.analysis_markdown` 同样扫描禁用结论，不能绕过 `risk_points` 约束。

成功输出固定为 `{"valid": true, "errors": []}`；失败示例为 `{"valid": false, "errors": ["unit must be a non-empty string"]}`。

- [ ] **Step 5: 编写字段语义文档**

`references/financial-analysis-bundle.md` 写明：

- 顶层字段表和完整合法示例；
- `analysis_markdown` 是 DOCX 正文唯一来源；
- `table_rows` 是模板二维矩阵，不替代分析层 `financial_tables`；
- 正文准入状态；
- future consumer 只能依赖 bundle，不依赖 `calculated_metrics.json` 等临时文件。

- [ ] **Step 6: 运行绿灯并提交**

```powershell
python -B scripts/selftest_financial_analysis_bundle.py
git add schemas/financial_analysis_bundle.schema.json references/financial-analysis-bundle.md scripts/validate_financial_analysis_bundle.py scripts/selftest_financial_analysis_bundle.py
git commit -m "feat: add financial analysis bundle contract"
```

Expected: `financial analysis bundle self-test passed`，提交成功。

---

### Task 2: 让数字反向审计消费 bundle

**Files:**

- Create: `scripts/selftest_report_number_audit.py`
- Modify: `scripts/audit_report_numbers.py:15-79`

**Interfaces:**

- Produces: `audit_text(draft: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]`。
- 现有 CLI 参数和输出保持兼容。

- [ ] **Step 1: 写失败测试**

`scripts/selftest_report_number_audit.py` 直接导入 Task 1 的 `valid_bundle()`，断言：

```python
assert audit_text(
    "截至2025年末，总资产为120.00万元，资产负债率为50.00%。",
    [bundle],
) == []

findings = audit_text("截至2025年末，总资产为999.00万元。", [bundle])
assert [item["number"] for item in findings] == ["999.00"]
```

将 `table_rows` 展平后再审计：`100.00`、`120.00` 通过，`888.00` 被识别。

- [ ] **Step 2: 运行红灯**

```powershell
python -B scripts/selftest_report_number_audit.py
```

Expected: FAIL，因为 `audit_text()` 尚不存在。

- [ ] **Step 3: 实现递归数值收集和可复用审计**

```python
def collect_allowed(payload: dict[str, Any]) -> set[str]:
    allowed: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"value", "display"} and value not in (None, ""):
                    allowed.add(normalize_number(str(value)))
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    for key in ("metrics", "calculated_metrics", "financial_tables", "ratios"):
        visit(payload.get(key, {}))
    for period in payload.get("periods", []):
        allowed.add(normalize_number(str(period)))
    return allowed


def audit_text(draft: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed: set[str] = set()
    for payload in payloads:
        allowed.update(collect_allowed(payload))
    findings = []
    for match in NUMBER_RE.finditer(draft):
        raw = match.group(0)
        if is_contextual_non_financial_number(draft, match.start(), match.end(), raw):
            continue
        if normalize_number(raw) not in allowed:
            findings.append({
                "number": raw,
                "offset": match.start(),
                "status": "not_in_allowed_payload",
            })
    return findings
```

CLI 改为调用 `audit_text()`。

- [ ] **Step 4: 运行绿灯并提交**

```powershell
python -B scripts/selftest_report_number_audit.py
python -B scripts/audit_report_numbers.py --help
git add scripts/audit_report_numbers.py scripts/selftest_report_number_audit.py
git commit -m "feat: audit report numbers from analysis bundle"
```

Expected: self-test 打印 `passed`，CLI help exit `0`。

---

### Task 3: 实现 DOCX 安全写回入口

**Files:**

- Create: `scripts/update_financial_docx.py`
- Create: `scripts/selftest_financial_docx_update.py`
- Modify: `scripts/backup_docx.py:12-39`
- Modify: `scripts/insert_financial_analysis.py:17-110`
- Modify: `scripts/validate_financial_docx.py:76-148`
- Modify: `scripts/export_change_log.py:10-47`

**Interfaces:**

- Main: `update_financial_docx(source_docx: Path, bundle_path: Path, schema_path: Path, out_dir: Path) -> dict[str, str]`。
- CLI: `python -B scripts/update_financial_docx.py SOURCE_DOCX BUNDLE --schema SCHEMA --out-dir OUT_DIR`。
- Produces backup、updated DOCX、`number_audit.json`、`validation_result.json`、`change_log.md`、`待核验清单.md`。

- [ ] **Step 1: 写合成 DOCX 端到端失败测试**

`scripts/selftest_financial_docx_update.py` 在临时目录创建：

- `（五）、财务分析`；
- 20 行 3 列、带字体/底纹/边框的资产负债表；
- `合并财务情况分析：`；
- `旧财务分析内容。`；
- `（六）、行业分析`；
- Task 1 合法 bundle，`table_rows.asset_liability` 同为 20 行 3 列。

成功场景断言：

```python
assert sha256(source_docx) == source_hash_before
assert len(list(out_dir.glob("*.backup-*.docx"))) == 1
assert updated_docx.exists()
assert "旧财务分析内容" not in output_text
assert "总资产为120.00万元" in output_text
assert output_table.cell(2, 2).text == "120.00"
assert east_asia_font(output_table.cell(2, 2).paragraphs[0].runs[0]) == "仿宋"
assert output_table.cell(2, 2).paragraphs[0].runs[0].font.size.pt == 11
assert cell_fill(output_table.cell(2, 2)) == "D9EAD3"
assert json.loads((out_dir / "number_audit.json").read_text(encoding="utf-8"))["findings"] == []
assert json.loads((out_dir / "validation_result.json").read_text(encoding="utf-8"))["failed"] == []
assert (out_dir / "change_log.md").exists()
assert (out_dir / "待核验清单.md").exists()
```

失败场景将正文数字改为 `999.00`，断言 CLI 非零、审计记录该数字、没有更新稿。

第三个场景将 `mode` 改为 `insert`：断言旧正文保留、新建议紧跟分析锚点插入、新段落应用 `FFF2CC` 底纹，并以 `allow_codex_marker=True` 通过结构校验。

- [ ] **Step 2: 运行红灯**

```powershell
python -B scripts/selftest_financial_docx_update.py
```

Expected: FAIL，因为 updater 尚不存在。

- [ ] **Step 3: 导出备份函数**

`scripts/backup_docx.py` 增加：

```python
def backup_path(source: Path, directory: Path | None = None) -> Path:
    target_dir = directory.resolve() if directory else source.resolve().parent
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = target_dir / f"{source.stem}.backup-{stamp}{source.suffix}"
    counter = 1
    while candidate.exists():
        candidate = target_dir / f"{source.stem}.backup-{stamp}-{counter}{source.suffix}"
        counter += 1
    return candidate


def create_backup(source: Path, target: Path | None = None) -> Path:
    source = source.resolve()
    if source.suffix.lower() != ".docx" or not source.is_file():
        raise ValueError(f"invalid DOCX source: {source}")
    target = target.resolve() if target else backup_path(source)
    if target.exists():
        raise FileExistsError(f"backup already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target
```

现有 CLI 调用 `create_backup()`。

- [ ] **Step 4: 增加显式锚点和正文格式函数**

`scripts/insert_financial_analysis.py` 增加：

```python
def find_paragraph_index(document: Document, anchor: str, start: int = 0) -> int:
    for index, paragraph in enumerate(document.paragraphs[start:], start):
        if anchor in paragraph.text:
            return index
    raise ValueError(f"paragraph anchor not found: {anchor}")


def set_paragraph_shading(paragraph, fill: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shd = p_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        p_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def format_run(run, font_name: str, font_size: float) -> None:
    run.font.name = font_name
    run.font.size = Pt(font_size)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), font_name)
```

实现接口：

```python
def replace_analysis_body(
    document: Document,
    section_start: str,
    analysis_anchor: str,
    section_end: str,
    analysis_markdown: str,
    shading: str,
    body_font: str = "仿宋_GB2312",
    body_size: float = 14,
) -> str:
```

行为：要求三个锚点严格有序；只删除分析锚点后、下一章节前的正文段落；不移动表格；逐行写入非空正文；新段落应用底纹、中文字体和字号。插入模式也必须定位分析锚点，禁止追加到文末。

- [ ] **Step 5: 导出 DOCX 校验与修改说明函数**

`scripts/validate_financial_docx.py` 提取：

```python
def validate_financial_docx(
    docx: Path,
    section_start: str,
    section_end: str,
    target_unit: str,
    forbidden_units: list[str],
    expected_shading: str,
    body_font: str | None = None,
    body_size: float | None = None,
    table_font: str | None = None,
    table_size: float | None = None,
    min_asset_table_rows: int = 20,
    allow_codex_marker: bool = False,
) -> dict[str, object]:
```

`section_shading_present` 必须是强制通过项；`replace` 模式要求 Codex 标记不存在，`insert` 模式允许保留标记。

`scripts/export_change_log.py` 提取：

```python
def write_change_log(
    out: Path,
    original: Path,
    workspace_copy: Path,
    backup: Path,
    output: Path,
    mode: str,
    location: str,
    sources: list[str],
    pending: list[str],
    table_preservation: str,
    validation_failed: list[str],
) -> Path:
```

两个现有 CLI 都改为调用新函数，参数保持兼容。

- [ ] **Step 6: 实现安全写回编排**

`update_financial_docx()` 固定执行：

```python
bundle = load_json(bundle_path)
schema = load_json(schema_path)
errors = validate_bundle(bundle, schema)
if errors:
    raise UpdateBlocked("bundle validation failed", errors)

reject_out_dir_inside_skill_repo(out_dir)
out_dir.mkdir(parents=True, exist_ok=True)
backup = create_backup(source_docx, backup_path(source_docx, out_dir))

plan = bundle["docx_write_plan"]
findings = audit_text(plan["analysis_markdown"], [bundle])
table_text = "\n".join(
    str(cell)
    for rows in plan["table_rows"].values()
    for row in rows
    for cell in row
)
findings.extend(audit_text(table_text, [bundle]))
write_json(out_dir / "number_audit.json", {"findings": findings})
if findings:
    raise UpdateBlocked("number audit failed", findings)

document = Document(str(source_docx))
if "asset_liability" in plan["table_rows"]:
    _, table = find_table(document, ["资产负债简表", "资产总计"])
    fill_table(table, plan["table_rows"]["asset_liability"])

if plan["mode"] == "replace":
    location = replace_analysis_body(
        document=document,
        section_start=plan["section_start"],
        analysis_anchor=plan["analysis_anchor"],
        section_end=plan["section_end"],
        analysis_markdown=plan["analysis_markdown"],
        shading=plan["change_shading"],
    )
else:
    location = insert_analysis_body(
        document=document,
        section_start=plan["section_start"],
        analysis_anchor=plan["analysis_anchor"],
        section_end=plan["section_end"],
        analysis_markdown=plan["analysis_markdown"],
        shading=plan["change_shading"],
    )
output = out_dir / plan["output_filename"]
document.save(str(output))
validation = validate_financial_docx(
    docx=output,
    section_start=plan["section_start"],
    section_end=plan["section_end"],
    target_unit=plan["target_unit"],
    forbidden_units=["亿元"] if plan["target_unit"] == "万元" else [],
    expected_shading=plan["change_shading"],
    body_font="仿宋_GB2312",
    body_size=14,
    min_asset_table_rows=20,
    allow_codex_marker=plan["mode"] == "insert",
)
write_json(out_dir / "validation_result.json", validation)
write_pending_markdown(out_dir / "待核验清单.md", bundle["pending_verification"])
write_change_log(
    out=out_dir / "change_log.md",
    original=source_docx,
    workspace_copy=source_docx,
    backup=backup,
    output=output,
    mode=plan["mode"],
    location=location,
    sources=[source["name"] for source in bundle["sources"].values()],
    pending=[item["issue"] for item in bundle["pending_verification"]],
    table_preservation="original OOXML text-only update",
    validation_failed=list(validation["failed"]),
)
if validation["failed"]:
    raise UpdateFailed("DOCX validation failed", validation["failed"])
```

硬规则：

- `out_dir` 位于 Skill 仓库内部时拒绝；
- output 与 source 为同一路径时拒绝；
- 数字审计失败时保留 backup 和审计 JSON，但不生成更新稿；
- 结构校验失败时保留更新稿和证据，但 CLI 返回非零；
- 成功 stdout 只输出路径摘要 JSON。

- [ ] **Step 7: 运行绿灯、编译检查并提交**

```powershell
python -B scripts/selftest_financial_docx_update.py
python -B scripts/selftest_table_format_preservation.py
python -B -m compileall -q scripts
git add scripts/backup_docx.py scripts/insert_financial_analysis.py scripts/validate_financial_docx.py scripts/export_change_log.py scripts/update_financial_docx.py scripts/selftest_financial_docx_update.py
git commit -m "feat: add safe financial DOCX update workflow"
```

Expected: 两个 self-test 均打印 `passed`；compileall exit `0`。

---

### Task 4: 接入 Skill 并完成全量验证

**Files:**

- Modify: `SKILL.md:27-113`
- Modify: `.gitignore`

**Interfaces:**

- Skill 必须先产出并校验 bundle，再进行正式 DOCX 写回。
- 不新增插件、command、hook、MCP 或 Agent。

- [ ] **Step 1: 更新 Skill 工作流**

在 `SKILL.md` 中加入：

- 读取 `references/financial-analysis-bundle.md` 的条件；
- 确定性计算后组装 bundle；
- 写回前运行 bundle validator；
- 正式写回只能调用 `update_financial_docx.py`；
- 分析模式可只交付 bundle；
- 输出目录必须位于 Skill 仓库外。

Quick Start 使用：

```powershell
python -B scripts/validate_financial_analysis_bundle.py C:\tmp\financial_analysis_bundle.json --schema schemas\financial_analysis_bundle.schema.json --out C:\tmp\bundle_validation.json
python -B scripts/update_financial_docx.py C:\tmp\source.docx C:\tmp\financial_analysis_bundle.json --schema schemas\financial_analysis_bundle.schema.json --out-dir C:\tmp\financial-analysis-output
```

- [ ] **Step 2: 强化仓库隔离**

`.gitignore` 追加：

```gitignore
/outputs/
/work/
/runs/
```

不得忽略所有 `*.docx`。

- [ ] **Step 3: 运行全部自动化验证**

```powershell
python -B scripts/selftest_financial_analysis_bundle.py
python -B scripts/selftest_report_number_audit.py
python -B scripts/selftest_table_format_preservation.py
python -B scripts/selftest_financial_docx_update.py
python -B -m compileall -q scripts
python -B C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
```

Expected: 四个 self-test 均打印 `passed`；compileall exit `0`；Skill validator 输出 `Skill is valid!`。

- [ ] **Step 4: 仓库外真实模板回归**

只读输入：

```text
C:\Users\Administrator\Documents\Codex\2026-07-09\anthropics-financial-services-https-github-com\work\评审报告-基蛋生物2022_数据更新_WPS副本.docx
```

输出目录：

```text
C:\tmp\china-credit-financial-analysis-real-template
```

用 Task 1 合法 bundle 作为基础，改为：

```json
{
  "schema_version": "1.0",
  "company_name": "真实模板回归测试",
  "reporting_basis": "合并口径",
  "currency": "CNY",
  "unit": "万元",
  "periods": ["模板原有期间"],
  "sources": {},
  "financial_tables": {},
  "ratios": {},
  "risk_points": [],
  "pending_verification": [],
  "docx_write_plan": {
    "mode": "replace",
    "section_start": "财务分析",
    "analysis_anchor": "合并财务情况分析",
    "section_end": "行业分析",
    "analysis_markdown": "本次输出仅用于验证财务章节定位、格式保留、备份及校验流程。",
    "table_rows": {},
    "target_unit": "万元",
    "require_backup": true,
    "preserve_asset_liability_table": true,
    "change_shading": "FFF2CC",
    "output_filename": "真实模板_财务分析更新回归稿.docx"
  }
}
```

运行：

```powershell
python -B scripts/update_financial_docx.py "C:\Users\Administrator\Documents\Codex\2026-07-09\anthropics-financial-services-https-github-com\work\评审报告-基蛋生物2022_数据更新_WPS副本.docx" "C:\tmp\china-credit-financial-analysis-real-template\financial_analysis_bundle.json" --schema schemas\financial_analysis_bundle.schema.json --out-dir "C:\tmp\china-credit-financial-analysis-real-template"
```

Expected: backup、更新稿、数字审计、结构校验、修改说明和待核验清单全部存在；原始 DOCX SHA-256 不变。

- [ ] **Step 5: 渲染并视觉检查真实模板**

```powershell
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B 'C:\Users\Administrator\.codex\plugins\cache\openai-primary-runtime\documents\26.709.11516\skills\documents\render_docx.py' 'C:\tmp\china-credit-financial-analysis-real-template\真实模板_财务分析更新回归稿.docx' --output_dir 'C:\tmp\china-credit-financial-analysis-real-template\rendered' --emit_pdf
```

Expected: 产生逐页 PNG 和 PDF。检查财务章节标题、资产负债表、分析正文和下一章节无重叠、断裂、乱码或异常空白。渲染失败时记录具体错误，只声明结构验证结果。

- [ ] **Step 6: 检查仓库无业务产物并提交**

```powershell
git status --short
rg --files . | rg "backup-|更新稿|validation_result|number_audit|待核验清单|\.docx$"
git add SKILL.md .gitignore
git commit -m "docs: integrate bundle workflow into credit skill"
```

Expected: 提交前只出现预期源码变更；业务产物搜索无命中。

- [ ] **Step 7: 最终验证**

```powershell
git status --short
git log -5 --oneline
```

Expected: 工作区干净；最近提交包含 bundle、数字审计、DOCX 写回和 Skill 接入。

---

## Final Review Checklist

- [ ] bundle 是唯一新增跨模块公开接口。
- [ ] 标准库校验器与 Schema 字段一致，无第三方依赖。
- [ ] 正文只来自 `docx_write_plan.analysis_markdown`。
- [ ] 表格二维数据只来自 `docx_write_plan.table_rows`，数字可追溯。
- [ ] 原始 DOCX 未修改，备份先于写回。
- [ ] 锚点、数字审计或结构校验失败均返回非零。
- [ ] 表格 OOXML、字体、字号和底纹通过合成测试及真实模板回归。
- [ ] 业务运行产物位于仓库外。
- [ ] 未增加 Agent、commands、hooks、MCP、状态机或事件日志。
- [ ] `SKILL.md`、Schema、reference 和脚本接口一致。
