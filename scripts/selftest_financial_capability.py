#!/usr/bin/env python3
"""Self-test the runtime-neutral financial capability contract and runner."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from selftest_financial_docx_update import (
    OUTPUT_FILENAME,
    make_source_docx,
    valid_bundle,
)


ROOT = Path(__file__).resolve().parent.parent
REQUEST_SCHEMA = ROOT / "schemas" / "capability_request.schema.json"
RESULT_SCHEMA = ROOT / "schemas" / "capability_result.schema.json"
RUNNER = ROOT / "scripts" / "run_financial_analysis_capability.py"
HEX64 = "a" * 64


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact(name: str) -> dict[str, object]:
    path = (ROOT.parent / "contract-test-artifacts" / name).resolve()
    return {"path": str(path), "sha256": HEX64, "size_bytes": 1}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def write_request(
    tmp_path: Path,
    bundle: dict,
    *,
    artifact_directory: str = "artifacts",
    expected_source_hash: str | None = None,
) -> tuple[Path, Path, Path]:
    source = tmp_path / "source.docx"
    bundle_path = tmp_path / "input-bundle.json"
    request_path = tmp_path / "capability_request.input.json"
    make_source_docx(source)
    bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    request = valid_request()
    request["request_id"] = f"selftest-{tmp_path.name}"
    request["inputs"] = {
        "source_docx": source.name,
        "financial_analysis_bundle": bundle_path.name,
    }
    if expected_source_hash is not None:
        request["inputs"]["source_docx_sha256"] = expected_source_hash
    request["artifact_directory"] = artifact_directory
    request_path.write_text(
        json.dumps(request, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return request_path, source, bundle_path


def run_capability(request_path: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-B", str(RUNNER), str(request_path)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def assert_artifact_descriptor(descriptor: dict[str, object]) -> Path:
    path = Path(str(descriptor["path"]))
    assert path.is_absolute()
    assert path.is_file(), path
    assert descriptor["sha256"] == sha256(path)
    assert descriptor["size_bytes"] == path.stat().st_size
    return path


def assert_runner_success() -> None:
    try:
        from validate_capability_contract import validate_result
    except ModuleNotFoundError as error:
        raise AssertionError("validate_capability_contract module is missing") from error

    assert RUNNER.exists(), "unified capability runner is missing"
    with tempfile.TemporaryDirectory(prefix="financial-capability-success-") as tmp:
        tmp_path = Path(tmp)
        request_path, source, input_bundle = write_request(tmp_path, valid_bundle())
        source_hash_before = sha256(source)
        process = run_capability(request_path)
        assert process.returncode == 0, process.stderr or process.stdout

        artifact_dir = tmp_path / "artifacts"
        result_path = artifact_dir / "capability_result.json"
        assert result_path.is_file()
        result = load_json(result_path)
        assert result["status"] == "success"
        assert validate_result(result, load_json(RESULT_SCHEMA)) == []
        assert result["source_integrity"] == {
            "before_sha256": source_hash_before,
            "after_sha256": source_hash_before,
            "unchanged": True,
        }
        assert result["metrics"] == {
            "number_findings": 0,
            "docx_failed_checks": 0,
        }
        assert result["errors"] == []
        assert sha256(source) == source_hash_before

        assert_artifact_descriptor(result["inputs"]["source_docx"])
        assert_artifact_descriptor(result["inputs"]["financial_analysis_bundle"])
        for descriptor in result["artifacts"].values():
            assert descriptor is not None
            assert_artifact_descriptor(descriptor)

        materialized_bundle = artifact_dir / "financial_analysis_bundle.json"
        assert load_json(materialized_bundle) == load_json(input_bundle)
        updated_docx = artifact_dir / OUTPUT_FILENAME
        assert updated_docx.is_file()
        assert Path(result["artifacts"]["updated_docx"]["path"]) == updated_docx.resolve()
        assert len(list(artifact_dir.glob("*.backup-*.docx"))) == 1

        stdout_summary = json.loads(process.stdout)
        assert stdout_summary == {
            "status": "success",
            "result": str(result_path.resolve()),
        }


def assert_runner_blocked_cases() -> None:
    from validate_capability_contract import validate_result

    assert RUNNER.exists(), "unified capability runner is missing"
    with tempfile.TemporaryDirectory(prefix="financial-capability-blocked-") as tmp:
        tmp_path = Path(tmp)

        invalid_bundle = valid_bundle()
        del invalid_bundle["company_name"]
        invalid_case = tmp_path / "invalid-bundle"
        invalid_case.mkdir()
        request_path, source, _ = write_request(invalid_case, invalid_bundle)
        source_hash = sha256(source)
        process = run_capability(request_path)
        assert process.returncode == 2, process.stderr or process.stdout
        result = load_json(invalid_case / "artifacts" / "capability_result.json")
        assert result["status"] == "blocked"
        assert validate_result(result, load_json(RESULT_SCHEMA)) == []
        assert result["errors"][0]["code"] == "BUNDLE_VALIDATION_FAILED"
        assert result["source_integrity"]["unchanged"] is True
        assert sha256(source) == source_hash
        assert result["artifacts"]["capability_request"] is not None
        assert result["artifacts"]["financial_analysis_bundle"] is not None
        assert result["artifacts"]["bundle_validation"] is not None
        for name in (
            "backup_docx",
            "updated_docx",
            "number_audit",
            "validation_result",
            "change_log",
            "pending_verification",
        ):
            assert result["artifacts"][name] is None
        bundle_validation = load_json(
            invalid_case / "artifacts" / "bundle_validation.json"
        )
        assert bundle_validation["valid"] is False
        assert bundle_validation["errors"]

        hash_case = tmp_path / "hash-mismatch"
        hash_case.mkdir()
        request_path, source, _ = write_request(
            hash_case,
            valid_bundle(),
            expected_source_hash="0" * 64,
        )
        source_hash = sha256(source)
        process = run_capability(request_path)
        assert process.returncode == 2, process.stderr or process.stdout
        result = load_json(hash_case / "artifacts" / "capability_result.json")
        assert result["status"] == "blocked"
        assert validate_result(result, load_json(RESULT_SCHEMA)) == []
        assert result["errors"][0]["code"] == "SOURCE_HASH_MISMATCH"
        assert result["artifacts"]["backup_docx"] is None
        assert result["artifacts"]["updated_docx"] is None
        assert sha256(source) == source_hash


def assert_runner_rejects_unsafe_artifact_directories() -> None:
    assert RUNNER.exists(), "unified capability runner is missing"
    with tempfile.TemporaryDirectory(prefix="financial-capability-paths-") as tmp:
        tmp_path = Path(tmp)

        nonempty_case = tmp_path / "nonempty"
        nonempty_case.mkdir()
        artifact_dir = nonempty_case / "artifacts"
        artifact_dir.mkdir()
        sentinel = artifact_dir / "do-not-touch.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        request_path, _, _ = write_request(nonempty_case, valid_bundle())
        process = run_capability(request_path)
        assert process.returncode == 2
        assert "artifact directory must be empty" in process.stderr
        assert sentinel.read_text(encoding="utf-8") == "preserve"
        assert not (artifact_dir / "capability_result.json").exists()

        forbidden_dir = ROOT / "forbidden-capability-artifacts"
        assert not forbidden_dir.exists(), forbidden_dir
        inside_repo_case = tmp_path / "inside-repo"
        inside_repo_case.mkdir()
        request_path, _, _ = write_request(
            inside_repo_case,
            valid_bundle(),
            artifact_directory=str(forbidden_dir),
        )
        process = run_capability(request_path)
        assert process.returncode == 2
        assert "outside the Skill repository" in process.stderr
        assert not forbidden_dir.exists()

        malformed_case = tmp_path / "malformed-request"
        malformed_case.mkdir()
        request_path, _, _ = write_request(malformed_case, valid_bundle())
        request = load_json(request_path)
        request["operation"] = "unsupported_operation"
        request_path.write_text(
            json.dumps(request, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        process = run_capability(request_path)
        assert process.returncode == 3
        assert "invalid capability request" in process.stderr
        assert not (malformed_case / "artifacts").exists()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=["all", "contract", "success", "blocked", "paths"],
        default="all",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.case in {"all", "contract"}:
        assert_contract_validation()
    if args.case in {"all", "success"}:
        assert_runner_success()
    if args.case in {"all", "blocked"}:
        assert_runner_blocked_cases()
    if args.case in {"all", "paths"}:
        assert_runner_rejects_unsafe_artifact_directories()
    print("financial capability self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
