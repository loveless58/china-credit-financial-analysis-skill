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
REFERENCE = ROOT / "references" / "financial-analysis-bundle.md"


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
                        "metric": "total_liabilities",
                        "label": "负债合计",
                        "values": {
                            "2024": {
                                "value": "40.00",
                                "status": "verified",
                                "source_refs": ["annual_2025"],
                            },
                            "2025": {
                                "value": "60.00",
                                "status": "verified",
                                "source_refs": ["annual_2025"],
                            },
                        },
                    },
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


def bundle_with_risk_statement(statement: str) -> dict:
    bundle = valid_bundle()
    bundle["risk_points"][0]["statement"] = statement
    return bundle


def bundle_with_analysis_markdown(analysis_markdown: str) -> dict:
    bundle = valid_bundle()
    bundle["docx_write_plan"]["analysis_markdown"] = analysis_markdown
    return bundle


def run_case(
    name: str,
    bundle: dict,
    expected_code: int,
    directory: Path,
    expected_errors: list[str] | None = None,
) -> str | None:
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
    if expected_errors is not None and result.get("errors") != expected_errors:
        return f"{name}: expected errors {expected_errors!r}, got {result.get('errors')!r}"
    return None


def schema_phase_one_contract_failures() -> list[str]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    plan_properties = schema["properties"]["docx_write_plan"]["properties"]
    table_rows = plan_properties["table_rows"]
    failures: list[str] = []
    if table_rows.get("additionalProperties") is not False:
        failures.append("schema: table_rows must reject unknown table keys")
    if set(table_rows.get("properties", {})) != {"asset_liability"}:
        failures.append("schema: table_rows must expose only asset_liability")
    if plan_properties["preserve_asset_liability_table"].get("const") is not True:
        failures.append(
            "schema: preserve_asset_liability_table must be constant true"
        )
    return failures


