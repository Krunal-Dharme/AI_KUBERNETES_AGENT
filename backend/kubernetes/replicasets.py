from kubernetes.executor import KubectlExecutor, summarize_stderr


class ReplicaSetInspector:
    """Inspect ReplicaSet health for rollout issues."""

    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        self.executor = executor or KubectlExecutor()

    def inspect(self) -> dict:
        data, result = self.executor.run_json("get", "replicasets", "-A")

        if data is None:
            return {
                "healthy": False,
                "error": summarize_stderr(result.stderr) or "Failed to fetch replicasets",
                "unhealthy_replicasets": [],
                "total_replicasets": 0,
            }

        items = data.get("items", [])
        unhealthy: list[dict] = []

        for rs in items:
            issue = self._detect_issue(rs)
            if issue:
                unhealthy.append(issue)

        return {
            "healthy": len(unhealthy) == 0,
            "total_replicasets": len(items),
            "unhealthy_replicasets": unhealthy,
        }

    def _detect_issue(self, rs: dict) -> dict | None:
        metadata = rs.get("metadata", {})
        spec = rs.get("spec", {})
        status = rs.get("status", {})

        name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", "default")
        desired = spec.get("replicas", 0)
        ready = status.get("readyReplicas", 0) or 0
        available = status.get("availableReplicas", 0) or 0

        issues = []
        if desired > 0 and ready < desired:
            issues.append(f"only {ready}/{desired} replicas ready")
        if desired > 0 and available < desired:
            issues.append(f"only {available}/{desired} replicas available")

        if not issues:
            return None

        return {
            "name": name,
            "namespace": namespace,
            "desired_replicas": desired,
            "ready_replicas": ready,
            "available_replicas": available,
            "issues": issues,
            "owner_references": [
                ref.get("kind", "") + "/" + ref.get("name", "")
                for ref in metadata.get("ownerReferences", [])
            ],
        }
