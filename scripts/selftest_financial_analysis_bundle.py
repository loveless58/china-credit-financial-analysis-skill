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


def run_case(name: str, bundle: dict, expected_code: int, directory: Path) -> None:
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

    assert completed.returncode == expected_code, (
        f"{name}: expected exit {expected_code}, got {completed.returncode}; "
        f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
    )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    if expected_code == 0:
        assert result == {"valid": True, "errors": []}, f"{name}: {result!r}"
    else:
        assert result["valid"] is False, f"{name}: {result!r}"
        assert result["errors"], f"{name}: {result!r}"


def main() -> None:
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
    ]

    with tempfile.TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        for name, bundle, expected_code in cases:
            run_case(name, bundle, expected_code, directory)

    print("financial analysis bundle self-test passed")


if __name__ == "__main__":
    main()
