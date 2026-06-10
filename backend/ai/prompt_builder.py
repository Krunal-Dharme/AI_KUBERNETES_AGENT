import json
from typing import Any

SYSTEM_PROMPT = """You are a Senior Kubernetes SRE producing a production-grade incident investigation report.

You receive FULL collected evidence from an automated investigation. Your job is to enrich pre-detected findings with root cause analysis, remediation, and confidence reasoning.

Rules:
- Report ALL issues found. Do NOT stop at the first issue.
- Every finding must have severity: Critical, High, Medium, Low, or Info.
- Use ONLY investigation commands already provided in pre_detected_findings — do NOT invent new kubectl commands.
- Correlate pods, logs, events, deployments, replicasets, nodes, services, and ingress.
- Be specific: name namespaces and resources.
- Assign per-finding confidence (0-100) with explicit reasoning citing evidence.
- Provide targeted remediation: immediate fix, verification steps, rollback steps.

You MUST respond with valid JSON only (no markdown) using this schema:
{
  "executive_summary": "2-3 sentence overview of cluster state and top issues",
  "cluster_health_score": 65,
  "prevention_recommendation": "Cluster-wide prevention advice",
  "findings": [
    {
      "namespace": "default",
      "resource_type": "Pod",
      "affected_resource": "imagepull-test",
      "root_cause": "One sentence root cause",
      "explanation": "2-4 sentences correlating evidence",
      "confidence": 95,
      "confidence_reasoning": "Bullet-style reasoning citing specific evidence",
      "remediation": {
        "immediate_fix": "Specific fix steps",
        "verification_steps": ["kubectl ..."],
        "rollback_steps": ["kubectl ..."]
      }
    }
  ]
}

Match findings to pre_detected_findings by namespace + resource_type + affected_resource."""


def build_messages(investigation: dict[str, Any], pre_detected_findings: list[dict]) -> list[dict[str, str]]:
    """Build structured LLM messages from full investigation evidence."""
    user_content = f"""Analyze this Kubernetes investigation and return an SRE report as JSON.

## Pre-Detected Findings (use these resources; do not invent new ones)
{json.dumps(pre_detected_findings, indent=2)}

## Node Status
{json.dumps(investigation.get("nodes", {}), indent=2)}

## Pod Status
{json.dumps(investigation.get("pods", {}), indent=2)}

## Container Logs
{json.dumps(investigation.get("logs", {}), indent=2)}

## Events
{json.dumps(investigation.get("events", {}), indent=2)}

## Deployments
{json.dumps(investigation.get("deployments", {}), indent=2)}

## ReplicaSets
{json.dumps(investigation.get("replicasets", {}), indent=2)}

## Networking (Services/Endpoints)
{json.dumps(investigation.get("network", {}), indent=2)}

## Ingress
{json.dumps(investigation.get("ingress", {}), indent=2)}

## Investigation Timeline
{json.dumps(investigation.get("timeline", []), indent=2)}

Enrich ALL pre-detected findings. Return JSON only."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
