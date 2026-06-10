"""Assemble the final SRE investigation report from evidence and AI enrichment."""

from __future__ import annotations

from typing import Any

from models.investigation import Diagnosis, Finding, Remediation, TimelineStep
from services.finding_builder import build_findings_from_investigation
from services.health_summary import build_cluster_health_summary, calculate_cluster_health_score


def _default_remediation(finding: dict[str, Any]) -> Remediation:
    category = finding.get("category", "")
    resource = finding.get("affected_resource", "")
    namespace = finding.get("namespace", "default")
    state = finding.get("current_state", "")

    if category == "pod" and "ImagePull" in state:
        return Remediation(
            immediate_fix="Update the container image reference to a valid, accessible image tag in the deployment spec.",
            verification_steps=[
                f"kubectl rollout status deployment/{resource} -n {namespace}"
                if namespace != "cluster"
                else f"kubectl get pod {resource} -n {namespace}",
                f"kubectl get pods -n {namespace}",
            ],
            rollback_steps=[
                f"kubectl rollout undo deployment/{resource} -n {namespace}"
                if namespace != "cluster"
                else f"kubectl delete pod {resource} -n {namespace}",
            ],
        )

    if category == "pod" and "CrashLoop" in state:
        return Remediation(
            immediate_fix="Inspect container logs and fix the application crash or misconfiguration causing restarts.",
            verification_steps=[
                f"kubectl logs {resource} -n {namespace}",
                f"kubectl get pod {resource} -n {namespace}",
            ],
            rollback_steps=[
                f"kubectl rollout undo deployment/{resource} -n {namespace}",
            ],
        )

    if category == "deployment":
        return Remediation(
            immediate_fix="Resolve underlying pod failures, then verify rollout completes successfully.",
            verification_steps=[
                f"kubectl rollout status deployment/{resource} -n {namespace}",
                f"kubectl get deployment {resource} -n {namespace}",
            ],
            rollback_steps=[f"kubectl rollout undo deployment/{resource} -n {namespace}"],
        )

    if category == "network":
        return Remediation(
            immediate_fix="Align service selector labels with pod labels or ensure backing pods are running.",
            verification_steps=[
                f"kubectl get endpoints {resource} -n {namespace}",
                f"kubectl describe service {resource} -n {namespace}",
            ],
            rollback_steps=[f"kubectl rollout undo deployment -n {namespace}"],
        )

    return Remediation(
        immediate_fix="Investigate using the provided commands and apply the targeted fix for this resource.",
        verification_steps=finding.get("investigation_commands", [])[:2],
        rollback_steps=[],
    )


def _merge_finding(rule_finding: dict[str, Any], llm_finding: dict[str, Any] | None) -> Finding:
    merged = dict(rule_finding)
    if llm_finding:
        for field in ("root_cause", "explanation", "confidence", "confidence_reasoning"):
            if llm_finding.get(field):
                merged[field] = llm_finding[field]

        llm_remediation = llm_finding.get("remediation", {})
        if isinstance(llm_remediation, dict):
            default = _default_remediation(rule_finding)
            merged["remediation"] = Remediation(
                immediate_fix=llm_remediation.get("immediate_fix") or default.immediate_fix,
                verification_steps=llm_remediation.get("verification_steps") or default.verification_steps,
                rollback_steps=llm_remediation.get("rollback_steps") or default.rollback_steps,
            )
        else:
            merged["remediation"] = _default_remediation(rule_finding)
    else:
        merged["remediation"] = _default_remediation(rule_finding)
        merged.setdefault("root_cause", rule_finding.get("title", ""))
        merged.setdefault(
            "explanation",
            "Detected from collected Kubernetes evidence during automated inspection.",
        )
        merged.setdefault("confidence_reasoning", _build_confidence_reasoning(rule_finding))

    # Never replace rule-based commands with LLM hallucinations
    merged["investigation_commands"] = rule_finding.get("investigation_commands", [])

    return Finding(**merged)


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


def _llm_findings_index(llm_findings: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict]:
    index: dict[tuple[str, str, str], dict] = {}
    for item in llm_findings:
        key = (
            item.get("namespace", ""),
            item.get("resource_type", ""),
            item.get("affected_resource", ""),
        )
        index[key] = item
    return index


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
        findings.append(_merge_finding(rule_finding, llm_index.get(key)))

    health_summary = build_cluster_health_summary(investigation, [f.model_dump() for f in findings])
    health_score = (
        100
        if cluster_healthy
        else (llm_response or {}).get("cluster_health_score")
        or calculate_cluster_health_score([f.model_dump() for f in findings])
    )

    timeline = [
        TimelineStep(**step)
        for step in investigation.get("timeline", [])
    ]

    executive_summary = (llm_response or {}).get("executive_summary", "")
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

    return Diagnosis(
        root_cause=primary.title if primary else "No critical issues detected",
        explanation=primary.explanation if primary else executive_summary,
        fix=primary.remediation.immediate_fix if primary else "No action required.",
        kubectl_command=primary.investigation_commands[0] if primary and primary.investigation_commands else "kubectl get pods -A",
        confidence=primary.confidence if primary else (100 if cluster_healthy else 50),
        prevention_recommendation=(llm_response or {}).get(
            "prevention_recommendation",
            "Add probes, resource limits, and CI validation before production deploys.",
        ),
        confidence_reasoning=primary.confidence_reasoning if primary else "",
        cluster_healthy=cluster_healthy,
        executive_summary=executive_summary,
        cluster_health_score=health_score,
        cluster_health_summary=health_summary,
        investigation_timeline=timeline,
        findings=findings,
        validation_commands=list(dict.fromkeys(validation_commands)),
        remediation_steps=list(dict.fromkeys(remediation_steps)),
        verification_steps=list(dict.fromkeys(verification_steps)),
        rollback_commands=list(dict.fromkeys(rollback_commands)),
    ).model_dump()
