import json
from typing import Any

SYSTEM_PROMPT = """You are a Senior Kubernetes SRE diagnosing production incidents.

Your job is to analyze collected Kubernetes evidence and produce a precise, actionable diagnosis.

Rules:
- Correlate evidence across pods, logs, events, deployments, and networking.
- Identify the most likely root cause, not just symptoms.
- Be specific: name resources (pod, deployment, namespace) when possible.
- Provide practical, Kubernetes-specific fixes. Avoid generic advice.
- Suggest real kubectl commands a beginner can run.
- Assign a confidence score (0-100) based on evidence strength.
- If evidence is insufficient, say so and lower confidence.

You MUST respond with valid JSON only (no markdown, no extra text) using this schema:
{
  "root_cause": "One concise sentence stating the root cause",
  "explanation": "2-4 sentences correlating pod status, logs, events, deployments, and network findings",
  "fix": "Clear actionable fix steps",
  "kubectl_command": "Primary kubectl command to apply or investigate the fix",
  "prevention_recommendation": "How to prevent this issue in the future",
  "confidence": 85,
  "confidence_reasoning": "Why this confidence level, citing specific evidence"
}"""


def build_messages(investigation: dict[str, Any]) -> list[dict[str, str]]:
    """Build structured LLM messages from investigation evidence."""
    user_content = f"""Analyze the following Kubernetes investigation evidence and return your diagnosis as JSON.

## Pod Status
{json.dumps(investigation.get("pods", {}), indent=2)}

## Logs
{json.dumps(investigation.get("logs", {}), indent=2)}

## Events
{json.dumps(investigation.get("events", {}), indent=2)}

## Deployment Health
{json.dumps(investigation.get("deployments", {}), indent=2)}

## Networking Findings
{json.dumps(investigation.get("network", {}), indent=2)}

Correlate all sections above. Return JSON only."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
