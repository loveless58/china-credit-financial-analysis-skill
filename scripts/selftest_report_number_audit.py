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

    assert audit_text(flatten_table_rows(bundle), [bundle]) == []
    table_findings = audit_text(f"{flatten_table_rows(bundle)}\n资产总计为888.00万元。", [bundle])
    assert [item["number"] for item in table_findings] == ["888.00"]

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

    print("selftest_report_number_audit: passed")


if __name__ == "__main__":
    main()
