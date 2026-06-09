import re
from typing import Any


class FixRecommendationEngine:
    """Validate and enhance fix recommendations from LLM output."""

    KUBECTL_PREFIX = "kubectl "

    def build(self, parsed: dict[str, Any], investigation: dict[str, Any]) -> dict[str, str]:
        fix = (parsed.get("fix") or "").strip()
        kubectl_command = self._normalize_kubectl_command(
            parsed.get("kubectl_command", ""), investigation
        )
        prevention = (parsed.get("prevention_recommendation") or "").strip()

        if not fix:
            fix = "Review pod logs and deployment configuration, then apply the suggested kubectl command."

        if not prevention:
            prevention = (
                "Add readiness/liveness probes, resource limits, and validate "
                "configuration in CI before deploying to production."
            )

        return {
            "fix": fix,
            "kubectl_command": kubectl_command,
            "prevention_recommendation": prevention,
        }

    def _normalize_kubectl_command(
        self, command: str, investigation: dict[str, Any]
    ) -> str:
        command = command.strip().strip("`")

        if command and not command.startswith("kubectl"):
            command = f"kubectl {command.lstrip()}"

        if command and self._looks_valid(command):
            return command

        fallback = self.suggest_fallback_command(investigation)
        return fallback or "kubectl get pods -A"

    def _looks_valid(self, command: str) -> bool:
        return bool(re.match(r"^kubectl\s+\w+", command))

    def suggest_fallback_command(self, investigation: dict[str, Any]) -> str:
        pods = investigation.get("pods", {}).get("problematic_pods", [])
        deployments = investigation.get("deployments", {}).get("unhealthy_deployments", [])

        if pods:
            pod = pods[0]
            name = pod.get("name", "")
            namespace = pod.get("namespace", "default")
            if name:
                return f"kubectl describe pod {name} -n {namespace}"

        if deployments:
            dep = deployments[0]
            name = dep.get("name", "")
            namespace = dep.get("namespace", "default")
            if name:
                return f"kubectl describe deployment {name} -n {namespace}"

        return "kubectl get events -A --sort-by=.lastTimestamp"