def reference_contract_failures() -> list[str]:
    reference = REFERENCE.read_text(encoding="utf-8")
    required_statement = (
        "Phase 1 中，`(metric, period)` 在整个 `financial_tables` 范围内全局唯一"
    )
    if required_statement not in reference:
        return ["reference: financial_tables metric+period must be globally unique"]
    return []


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

    missing_ratio_input = valid_bundle()
    missing_ratio_input["ratios"]["asset_liability_ratio"]["inputs"][0][
        "metric"
    ] = "not_in_financial_tables"

    blocked_ratio_input = valid_bundle()
    blocked_ratio_input["financial_tables"]["asset_liability"]["rows"][0][
        "values"
    ]["2025"]["status"] = "conflict"

    undeclared_ratio_period = valid_bundle()
    undeclared_ratio_period["ratios"]["asset_liability_ratio"]["period"] = "2026"

    undeclared_input_period = valid_bundle()
    undeclared_input_period["ratios"]["asset_liability_ratio"]["inputs"][0][
        "period"
    ] = "2026"

    undeclared_table_period = valid_bundle()
    undeclared_table_period["financial_tables"]["asset_liability"]["rows"][0][
        "values"
    ]["2026"] = {
        "value": "61.00",
        "status": "verified",
        "source_refs": ["annual_2025"],
    }

    unsupported_table_rows = valid_bundle()
    unsupported_table_rows["docx_write_plan"]["table_rows"]["profit"] = [
        ["利润表", "2025"],
        ["净利润", "10.00"],
    ]

    preserve_false = valid_bundle()
    preserve_false["docx_write_plan"]["preserve_asset_liability_table"] = False

    empty_table_rows = valid_bundle()
    empty_table_rows["docx_write_plan"]["table_rows"] = {}

    duplicate_metric_period = valid_bundle()
    duplicate_metric_period["financial_tables"]["profit"] = {
        "rows": [
            {
                "metric": "total_assets",
                "label": "资产总计（重复）",
                "values": {
                    "2025": {
                        "value": "121.00",
                        "status": "verified",
                        "source_refs": ["annual_2025"],
                    }
                },
            }
        ]
    }

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
        ("forbidden_give_risk", bundle_with_risk_statement("建议给予授信。"), 1),
        (
            "forbidden_give_analysis",
            bundle_with_analysis_markdown("建议给予授信。"),
            1,
        ),
        (
            "forbidden_not_recommend_risk",
            bundle_with_risk_statement("不建议授信。"),
            1,
        ),
        (
            "forbidden_not_recommend_analysis",
            bundle_with_analysis_markdown("不建议授信。"),
            1,
        ),
        (
            "forbidden_amount_risk",
            bundle_with_risk_statement("建议授信100万元。"),
            1,
        ),
        (
            "forbidden_amount_analysis",
            bundle_with_analysis_markdown("建议授信100万元。"),
            1,
        ),
        (
            "allowed_existing_credit_balance_risk",
            bundle_with_risk_statement("公司现有银行授信余额100万元。"),
            0,
        ),
        (
            "allowed_credit_balance_change_analysis",
            bundle_with_analysis_markdown("公司授信余额较上年下降。"),
            0,
        ),
        (
            "forbidden_credit_recommendation_amount_risk",
            bundle_with_risk_statement("本次授信建议为100万元。"),
            1,
        ),
        (
            "forbidden_credit_recommendation_amount_analysis",
            bundle_with_analysis_markdown("本次授信建议为100万元。"),
            1,
        ),
        (
            "forbidden_credit_limit_decision_risk",
            bundle_with_risk_statement("公司授信额度确定为100万元。"),
            1,
        ),
        (
            "forbidden_credit_limit_decision_analysis",
            bundle_with_analysis_markdown("公司授信额度确定为100万元。"),
            1,
        ),
        (
            "allowed_credit_limit_fact_risk",
            bundle_with_risk_statement("截至报告期，公司银行授信额度为100万元。"),
            0,
        ),
        (
            "allowed_credit_limit_fact_analysis",
            bundle_with_analysis_markdown("截至报告期，公司银行授信额度为100万元。"),
            0,
        ),
        (
            "forbidden_approval_quota_without_credit_word",
            bundle_with_analysis_markdown("建议批复额度100万元。"),
            1,
        ),
        (
            "forbidden_approval_result_pass",
            bundle_with_analysis_markdown("审批结论：通过。"),
            1,
        ),
        (
            "allowed_cross_sentence_non_decision",
            bundle_with_analysis_markdown("公司授信余额下降。同意调整报表格式。"),
            0,
        ),
        (
            "allowed_cross_semicolon_negative_word",
            bundle_with_analysis_markdown("公司授信余额下降；不同意采用旧表格。"),
            0,
        ),
        (
            "allowed_cross_newline_pass_word",
            bundle_with_analysis_markdown("公司授信余额下降\n通过格式校验。"),
            0,
        ),
        (
            "allowed_cross_sentence_amount_word",
            bundle_with_analysis_markdown("公司授信余额为100万元。建议调整报表格式。"),
            0,
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
        ("missing_ratio_input", missing_ratio_input, 1),
        ("blocked_ratio_input", blocked_ratio_input, 1),
        ("undeclared_ratio_period", undeclared_ratio_period, 1),
        ("undeclared_input_period", undeclared_input_period, 1),
        ("undeclared_table_period", undeclared_table_period, 1),
        ("unsupported_table_rows", unsupported_table_rows, 1),
        ("preserve_false", preserve_false, 1),
        ("empty_table_rows", empty_table_rows, 0),
    ]

    exact_error_cases = [
        (
            "forbidden_approval_result_agree_risk",
            bundle_with_risk_statement("审批结论：同意。"),
            [
                "risk_points[0].statement contains forbidden conclusion categories: 同意"
            ],
        ),
        (
            "forbidden_approval_result_agree_analysis",
            bundle_with_analysis_markdown("审批结论：同意。"),
            [
                "docx_write_plan.analysis_markdown contains forbidden conclusion categories: 同意"
            ],
        ),
        (
            "forbidden_approval_result_veto_risk",
            bundle_with_risk_statement("审批结论：否决。"),
            [
                "risk_points[0].statement contains forbidden conclusion categories: 否决"
            ],
        ),
        (
            "forbidden_approval_result_veto_analysis",
            bundle_with_analysis_markdown("审批结论：否决。"),
            [
                "docx_write_plan.analysis_markdown contains forbidden conclusion categories: 否决"
            ],
        ),
        (
            "forbidden_approval_result_disagree_risk",
            bundle_with_risk_statement("审批结论：不同意。"),
            [
                "risk_points[0].statement contains forbidden conclusion categories: 否决"
            ],
        ),
        (
            "forbidden_approval_result_disagree_analysis",
            bundle_with_analysis_markdown("审批结论：不同意。"),
            [
                "docx_write_plan.analysis_markdown contains forbidden conclusion categories: 否决"
            ],
        ),
        (
            "forbidden_review_result_reject_risk",
            bundle_with_risk_statement("审查结论：拒绝。"),
            [
                "risk_points[0].statement contains forbidden conclusion categories: 否决"
            ],
        ),
        (
            "forbidden_review_result_reject_analysis",
            bundle_with_analysis_markdown("审查结论：拒绝。"),
            [
                "docx_write_plan.analysis_markdown contains forbidden conclusion categories: 否决"
            ],
        ),
        (
            "duplicate_metric_period",
            duplicate_metric_period,
            [
                "financial_tables duplicate (metric, period) key "
                "('total_assets', '2025'): financial_tables.profit.rows[0].values.2025 "
                "conflicts with financial_tables.asset_liability.rows[1].values.2025",
                "ratios.asset_liability_ratio.inputs[1] must reference a unique "
                "financial_tables value",
            ],
        ),
    ]

    with tempfile.TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        failures = schema_phase_one_contract_failures()
        failures.extend(reference_contract_failures())
        for name, bundle, expected_code in cases:
            failure = run_case(name, bundle, expected_code, directory)
            if failure:
                failures.append(failure)
        for name, bundle, expected_errors in exact_error_cases:
            failure = run_case(
                name,
                bundle,
                1,
                directory,
                expected_errors=expected_errors,
            )
            if failure:
                failures.append(failure)

    assert not failures, "\n".join(failures)

    print("financial analysis bundle self-test passed")


if __name__ == "__main__":
    main()
