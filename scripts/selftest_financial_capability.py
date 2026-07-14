#!/usr/bin/env python3
"""Self-test the runtime-neutral financial capability contract and runner."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUEST_SCHEMA = ROOT / "schemas" / "capability_request.schema.json"
RESULT_SCHEMA = ROOT / "schemas" / "capability_result.schema.json"
HEX64 = "a" * 64


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact(name: str) -> dict[str, object]:
    path = (ROOT.parent / "contract-test-artifacts" / name).resolve()
    return {"path": str(path), "sha256": HEX64, "size_bytes": 1}


def valid_request() -> dict:
    return {
        "schema_version": "1.0",
        "capability": "china-credit-financial-analysis",
        "request_id": "run-20260714-001",
        "operation": "update_docx",
        "inputs": {
            "source_docx": "input/report.docx",
            "financial_analysis_bundle": "input/financial_analysis_bundle.json",
            "source_docx_sha256": HEX64,
        },
        "artifact_directory": "output/run-20260714-001",
    }


def valid_result() -> dict:
    return {
        "schema_version": "1.0",
        "capability": "china-credit-financial-analysis",
        "request_id": "run-20260714-001",
        "operation": "update_docx",
        "status": "success",
        "started_at": "2026-07-14T12:00:00Z",
        "completed_at": "2026-07-14T12:00:01Z",
        "inputs": {
            "source_docx": artifact("source.docx"),
            "financial_analysis_bundle": artifact("input-bundle.json"),
        },
        "source_integrity": {
            "before_sha256": HEX64,
            "after_sha256": HEX64,
            "unchanged": True,
        },
        "artifacts": {
            "capability_request": artifact("capability_request.json"),
            "financial_analysis_bundle": artifact("financial_analysis_bundle.json"),
            "bundle_validation": artifact("bundle_validation.json"),
            "backup_docx": artifact("source.backup.docx"),
            "updated_docx": artifact("updated.docx"),
            "number_audit": artifact("number_audit.json"),
            "validation_result": artifact("validation_result.json"),
            "change_log": artifact("change_log.md"),
            "pending_verification": artifact("pending.md"),
        },
        "metrics": {"number_findings": 0, "docx_failed_checks": 0},
        "errors": [],
    }


def assert_contract_validation() -> None:
    try:
        from validate_capability_contract import validate_request, validate_result
    except ModuleNotFoundError as error:
        raise AssertionError("validate_capability_contract module is missing") from error

    assert REQUEST_SCHEMA.exists(), "request schema is missing"
    assert RESULT_SCHEMA.exists(), "result schema is missing"
    request_schema = load_json(REQUEST_SCHEMA)
    result_schema = load_json(RESULT_SCHEMA)

    assert validate_request(valid_request(), request_schema) == []

    request_with_unknown_field = valid_request()
    request_with_unknown_field["unexpected"] = True
    assert "request unknown field: unexpected" in validate_request(
        request_with_unknown_field, request_schema
    )

    request_with_bad_operation = valid_request()
    request_with_bad_operation["operation"] = "generate_everything"
    assert "operation must equal update_docx" in validate_request(
        request_with_bad_operation, request_schema
    )

    request_with_bad_hash = valid_request()
    request_with_bad_hash["inputs"]["source_docx_sha256"] = "not-a-hash"
    assert "inputs.source_docx_sha256 must be a SHA-256 hex string" in validate_request(
        request_with_bad_hash, request_schema
    )

    assert validate_result(valid_result(), result_schema) == []

    incomplete_success = valid_result()
    incomplete_success["artifacts"]["updated_docx"] = None
    assert "success result requires artifact: updated_docx" in validate_result(
        incomplete_success, result_schema
    )

    changed_source = valid_result()
    changed_source["source_integrity"]["unchanged"] = False
    assert "success result requires source_integrity.unchanged true" in validate_result(
        changed_source, result_schema
    )

    malformed_artifact = valid_result()
    malformed_artifact["artifacts"]["number_audit"]["sha256"] = "bad"
    assert "artifacts.number_audit.sha256 must be a SHA-256 hex string" in (
        validate_result(malformed_artifact, result_schema)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=["all", "contract"],
        default="all",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.case in {"all", "contract"}:
        assert_contract_validation()
    print("financial capability self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
