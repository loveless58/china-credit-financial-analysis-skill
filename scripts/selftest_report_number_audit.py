"""Self-test report-number auditing against the financial analysis bundle."""

from __future__ import annotations

import copy

from audit_report_numbers import audit_text
from selftest_financial_analysis_bundle import valid_bundle


def flatten_table_rows(bundle: dict) -> str:
    table_rows = bundle["docx_write_plan"]["table_rows"]
    return "\n".join(
        str(cell)
        for rows in table_rows.values()
        for row in rows
        for cell in row
    )


def main() -> None:
    bundle = valid_bundle()

    assert audit_text(
        bundle["docx_write_plan"]["analysis_markdown"],
        [bundle],
    ) == []

    findings = audit_text("截至2025年末，总资产为999.00万元。", [bundle])
    assert [item["number"] for item in findings] == ["999.00"]

    percentage_semantic_findings = audit_text(
        "总资产为120.0万元，资产负债率为50.0%。"
        "资产负债率为50.00万元，总资产为120.00%。",
        [bundle],
    )
    assert [item["number"] for item in percentage_semantic_findings] == [
        "50.00",
        "120.00%",
    ]

    quarterly_bundle = copy.deepcopy(bundle)
    quarterly_bundle["periods"] = ["2026Q1"]
    assert audit_text("截至2026年一季度，总资产为120.00万元。", [quarterly_bundle]) == []
    quarterly_year_findings = audit_text(
        "截至2027年一季度，总资产为120.00万元。", [quarterly_bundle]
    )
    assert [item["number"] for item in quarterly_year_findings] == ["2027"]

    noncanonical_period_bundle = copy.deepcopy(bundle)
    noncanonical_period_bundle["periods"] = ["2026forecast"]
    noncanonical_period_findings = audit_text(
        "截至2026年末，总资产为120.00万元。", [noncanonical_period_bundle]
    )
    assert [item["number"] for item in noncanonical_period_findings] == ["2026"]

    assert audit_text(flatten_table_rows(bundle), [bundle]) == []
    table_findings = audit_text(f"{flatten_table_rows(bundle)}\n资产总计为888.00万元。", [bundle])
    assert [item["number"] for item in table_findings] == ["888.00"]

    for surface, text in (
        ("analysis body", "资产负债表内金额为30万元。"),
        ("table_rows", f"{flatten_table_rows(bundle)}\n资产负债表内金额为30万元。"),
    ):
        contextual_table_findings = audit_text(text, [bundle])
        assert [item["number"] for item in contextual_table_findings] == [
            "30"
        ], f"table word authorized amount on {surface}"

    for amount in ("30", "999"):
        report_amount_findings = audit_text(f"报表{amount}万元差异。", [bundle])
        assert [item["number"] for item in report_amount_findings] == [
            amount
        ], f"report word authorized financial amount {amount}"

    structural_number_draft = (
        "1. 总资产分析\n"
        "表1：资产负债简表\n"
        "第1章 财务分析\n"
        "第2节 偿债能力\n"
        "第3项 风险提示"
    )
    assert audit_text(structural_number_draft, [bundle]) == []

    legacy_payload = {
        "metrics": {"total_assets": {"2025": {"value": "120.00"}}},
        "calculated_metrics": [{"value": "50.00", "display": "50.00%"}],
    }
    assert audit_text("2025年末总资产为120.00万元，资产负债率为50.00%。", [legacy_payload]) == []

    legacy_multiplier_payload = {
        "calculated_metrics": [
            {"value": "1.23", "display": "1.23倍"},
            {"value": "-", "display": " "},
            {"value": None, "display": "-"},
        ]
    }
    assert audit_text("指标为1.23。", [legacy_multiplier_payload]) == []

    non_numeric_display_payload = {
        "calculated_metrics": [{"value": "-", "display": "1.23倍"}]
    }
    non_numeric_findings = audit_text("指标为1.23。", [non_numeric_display_payload])
    assert [item["number"] for item in non_numeric_findings] == ["1.23"]

    signed_comma_payload = {
        "financial_tables": {
            "asset_liability": {
                "rows": [{"values": {"2025": {"value": "-1,200.00"}}}]
            }
        }
    }
    assert audit_text("2024年末金额为-1200.0。", [signed_comma_payload]) == []

    plan_only_number_bundle = copy.deepcopy(bundle)
    plan_only_number_bundle["docx_write_plan"]["analysis_markdown"] = "总资产为777.00万元。"
    plan_findings = audit_text(plan_only_number_bundle["docx_write_plan"]["analysis_markdown"], [plan_only_number_bundle])
    assert [item["number"] for item in plan_findings] == ["777.00"]

    regression_failures: list[str] = []
    blocked_status_values = {
        "source_missing": "771.00",
        "unit_missing": "772.00",
        "conflict": "773.00",
        "missing": "774.00",
        "llm_generated_blocked": "775.00",
    }
    for status, value in blocked_status_values.items():
        blocked_bundle = copy.deepcopy(bundle)
        blocked_bundle["financial_tables"]["asset_liability"]["rows"][0][
            "values"
        ]["2025"] = {
            "value": value,
            "status": status,
            "source_refs": [],
        }
        for surface, text in (
            ("analysis body", f"负债合计为{value}万元。"),
            ("table_rows", f"负债合计\n{value}"),
        ):
            actual = [
                item["number"] for item in audit_text(text, [blocked_bundle])
            ]
            if actual != [value]:
                regression_failures.append(
                    f"{status} authorized on {surface}: findings={actual!r}"
                )

    undeclared_year_findings = audit_text(
        "截至2026年末，总资产为120.00万元。", [bundle]
    )
    if [item["number"] for item in undeclared_year_findings] != ["2026"]:
        regression_failures.append(
            "bundle audit authorized undeclared contextual year 2026"
        )
    year_as_metric_bundle = copy.deepcopy(bundle)
    year_as_metric_bundle["financial_tables"]["asset_liability"]["rows"].append(
        {
            "metric": "coincidental_numeric_value",
            "label": "巧合数值",
            "values": {
                "2025": {
                    "value": "2026",
                    "status": "calculated",
                    "source_refs": [],
                }
            },
        }
    )
    year_as_metric_findings = audit_text(
        "截至2026年末，总资产为120.00万元。", [year_as_metric_bundle]
    )
    if [item["number"] for item in year_as_metric_findings] != ["2026"]:
        regression_failures.append(
            "bundle audit authorized undeclared year through a metric value"
        )
    assert audit_text("截至2025年末，总资产为120.00万元。", [bundle]) == []

    assert audit_text("截至2026年末，总资产为120.00万元。", [legacy_payload]) == []
    assert not regression_failures, "\n".join(regression_failures)

    print("selftest_report_number_audit: passed")


if __name__ == "__main__":
    main()
