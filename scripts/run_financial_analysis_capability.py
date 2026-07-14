#!/usr/bin/env python3
"""Run the financial-analysis DOCX capability from a stable file contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from update_financial_docx import (
    UpdateBlocked,
    UpdateFailed,
    reject_out_dir_inside_skill_repo,
    update_financial_docx,
)
from validate_capability_contract import (
    ARTIFACT_NAMES,
    validate_request,
    validate_result,
)
from validate_financial_analysis_bundle import validate_bundle


ROOT = Path(__file__).resolve().parent.parent
REQUEST_SCHEMA = ROOT / "schemas" / "capability_request.schema.json"
RESULT_SCHEMA = ROOT / "schemas" / "capability_result.schema.json"
BUNDLE_SCHEMA = ROOT / "schemas" / "financial_analysis_bundle.schema.json"
RESULT_FILENAME = "capability_result.json"


class PreflightError(RuntimeError):
    """Raised when no trustworthy artifact directory is available."""

    def __init__(self, message: str, exit_code: int = 3) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as file_handle:
        return json.load(file_handle)


def write_json(path: Path, payload: object) -> Path:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_descriptor(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.is_file():
        return None
    resolved = path.resolve()
    return {
        "path": str(resolved),
        "sha256": sha256(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def resolve_from_request(request_path: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = request_path.parent / path
    return path.resolve()


def prepare_artifact_directory(path: Path) -> Path:
    try:
        reject_out_dir_inside_skill_repo(path)
    except UpdateBlocked as error:
        raise PreflightError(str(error), exit_code=2) from error
    if path.exists():
        if not path.is_dir():
            raise PreflightError(
                "artifact directory path is not a directory", exit_code=2
            )
        if any(path.iterdir()):
            raise PreflightError("artifact directory must be empty", exit_code=2)
    else:
        path.mkdir(parents=True)
    return path.resolve()


def normalized_request(
    request: dict[str, Any],
    source_docx: Path,
    bundle_path: Path,
    artifact_dir: Path,
) -> dict[str, Any]:
    normalized = {
        "schema_version": request["schema_version"],
        "capability": request["capability"],
        "request_id": request["request_id"],
        "operation": request["operation"],
        "inputs": {
            "source_docx": str(source_docx),
            "financial_analysis_bundle": str(bundle_path),
        },
        "artifact_directory": str(artifact_dir),
    }
    expected_hash = request["inputs"].get("source_docx_sha256")
    if expected_hash is not None:
        normalized["inputs"]["source_docx_sha256"] = expected_hash.lower()
    return normalized


def empty_artifacts() -> dict[str, dict[str, object] | None]:
    return {name: None for name in ARTIFACT_NAMES}


def existing_output_paths(
    artifact_dir: Path,
    bundle: dict[str, Any] | None,
    updater_result: dict[str, str] | None,
    request_copy: Path,
    bundle_copy: Path,
    bundle_validation: Path,
) -> dict[str, Path | None]:
    paths: dict[str, Path | None] = {
        "capability_request": request_copy,
        "financial_analysis_bundle": bundle_copy,
        "bundle_validation": bundle_validation,
        "backup_docx": None,
        "updated_docx": None,
        "number_audit": artifact_dir / "number_audit.json",
        "validation_result": artifact_dir / "validation_result.json",
        "change_log": artifact_dir / "change_log.md",
        "pending_verification": artifact_dir / "待核验清单.md",
    }
    if updater_result:
        paths["backup_docx"] = Path(updater_result["backup"])
        paths["updated_docx"] = Path(updater_result["output"])
    else:
        backups = list(artifact_dir.glob("*.backup-*.docx"))
        if len(backups) == 1:
            paths["backup_docx"] = backups[0]
        if isinstance(bundle, dict):
            plan = bundle.get("docx_write_plan")
            if isinstance(plan, dict) and isinstance(plan.get("output_filename"), str):
                paths["updated_docx"] = artifact_dir / plan["output_filename"]
    return paths


def read_metrics(artifact_dir: Path) -> dict[str, int | None]:
    number_findings: int | None = None
    audit_path = artifact_dir / "number_audit.json"
    if audit_path.is_file():
        try:
            findings = load_json(audit_path).get("findings")
            if isinstance(findings, list):
                number_findings = len(findings)
        except (OSError, json.JSONDecodeError, AttributeError):
            pass

    docx_failed_checks: int | None = None
    validation_path = artifact_dir / "validation_result.json"
    if validation_path.is_file():
        try:
            failed = load_json(validation_path).get("failed")
            if isinstance(failed, list):
                docx_failed_checks = len(failed)
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
    return {
        "number_findings": number_findings,
        "docx_failed_checks": docx_failed_checks,
    }


def error_item(code: str, message: str, details: list[Any] | None = None) -> dict:
    return {
        "code": code,
        "message": message,
        "details": details or [],
    }


def build_result(
    *,
    request: dict[str, Any],
    status: str,
    started_at: str,
    source_docx: Path,
    source_input: dict[str, object] | None,
    bundle_input: dict[str, object] | None,
    source_hash_before: str | None,
    artifact_paths: dict[str, Path | None],
    metrics: dict[str, int | None],
    errors: list[dict],
) -> dict[str, Any]:
    source_hash_after = sha256(source_docx) if source_docx.is_file() else None
    source_unchanged = (
        source_hash_before == source_hash_after
        if source_hash_before is not None and source_hash_after is not None
        else None
    )
    artifacts = empty_artifacts()
    for name in ARTIFACT_NAMES:
        artifacts[name] = artifact_descriptor(artifact_paths.get(name))
    return {
        "schema_version": "1.0",
        "capability": request["capability"],
        "request_id": request["request_id"],
        "operation": request["operation"],
        "status": status,
        "started_at": started_at,
        "completed_at": utc_now(),
        "inputs": {
            "source_docx": source_input,
            "financial_analysis_bundle": bundle_input,
        },
        "source_integrity": {
            "before_sha256": source_hash_before,
            "after_sha256": source_hash_after,
            "unchanged": source_unchanged,
        },
        "artifacts": artifacts,
        "metrics": metrics,
        "errors": errors,
    }


def write_result(
    result_path: Path,
    result: dict[str, Any],
    result_schema: dict[str, Any],
) -> None:
    contract_errors = validate_result(result, result_schema)
    if contract_errors:
        raise RuntimeError(
            "internal capability result contract violation: " + "; ".join(contract_errors)
        )
    write_json(result_path, result)


def run(request_path: Path) -> tuple[int, Path]:
    started_at = utc_now()
    request_path = request_path.resolve()
    request_schema = load_json(REQUEST_SCHEMA)
    result_schema = load_json(RESULT_SCHEMA)
    request = load_json(request_path)
    request_errors = validate_request(request, request_schema)
    if request_errors:
        raise PreflightError("invalid capability request: " + "; ".join(request_errors))

    source_docx = resolve_from_request(request_path, request["inputs"]["source_docx"])
    input_bundle = resolve_from_request(
        request_path, request["inputs"]["financial_analysis_bundle"]
    )
    artifact_dir = resolve_from_request(request_path, request["artifact_directory"])
    artifact_dir = prepare_artifact_directory(artifact_dir)
    request_copy = artifact_dir / "capability_request.json"
    bundle_copy = artifact_dir / "financial_analysis_bundle.json"
    bundle_validation_path = artifact_dir / "bundle_validation.json"
    result_path = artifact_dir / RESULT_FILENAME

    normalized = normalized_request(
        request, source_docx, input_bundle, artifact_dir
    )
    write_json(request_copy, normalized)

    source_hash_before: str | None = None
    source_input: dict[str, object] | None = None
    bundle_input: dict[str, object] | None = None
    bundle: dict[str, Any] | None = None
    updater_result: dict[str, str] | None = None
    status = "failed"
    errors: list[dict] = []

    try:
        source_input = artifact_descriptor(source_docx)
        bundle_input = artifact_descriptor(input_bundle)
        missing = [
            str(path)
            for path, descriptor in (
                (source_docx, source_input),
                (input_bundle, bundle_input),
            )
            if descriptor is None
        ]
        if missing:
            raise UpdateBlocked("input file is missing", missing)

        source_hash_before = str(source_input["sha256"])
        shutil.copyfile(input_bundle, bundle_copy)
        if sha256(bundle_copy) != bundle_input["sha256"]:
            raise UpdateBlocked(
                "input financial_analysis_bundle changed during materialization",
                [str(input_bundle)],
            )
        try:
            loaded_bundle = load_json(bundle_copy)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"financial_analysis_bundle cannot be parsed: {error}") from error
        if not isinstance(loaded_bundle, dict):
            bundle = None
            bundle_errors = ["bundle must be a JSON object"]
        else:
            bundle = loaded_bundle
            bundle_errors = validate_bundle(bundle, load_json(BUNDLE_SCHEMA))
        write_json(
            bundle_validation_path,
            {"valid": not bundle_errors, "errors": bundle_errors},
        )

        expected_hash = request["inputs"].get("source_docx_sha256")
        if expected_hash is not None and source_hash_before.lower() != expected_hash.lower():
            raise UpdateBlocked(
                "source DOCX SHA-256 does not match capability request",
                [
                    f"expected={expected_hash.lower()}",
                    f"actual={source_hash_before.lower()}",
                ],
            )
        if bundle_errors:
            raise UpdateBlocked("financial_analysis_bundle validation failed", bundle_errors)

        updater_result = update_financial_docx(
            source_docx=source_docx,
            bundle_path=bundle_copy,
            schema_path=BUNDLE_SCHEMA,
            out_dir=artifact_dir,
        )
        status = "success"
    except UpdateBlocked as error:
        status = "blocked"
        if str(error) == "financial_analysis_bundle validation failed":
            code = "BUNDLE_VALIDATION_FAILED"
        elif str(error) == "source DOCX SHA-256 does not match capability request":
            code = "SOURCE_HASH_MISMATCH"
        elif str(error) == "input file is missing":
            code = "INPUT_FILE_MISSING"
        elif str(error) == "input financial_analysis_bundle changed during materialization":
            code = "INPUT_BUNDLE_CHANGED"
        elif str(error) == "number audit failed":
            code = "NUMBER_AUDIT_FAILED"
        else:
            code = "DOCX_UPDATE_BLOCKED"
        errors = [error_item(code, str(error), list(error.details))]
    except UpdateFailed as error:
        status = "blocked"
        errors = [error_item("DOCX_VALIDATION_FAILED", str(error), list(error.details))]
    except Exception as error:
        status = "failed"
        errors = [error_item("EXECUTION_FAILED", str(error))]

    artifact_paths = existing_output_paths(
        artifact_dir,
        bundle,
        updater_result,
        request_copy,
        bundle_copy,
        bundle_validation_path,
    )
    metrics = read_metrics(artifact_dir)
    result = build_result(
        request=request,
        status=status,
        started_at=started_at,
        source_docx=source_docx,
        source_input=source_input,
        bundle_input=bundle_input,
        source_hash_before=source_hash_before,
        artifact_paths=artifact_paths,
        metrics=metrics,
        errors=errors,
    )
    if status == "success" and result["source_integrity"]["unchanged"] is not True:
        result["status"] = "failed"
        result["errors"] = [
            error_item(
                "SOURCE_MODIFIED",
                "source DOCX changed during capability execution",
            )
        ]
        status = "failed"
    write_result(result_path, result, result_schema)
    return (0 if status == "success" else 2 if status == "blocked" else 3), result_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, help="path to capability_request.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        exit_code, result_path = run(args.request)
    except (OSError, json.JSONDecodeError, PreflightError) as error:
        print(str(error), file=sys.stderr)
        return error.exit_code if isinstance(error, PreflightError) else 3
    print(
        json.dumps(
            {
                "status": load_json(result_path)["status"],
                "result": str(result_path.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
