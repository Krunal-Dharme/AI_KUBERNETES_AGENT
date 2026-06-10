"""Assemble the final SRE investigation report from evidence and AI enrichment."""

from __future__ import annotations

from typing import Any

from loguru import logger
from pydantic import ValidationError

from models.investigation import Diagnosis, Finding, Remediation, TimelineStep
from services.finding_builder import build_findings_from_investigation
from services.health_summary import build_cluster_health_summary, calculate_cluster_health_score
from services.report_normalizer import normalize_diagnosis_payload, normalize_finding_payload, normalize_str


def _default_remediation(finding: dict[str, Any]) -> dict[str, Any]:
    category = finding.get("category", "")
    resource = finding.get("affected_resource", "")
    namespace = finding.get("namespace", "default")
    state = finding.get("current_state", "")

    if category == "pod" and "ImagePull" in state:
        return {
            "immediate_fix": "Update the container image reference to a valid, accessible image tag in the deployment spec.",
            "verification_steps": [
                f"kubectl rollout status deployment/{resource} -n {namespace}"
                if namespace != "cluster"
                else f"kubectl get pod {resource} -n {namespace}",
                f"kubectl get pods -n {namespace}",
            ],
            "rollback_steps": [
                f"kubectl rollout undo deployment/{resource} -n {namespace}"
                if namespace != "cluster"
                else f"kubectl delete pod {resource} -n {namespace}",
            ],
        }

    if category == "pod" and "CrashLoop" in state:
        return {
            "immediate_fix": "Inspect container logs and fix the application crash or misconfiguration causing restarts.",
            "verification_steps": [
                f"kubectl logs {resource} -n {namespace}",
                f"kubectl get pod {resource} -n {namespace}",
            ],
            "rollback_steps": [f"kubectl rollout undo deployment/{resource} -n {namespace}"],
        }

    if category == "deployment":
        return {
            "immediate_fix": "Resolve underlying pod failures, then verify rollout completes successfully.",
            "verification_steps": [
                f"kubectl rollout status deployment/{resource} -n {namespace}",
                f"kubectl get deployment {resource} -n {namespace}",
            ],
            "rollback_steps": [f"kubectl rollout undo deployment/{resource} -n {namespace}"],
        }

    if category == "network":
        return {
            "immediate_fix": "Align service selector labels with pod labels or ensure backing pods are running.",
            "verification_steps": [
                f"kubectl get endpoints {resource} -n {namespace}",
                f"kubectl describe service {resource} -n {namespace}",
            ],
            "rollback_steps": [f"kubectl rollout undo deployment -n {namespace}"],
        }

    return {
        "immediate_fix": "Investigate using the provided commands and apply the targeted fix for this resource.",
        "verification_steps": finding.get("investigation_commands", [])[:2],
        "rollback_steps": [],
    }


def _build_confidence_reasoning(finding: dict[str, Any]) -> str:
    reasons = []
    if finding.get("evidence"):
        reasons.append("Collected pod/event/log evidence supports this finding.")
    if finding.get("severity") in {"Critical", "High"}:
        reasons.append("Severity indicates active user-facing impact.")
    state = finding.get("current_state", "")
    if "ImagePull" in state:
        reasons.append("Events confirm image pull failure.")
    if "CrashLoop" in state:
        reasons.append("Container restart loop detected.")
    if not reasons:
        reasons.append("Based on automated Kubernetes inspection signals.")
    return " ".join(reasons)


def _safe_finding_from_dict(payload: dict[str, Any]) -> Finding | None:
    finding_id = payload.get("id", "unknown")
    try:
        normalized = normalize_finding_payload(payload)
        return Finding(**normalized)
    except ValidationError as exc:
        logger.warning(
            "Skipping invalid finding {} after normalization: {}",
            finding_id,
            exc.errors()[0].get("msg") if exc.errors() else exc,
        )
        return None


def _merge_finding(rule_finding: dict[str, Any], llm_finding: dict[str, Any] | None) -> Finding | None:
    merged = dict(rule_finding)
    default_remediation = _default_remediation(rule_finding)
    merged["_default_remediation"] = default_remediation

    if llm_finding:
        for field in ("root_cause", "explanation", "confidence", "confidence_reasoning"):
            if llm_finding.get(field) is not None:
                merged[field] = llm_finding[field]

        llm_remediation = llm_finding.get("remediation")
        if llm_remediation is not None:
            merged["remediation"] = llm_remediation
        else:
            merged["remediation"] = default_remediation
    else:
        merged["remediation"] = default_remediation
        merged.setdefault("root_cause", rule_finding.get("title", ""))
        merged.setdefault(
            "explanation",
            "Detected from collected Kubernetes evidence during automated inspection.",
        )
        merged.setdefault("confidence_reasoning", _build_confidence_reasoning(rule_finding))

    # Never replace rule-based commands with LLM hallucinations
    merged["investigation_commands"] = rule_finding.get("investigation_commands", [])

    finding = _safe_finding_from_dict(merged)
    if finding is None:
        # Last-resort fallback: rule-based only, strip LLM fields
        logger.warning(
            "Falling back to rule-based finding for {}",
            rule_finding.get("id", rule_finding.get("affected_resource", "unknown")),
        )
        fallback = dict(rule_finding)
        fallback["_default_remediation"] = default_remediation
        fallback["remediation"] = default_remediation
        fallback.setdefault("root_cause", rule_finding.get("title", ""))
        fallback.setdefault("explanation", "Detected from collected Kubernetes evidence.")
        fallback.setdefault("confidence_reasoning", _build_confidence_reasoning(rule_finding))
        finding = _safe_finding_from_dict(fallback)

    return finding


