#!/usr/bin/env python3
"""Validate capability request and result payloads without runtime dependencies."""

from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath
from typing import Any


HEX64 = re.compile(r"^[0-9A-Fa-f]{64}$")
REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
UTC_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
CAPABILITY = "china-credit-financial-analysis"
OPERATION = "update_docx"
ARTIFACT_NAMES = (
    "capability_request",
    "financial_analysis_bundle",
    "bundle_validation",
    "backup_docx",
    "updated_docx",
    "number_audit",
    "validation_result",
    "change_log",
    "pending_verification",
)


def object_contract_errors(
    value: Any,
    schema: dict[str, Any],
    prefix: str,
) -> list[str]:
    if not isinstance(value, dict):
        return [f"{prefix} must be an object"]
    required = set(schema.get("required", []))
    properties = set(schema.get("properties", {}))
    errors = [
        f"{prefix} missing field: {name}" for name in sorted(required - value.keys())
    ]
    if schema.get("additionalProperties") is False:
        errors.extend(
            f"{prefix} unknown field: {name}"
            for name in sorted(value.keys() - properties)
        )
    return errors


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def absolute_path_string(value: Any) -> bool:
    if not non_empty_string(value):
        return False
    return Path(value).is_absolute() or PureWindowsPath(value).is_absolute()


def validate_request(payload: Any, schema: dict[str, Any]) -> list[str]:
    errors = object_contract_errors(payload, schema, "request")
    if not isinstance(payload, dict):
        return errors

    if payload.get("schema_version") != "1.0":
        errors.append("schema_version must equal 1.0")
    if payload.get("capability") != CAPABILITY:
        errors.append(f"capability must equal {CAPABILITY}")
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
        errors.append("request_id must use 1-128 letters, digits, dot, underscore, or hyphen")
    if payload.get("operation") != OPERATION:
        errors.append(f"operation must equal {OPERATION}")
    if not non_empty_string(payload.get("artifact_directory")):
        errors.append("artifact_directory must be a non-empty path string")

    inputs_schema = schema.get("properties", {}).get("inputs", {})
    inputs = payload.get("inputs")
    errors.extend(object_contract_errors(inputs, inputs_schema, "inputs"))
    if isinstance(inputs, dict):
        for name in ("source_docx", "financial_analysis_bundle"):
            if not non_empty_string(inputs.get(name)):
                errors.append(f"inputs.{name} must be a non-empty path string")
        expected_hash = inputs.get("source_docx_sha256")
        if expected_hash is not None and (
            not isinstance(expected_hash, str) or not HEX64.fullmatch(expected_hash)
        ):
            errors.append("inputs.source_docx_sha256 must be a SHA-256 hex string")
    return errors


