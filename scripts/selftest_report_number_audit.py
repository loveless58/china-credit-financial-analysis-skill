"""Self-test report-number auditing against the financial analysis bundle."""

from __future__ import annotations

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

    assert audit_text(flatten_table_rows(bundle), [bundle]) == []
    table_findings = audit_text(f"{flatten_table_rows(bundle)}\n资产总计为888.00万元。", [bundle])
    assert [item["number"] for item in table_findings] == ["888.00"]

    legacy_payload = {
        "metrics": {"total_assets": {"2025": {"value": "120.00"}}},
        "calculated_metrics": [{"value": "50.00", "display": "50.00%"}],
    }
    assert audit_text("2025年末总资产为120.00万元，资产负债率为50.00%。", [legacy_payload]) == []

    print("selftest_report_number_audit: passed")


if __name__ == "__main__":
    main()
