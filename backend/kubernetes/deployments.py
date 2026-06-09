from kubernetes.executor import KubectlExecutor, summarize_stderr


class DeploymentInspector:
    """Inspect deployment health and rollout status."""

    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        self.executor = executor or KubectlExecutor()

    def inspect(self) -> dict:
        data, result = self.executor.run_json("get", "deployments", "-A")

        if data is None:
            return {
                "healthy": False,
                "error": summarize_stderr(result.stderr) or "Failed to fetch deployments",
                "unhealthy_deployments": [],
                "total_deployments": 0,
            }

        items = data.get("items", [])
        unhealthy_deployments: list[dict] = []

        for deployment in items:
            issue = self._detect_deployment_issue(deployment)
            if issue:
                unhealthy_deployments.append(issue)

        return {
            "healthy": len(unhealthy_deployments) == 0,
            "total_deployments": len(items),
            "unhealthy_deployments": unhealthy_deployments,
        }

    def _detect_deployment_issue(self, deployment: dict) -> dict | None:
        metadata = deployment.get("metadata", {})
        spec = deployment.get("spec", {})
        status = deployment.get("status", {})

        name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", "default")

        desired = spec.get("replicas", 0)
        available = status.get("availableReplicas", 0) or 0
        unavailable = status.get("unavailableReplicas", 0) or 0
        ready = status.get("readyReplicas", 0) or 0
        updated = status.get("updatedReplicas", 0) or 0

        conditions = status.get("conditions", [])
        failed_conditions = [
            {
                "type": c.get("type"),
                "status": c.get("status"),
                "reason": c.get("reason"),
                "message": c.get("message", "")[:200],
            }
            for c in conditions
            if c.get("status") != "True"
        ]

        issues = []

        if desired > 0 and available < desired:
            issues.append(
                f"only {available}/{desired} replicas available"
            )

        if unavailable > 0:
            issues.append(f"{unavailable} unavailable replicas")

        if desired > 0 and ready < desired:
            issues.append(f"only {ready}/{desired} replicas ready")

        if desired > 0 and updated < desired:
            issues.append(f"rollout incomplete: {updated}/{desired} updated")

        for condition in conditions:
            if condition.get("type") == "Progressing" and condition.get("status") == "False":
                issues.append(
                    f"rollout failed: {condition.get('reason', 'Unknown')}"
                )
            if condition.get("type") == "Available" and condition.get("status") == "False":
                issues.append("deployment not available")

        if not issues:
            return None

        return {
            "name": name,
            "namespace": namespace,
            "desired_replicas": desired,
            "available_replicas": available,
            "unavailable_replicas": unavailable,
            "ready_replicas": ready,
            "updated_replicas": updated,
            "issues": issues,
            "conditions": failed_conditions,
        }
