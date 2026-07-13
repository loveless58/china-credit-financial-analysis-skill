# financial_analysis_bundle 1.0

`financial_analysis_bundle.json` 是第一阶段唯一新增的跨模块公开接口。文件必须为 UTF-8 JSON 对象，且 `schema_version` 固定为 `"1.0"`。后续数字审计和 DOCX 写回只能依赖这个 bundle，不得依赖 `calculated_metrics.json` 等临时文件。

## 顶层字段

| 字段 | 类型 | 约束与语义 |
| --- | --- | --- |
| `schema_version` | string | 固定为 `"1.0"`。 |
| `company_name` | string | 非空公司名称。 |
| `reporting_basis` | string | 非空报表口径，例如 `"合并口径"`。 |
| `currency` | string | 非空币种代码或名称。 |
| `unit` | string | 非空金额单位。 |
| `periods` | string[] | 非空期间数组，每项为非空字符串。 |
| `sources` | object | 以稳定来源 ID 为键的来源登记表；每项有 `name`、`type`、`file`。 |
| `financial_tables` | object | 分析层财务表，按表名保存 `rows`；每个期间值有 `value`、`status`、`source_refs`。 |
| `ratios` | object | 分析层比率；每项有公式、值、展示值、`calculated` 状态和非空输入。 |
| `risk_points` | array | 风险关注点；每项有非空 `statement` 与有效、非空 `evidence_refs`。不得包含授信审批、额度、通过或否决结论。 |
| `pending_verification` | array | 待核验清单及修改说明的直接输入；每项有非空 `issue` 和非正文状态。 |
| `docx_write_plan` | object | DOCX 写回计划，字段集合固定，未知字段无效。 |

## 状态与正文准入

允许的状态为 `verified`、`calculated`、`source_missing`、`unit_missing`、`conflict`、`missing`、`llm_generated_blocked`。只有 `verified` 与 `calculated` 可作为 `analysis_markdown` 正文的数字准入状态；其余状态必须留在 `pending_verification` 或对应的数据项中，不能作为已确认正文事实。

`verified` 财务表数据必须引用 `sources` 中存在的来源 ID。`pending_verification.status` 只能使用非正文状态。`risk_points.statement` 和 `docx_write_plan.analysis_markdown` 使用同一组具名禁令模式，拦截四类业务结论：同意（如“建议同意授信”）、否决（如“建议不予授信”）、通过（如“建议通过授信审批”）和额度（如“建议授信额度为100万元”）。

## DOCX 写回计划

`docx_write_plan` 必须包含 `mode`、`section_start`、`analysis_anchor`、`section_end`、`analysis_markdown`、`table_rows`、`target_unit`、`require_backup`、`preserve_asset_liability_table`、`change_shading`、`output_filename`。

- `mode` 只能是 `insert` 或 `replace`。
- `require_backup` 必须为 `true`；`change_shading` 为六位十六进制颜色；`output_filename` 必须以 `.docx` 结尾。
- `analysis_markdown` 是 DOCX 正文的唯一来源。
- `table_rows` 是模板写回所需的二维矩阵，不替代分析层 `financial_tables`，也不应被下游当作计算或审计依据。

## 完整合法示例

```json
{
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
      "file": "source/annual_2025.pdf"
    }
  },
  "financial_tables": {
    "asset_liability": {
      "rows": [
        {
          "metric": "total_assets",
          "label": "资产总计",
          "values": {
            "2024": {
              "value": "100.00",
              "status": "verified",
              "source_refs": ["annual_2025"]
            },
            "2025": {
              "value": "120.00",
              "status": "verified",
              "source_refs": ["annual_2025"]
            }
          }
        }
      ]
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
        {"metric": "total_assets", "period": "2025"}
      ]
    }
  },
  "risk_points": [
    {
      "category": "偿债能力",
      "statement": "需关注债务期限结构与经营现金流匹配情况。",
      "evidence_refs": ["annual_2025"]
    }
  ],
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
        ["资产总计", "100.00", "120.00"]
      ]
    },
    "target_unit": "万元",
    "require_backup": true,
    "preserve_asset_liability_table": true,
    "change_shading": "FFF2CC",
    "output_filename": "某测试公司_财务分析更新稿.docx"
  }
}
```