def validate_artifact(value: Any, prefix: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, dict):
        return [f"{prefix} must be an artifact object or null"]

    errors: list[str] = []
    expected = {"path", "sha256", "size_bytes"}
    errors.extend(
        f"{prefix} missing field: {name}" for name in sorted(expected - value.keys())
    )
    errors.extend(
        f"{prefix} unknown field: {name}" for name in sorted(value.keys() - expected)
    )
    if not absolute_path_string(value.get("path")):
        errors.append(f"{prefix}.path must be an absolute path")
    digest = value.get("sha256")
    if not isinstance(digest, str) or not HEX64.fullmatch(digest):
        errors.append(f"{prefix}.sha256 must be a SHA-256 hex string")
    size = value.get("size_bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        errors.append(f"{prefix}.size_bytes must be a non-negative integer")
    return errors


def validate_result(payload: Any, schema: dict[str, Any]) -> list[str]:
    errors = object_contract_errors(payload, schema, "result")
    if not isinstance(payload, dict):
        return errors

    if payload.get("schema_version") != "1.0":
        errors.append("schema_version must equal 1.0")
    if payload.get("capability") != CAPABILITY:
        errors.append(f"capability must equal {CAPABILITY}")
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
        errors.append("request_id must use 1-128 letters, digits, dot, underscore, or hyphen")
    if payload.get("operation") != OPERATION:
        errors.append(f"operation must equal {OPERATION}")
    status = payload.get("status")
    if status not in {"success", "blocked", "failed"}:
        errors.append("status must be success, blocked, or failed")
    for name in ("started_at", "completed_at"):
        value = payload.get(name)
        if not isinstance(value, str) or not UTC_TIMESTAMP.fullmatch(value):
            errors.append(f"{name} must be a UTC ISO-8601 timestamp")

    inputs_schema = schema.get("properties", {}).get("inputs", {})
    inputs = payload.get("inputs")
    errors.extend(object_contract_errors(inputs, inputs_schema, "inputs"))
    if isinstance(inputs, dict):
        for name in ("source_docx", "financial_analysis_bundle"):
            errors.extend(validate_artifact(inputs.get(name), f"inputs.{name}"))

    integrity_schema = schema.get("properties", {}).get("source_integrity", {})
    integrity = payload.get("source_integrity")
    errors.extend(object_contract_errors(integrity, integrity_schema, "source_integrity"))
    if isinstance(integrity, dict):
        for name in ("before_sha256", "after_sha256"):
            value = integrity.get(name)
            if value is not None and (
                not isinstance(value, str) or not HEX64.fullmatch(value)
            ):
                errors.append(f"source_integrity.{name} must be a SHA-256 hex string or null")
        if integrity.get("unchanged") not in {True, False, None}:
            errors.append("source_integrity.unchanged must be boolean or null")

    artifacts_schema = schema.get("properties", {}).get("artifacts", {})
    artifacts = payload.get("artifacts")
    errors.extend(object_contract_errors(artifacts, artifacts_schema, "artifacts"))
    if isinstance(artifacts, dict):
        for name in ARTIFACT_NAMES:
            errors.extend(validate_artifact(artifacts.get(name), f"artifacts.{name}"))

    metrics_schema = schema.get("properties", {}).get("metrics", {})
    metrics = payload.get("metrics")
    errors.extend(object_contract_errors(metrics, metrics_schema, "metrics"))
    if isinstance(metrics, dict):
        for name in ("number_findings", "docx_failed_checks"):
            value = metrics.get(name)
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0
            ):
                errors.append(f"metrics.{name} must be a non-negative integer or null")

    error_items = payload.get("errors")
    if not isinstance(error_items, list):
        errors.append("errors must be an array")
    else:
        for index, item in enumerate(error_items):
            prefix = f"errors[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            if set(item) != {"code", "message", "details"}:
                errors.append(f"{prefix} must contain only code, message, and details")
            if not isinstance(item.get("code"), str) or not re.fullmatch(
                r"^[A-Z][A-Z0-9_]*$", item.get("code", "")
            ):
                errors.append(f"{prefix}.code must be an uppercase error code")
            if not non_empty_string(item.get("message")):
                errors.append(f"{prefix}.message must be non-empty")
            if not isinstance(item.get("details"), list):
                errors.append(f"{prefix}.details must be an array")

    if status == "success":
        if isinstance(artifacts, dict):
            for name in ARTIFACT_NAMES:
                if artifacts.get(name) is None:
                    errors.append(f"success result requires artifact: {name}")
        if not isinstance(integrity, dict) or integrity.get("unchanged") is not True:
            errors.append("success result requires source_integrity.unchanged true")
        if isinstance(metrics, dict):
            if metrics.get("number_findings") != 0:
                errors.append("success result requires zero number findings")
            if metrics.get("docx_failed_checks") != 0:
                errors.append("success result requires zero DOCX failed checks")
        if error_items != []:
            errors.append("success result requires an empty errors array")
    elif status in {"blocked", "failed"} and isinstance(error_items, list) and not error_items:
        errors.append(f"{status} result requires at least one error")

    return errors
