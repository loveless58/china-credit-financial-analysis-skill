"""Self-test the financial analysis bundle validator through its public CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "scripts" / "validate_financial_analysis_bundle.py"
SCHEMA = ROOT / "schemas" / "financial_analysis_bundle.schema.json"


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
                "rows": [
                    {
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
                            },
                        },
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
                    {"metric": "total_assets", "period": "2025"},
                ],
            }
        },
        "risk_points": [
            {
                "category": "偿债能力",
                "statement": "需关注债务期限结构与经营现金流匹配情况。",
                "evidence_refs": ["annual_2025"],
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


def run_case(name: str, bundle: dict, expected_code: int, directory: Path) -> str | None:
    bundle_path = directory / f"{name}.json"
    result_path = directory / f"{name}.result.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(VALIDATOR),
            str(bundle_path),
            "--schema",
            str(SCHEMA),
            "--out",
            str(result_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    if completed.returncode != expected_code:
        return (
            f"{name}: expected exit {expected_code}, got {completed.returncode}; "
            f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
        )
    if not result_path.exists():
        return f"{name}: result JSON was not created"

    result = json.loads(result_path.read_text(encoding="utf-8"))
    if expected_code == 0 and result != {"valid": True, "errors": []}:
        return f"{name}: {result!r}"
    if expected_code != 0 and (result.get("valid") is not False or not result.get("errors")):
        return f"{name}: {result!r}"
    return None


def main() -> None:
    missing_metric = valid_bundle()
    del missing_metric["financial_tables"]["asset_liability"]["rows"][0]["metric"]

    missing_ratio_label_period = valid_bundle()
    del missing_ratio_label_period["ratios"]["asset_liability_ratio"]["label"]
    del missing_ratio_label_period["ratios"]["asset_liability_ratio"]["period"]

    missing_risk_category = valid_bundle()
    del missing_risk_category["risk_points"][0]["category"]

    empty_source_metadata = valid_bundle()
    empty_source_metadata["sources"]["annual_2025"]["name"] = ""

    illegal_status = valid_bundle()
    illegal_status["financial_tables"]["asset_liability"]["rows"][0]["values"]["2024"]["status"] = "not_allowed"

    unknown_source_field = valid_bundle()
    unknown_source_field["sources"]["annual_2025"]["unexpected"] = True

    unknown_table_field = valid_bundle()
    unknown_table_field["financial_tables"]["asset_liability"]["unexpected"] = True

    unknown_row_field = valid_bundle()
    unknown_row_field["financial_tables"]["asset_liability"]["rows"][0]["unexpected"] = True

    unknown_value_field = valid_bundle()
    unknown_value_field["financial_tables"]["asset_liability"]["rows"][0]["values"]["2024"]["unexpected"] = True

    unknown_ratio_field = valid_bundle()
    unknown_ratio_field["ratios"]["asset_liability_ratio"]["unexpected"] = True

    unknown_ratio_input_field = valid_bundle()
    unknown_ratio_input_field["ratios"]["asset_liability_ratio"]["inputs"][0]["unexpected"] = True

    unknown_risk_field = valid_bundle()
    unknown_risk_field["risk_points"][0]["unexpected"] = True

    unknown_pending_field = valid_bundle()
    unknown_pending_field["pending_verification"] = [
        {"issue": "待补充审计报告", "status": "source_missing", "unexpected": True}
    ]

    cases = [
        ("valid", valid_bundle(), 0),
        ("missing_unit", {**valid_bundle(), "unit": ""}, 1),
        ("unknown_top_level", {**valid_bundle(), "unexpected": True}, 1),
        (
            "forbidden_conclusion",
            {
                **valid_bundle(),
                "risk_points": [
                    {
                        "category": "结论",
                        "statement": "建议同意授信。",
                        "evidence_refs": ["annual_2025"],
                    }
                ],
            },
            1,
        ),
        (
            "forbidden_denial",
            {
                **valid_bundle(),
                "risk_points": [
                    {
                        "category": "结论",
                        "statement": "建议不予授信。",
                        "evidence_refs": ["annual_2025"],
                    }
                ],
            },
            1,
        ),
        (
            "forbidden_pass",
            {
                **valid_bundle(),
                "docx_write_plan": {
                    **valid_bundle()["docx_write_plan"],
                    "analysis_markdown": "建议通过授信审批。",
                },
            },
            1,
        ),
        (
            "forbidden_quota",
            {
                **valid_bundle(),
                "docx_write_plan": {
                    **valid_bundle()["docx_write_plan"],
                    "analysis_markdown": "建议授信额度为100万元。",
                },
            },
            1,
        ),
        ("empty_source_metadata", empty_source_metadata, 1),
        ("missing_metric", missing_metric, 1),
        ("missing_ratio_label_period", missing_ratio_label_period, 1),
        ("missing_risk_category", missing_risk_category, 1),
        ("illegal_status", illegal_status, 1),
        ("unknown_source_field", unknown_source_field, 1),
        ("unknown_table_field", unknown_table_field, 1),
        ("unknown_row_field", unknown_row_field, 1),
        ("unknown_value_field", unknown_value_field, 1),
        ("unknown_ratio_field", unknown_ratio_field, 1),
        ("unknown_ratio_input_field", unknown_ratio_input_field, 1),
        ("unknown_risk_field", unknown_risk_field, 1),
        ("unknown_pending_field", unknown_pending_field, 1),
    ]

    with tempfile.TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        failures: list[str] = []
        for name, bundle, expected_code in cases:
            failure = run_case(name, bundle, expected_code, directory)
            if failure:
                failures.append(failure)

    assert not failures, "\n".join(failures)

    print("financial analysis bundle self-test passed")


if __name__ == "__main__":
    main()
