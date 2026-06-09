from typing import Any

from ai.root_cause_analyzer import AIAgent


def analyze_cluster_state(investigation: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible entry point for AI reasoning."""
    return AIAgent().diagnose(investigation)