def _llm_findings_index(llm_findings: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict]:
    index: dict[tuple[str, str, str], dict] = {}
    for item in llm_findings:
        if not isinstance(item, dict):
            continue
        key = (
            normalize_str(item.get("namespace"), ""),
            normalize_str(item.get("resource_type"), ""),
            normalize_str(item.get("affected_resource"), ""),
        )
        index[key] = item
    return index


def _normalize_timeline(investigation: dict[str, Any]) -> list[TimelineStep]:
    timeline: list[TimelineStep] = []
    for step in investigation.get("timeline", []):
        if not isinstance(step, dict):
            continue
        try:
            timeline.append(
                TimelineStep(
                    step=int(step.get("step", len(timeline) + 1)),
                    action=normalize_str(step.get("action"), "Investigation step"),
                    status=normalize_str(step.get("status"), "completed"),
                )
            )
        except (TypeError, ValueError, ValidationError) as exc:
            logger.warning("Skipping invalid timeline step: {}", exc)
    return timeline


def build_sre_report(
    investigation: dict[str, Any],
    llm_response: dict[str, Any] | None = None,
    cluster_healthy: bool = False,
) -> dict[str, Any]:
    rule_findings = build_findings_from_investigation(investigation)
    llm_findings = (llm_response or {}).get("findings", [])
    llm_index = _llm_findings_index(llm_findings if isinstance(llm_findings, list) else [])

    findings: list[Finding] = []
    for rule_finding in rule_findings:
        key = (
            rule_finding.get("namespace", ""),
            rule_finding.get("resource_type", ""),
            rule_finding.get("affected_resource", ""),
        )
        finding = _merge_finding(rule_finding, llm_index.get(key))
        if finding is not None:
            findings.append(finding)
        else:
            logger.error(
                "Could not build finding for {}/{} in {}",
                rule_finding.get("resource_type"),
                rule_finding.get("affected_resource"),
                rule_finding.get("namespace"),
            )

    health_summary = build_cluster_health_summary(investigation, [f.model_dump() for f in findings])
    llm_score = (llm_response or {}).get("cluster_health_score")
    health_score = (
        100
        if cluster_healthy
        else llm_score
        if llm_score is not None
        else calculate_cluster_health_score([f.model_dump() for f in findings])
    )

    timeline = _normalize_timeline(investigation)

    executive_summary = normalize_str((llm_response or {}).get("executive_summary"), "")
    if not executive_summary:
        if cluster_healthy:
            executive_summary = "Cluster appears healthy. No critical findings detected during investigation."
        elif findings:
            critical = sum(1 for f in findings if f.severity == "Critical")
            executive_summary = (
                f"Investigation detected {len(findings)} issue(s) "
                f"including {critical} critical finding(s). "
                "Review detailed evidence and remediation below."
            )
        else:
            executive_summary = "Investigation completed with limited actionable findings."

    primary = findings[0] if findings else None
    validation_commands: list[str] = []
    remediation_steps: list[str] = []
    verification_steps: list[str] = []
    rollback_commands: list[str] = []

    for finding in findings:
        remediation_steps.append(finding.remediation.immediate_fix)
        verification_steps.extend(finding.remediation.verification_steps)
        rollback_commands.extend(finding.remediation.rollback_steps)
        validation_commands.extend(finding.investigation_commands[:2])

    prevention = normalize_str(
        (llm_response or {}).get("prevention_recommendation"),
        "Add probes, resource limits, and CI validation before production deploys.",
        "prevention_recommendation",
    )

    diagnosis_payload = normalize_diagnosis_payload(
        {
            "root_cause": primary.title if primary else "No critical issues detected",
            "explanation": primary.explanation if primary else executive_summary,
            "fix": primary.remediation.immediate_fix if primary else "No action required.",
            "kubectl_command": primary.investigation_commands[0]
            if primary and primary.investigation_commands
            else "kubectl get pods -A",
            "confidence": primary.confidence if primary else (100 if cluster_healthy else 50),
            "prevention_recommendation": prevention,
            "confidence_reasoning": primary.confidence_reasoning if primary else "",
            "cluster_healthy": cluster_healthy,
            "executive_summary": executive_summary,
            "cluster_health_score": health_score,
            "cluster_health_summary": health_summary,
            "investigation_timeline": timeline,
            "findings": findings,
            "validation_commands": list(dict.fromkeys(validation_commands)),
            "remediation_steps": list(dict.fromkeys(remediation_steps)),
            "verification_steps": list(dict.fromkeys(verification_steps)),
            "rollback_commands": list(dict.fromkeys(rollback_commands)),
        }
    )

    try:
        return Diagnosis(**diagnosis_payload).model_dump()
    except ValidationError as exc:
        logger.error("Diagnosis validation failed, returning minimal safe report: {}", exc)
        return Diagnosis(
            root_cause=primary.title if primary else "Investigation completed",
            explanation=executive_summary,
            fix=primary.remediation.immediate_fix if primary else "Review findings manually.",
            kubectl_command="kubectl get pods -A",
            confidence=primary.confidence if primary else 50,
            cluster_healthy=cluster_healthy,
            executive_summary=executive_summary,
            cluster_health_score=health_score,
            findings=findings,
        ).model_dump()
