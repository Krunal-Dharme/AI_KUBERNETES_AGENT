"""Defensive normalization for SRE report fields from rule-based and LLM sources."""

from __future__ import annotations

from typing import Any

from loguru import logger

VALID_SEVERITIES = frozenset({"Critical", "High", "Medium", "Low", "Info"})

MAX_EVIDENCE_ITEMS = 12
MAX_COMMAND_ITEMS = 6
MAX_STRING_LENGTH = 2000


def _log_normalized(field: str, original_type: str, finding_id: str = "") -> None:
    suffix = f" (finding={finding_id})" if finding_id else ""
    logger.info("Normalized Finding.{} from {} to expected type{}", field, original_type, suffix)


def normalize_str(
    value: Any,
    default: str = "",
    field: str = "",
    finding_id: str = "",
    max_length: int = MAX_STRING_LENGTH,
) -> str:
    if value is None:
        return default

    if isinstance(value, str):
        text = value.strip()
        return text[:max_length] if text else default

    if isinstance(value, list):
        if field:
            _log_normalized(field, "list[str]", finding_id)
        parts = [normalize_str(item, field="", max_length=max_length) for item in value]
        joined = "; ".join(part for part in parts if part)
        return joined[:max_length] if joined else default

    if isinstance(value, dict):
        if field:
            _log_normalized(field, "dict", finding_id)
        return normalize_str(value.get("text") or value.get("message"), default, field, finding_id)

    if field:
        _log_normalized(field, type(value).__name__, finding_id)
    return str(value)[:max_length]


def normalize_str_list(
    value: Any,
    field: str = "",
    finding_id: str = "",
    max_items: int = MAX_COMMAND_ITEMS,
) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        text = value.strip()
        return [text[:MAX_STRING_LENGTH]] if text else []

    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            text = normalize_str(item, max_length=500)
            if text:
                items.append(text)
            if len(items) >= max_items:
                break
        return items

    if field:
        _log_normalized(field, type(value).__name__, finding_id)
    text = normalize_str(value, max_length=500)
    return [text] if text else []


def normalize_confidence(value: Any, default: int = 50, field: str = "", finding_id: str = "") -> int:
    if value is None:
        return default

    try:
        if isinstance(value, str):
            value = value.strip().rstrip("%")
        score = int(float(value))
    except (TypeError, ValueError):
        if field:
            _log_normalized(field, type(value).__name__, finding_id)
        return default

    if score < 0 or score > 100:
        if field:
            _log_normalized(field, f"out-of-range int({score})", finding_id)
    return max(0, min(100, score))


def normalize_severity(value: Any, default: str = "Medium", finding_id: str = "") -> str:
    if isinstance(value, str) and value in VALID_SEVERITIES:
        return value

    if isinstance(value, str):
        mapped = value.strip().capitalize()
        if mapped in VALID_SEVERITIES:
            return mapped

    _log_normalized("severity", type(value).__name__, finding_id)
    return default


def normalize_remediation(
    value: Any,
    default: dict[str, Any],
    finding_id: str = "",
) -> dict[str, Any]:
    if not isinstance(value, dict):
        if value is not None:
            _log_normalized("remediation", type(value).__name__, finding_id)
        return default

    return {
        "immediate_fix": normalize_str(
            value.get("immediate_fix"),
            default.get("immediate_fix", ""),
            "remediation.immediate_fix",
            finding_id,
        ),
        "verification_steps": normalize_str_list(
            value.get("verification_steps"),
            "remediation.verification_steps",
            finding_id,
        )
        or default.get("verification_steps", []),
        "rollback_steps": normalize_str_list(
            value.get("rollback_steps"),
            "remediation.rollback_steps",
            finding_id,
        )
        or default.get("rollback_steps", []),
    }


def normalize_finding_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a finding dict before Pydantic validation."""
    finding_id = normalize_str(raw.get("id"), "finding-unknown", "id")

    evidence = normalize_str_list(raw.get("evidence"), "evidence", finding_id, MAX_EVIDENCE_ITEMS)
    commands = normalize_str_list(
        raw.get("investigation_commands"),
        "investigation_commands",
        finding_id,
        MAX_COMMAND_ITEMS,
    )

    default_remediation = raw.get("_default_remediation", {})
    if not isinstance(default_remediation, dict):
        default_remediation = {}

    remediation_raw = raw.get("remediation", default_remediation)
    remediation = normalize_remediation(remediation_raw, default_remediation, finding_id)

    return {
        "id": finding_id,
        "title": normalize_str(raw.get("title"), "Untitled finding", "title", finding_id, 300),
        "severity": normalize_severity(raw.get("severity"), "Medium", finding_id),
        "category": normalize_str(raw.get("category"), "unknown", "category", finding_id, 100),
        "affected_resource": normalize_str(
            raw.get("affected_resource"), "unknown", "affected_resource", finding_id, 200
        ),
        "namespace": normalize_str(raw.get("namespace"), "default", "namespace", finding_id, 100),
        "resource_type": normalize_str(
            raw.get("resource_type"), "Resource", "resource_type", finding_id, 100
        ),
        "current_state": normalize_str(
            raw.get("current_state"), "Unknown", "current_state", finding_id, 500
        ),
        "evidence": evidence,
        "root_cause": normalize_str(raw.get("root_cause"), "", "root_cause", finding_id),
        "explanation": normalize_str(raw.get("explanation"), "", "explanation", finding_id),
        "investigation_commands": commands,
        "remediation": remediation,
        "confidence": normalize_confidence(raw.get("confidence"), 50, "confidence", finding_id),
        "confidence_reasoning": normalize_str(
            raw.get("confidence_reasoning"),
            "",
            "confidence_reasoning",
            finding_id,
        ),
    }


def normalize_diagnosis_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize top-level diagnosis fields before Pydantic validation."""
    normalized = dict(raw)
    for field in (
        "root_cause",
        "explanation",
        "fix",
        "kubectl_command",
        "prevention_recommendation",
        "confidence_reasoning",
        "executive_summary",
    ):
        if field in normalized:
            normalized[field] = normalize_str(normalized.get(field), "", field)

    normalized["confidence"] = normalize_confidence(normalized.get("confidence"), 50, "confidence")
    normalized["cluster_health_score"] = normalize_confidence(
        normalized.get("cluster_health_score"), 100, "cluster_health_score"
    )

    for list_field in (
        "validation_commands",
        "remediation_steps",
        "verification_steps",
        "rollback_commands",
    ):
        if list_field in normalized:
            normalized[list_field] = normalize_str_list(
                normalized.get(list_field), list_field, max_items=MAX_COMMAND_ITEMS
            )

    return normalized
