from kubernetes.executor import KubectlExecutor, summarize_stderr


class IngressInspector:
    """Inspect Ingress resources for routing issues."""

    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        self.executor = executor or KubectlExecutor()

    def inspect(self) -> dict:
        data, result = self.executor.run_json("get", "ingress", "-A")

        if data is None:
            return {
                "healthy": False,
                "error": summarize_stderr(result.stderr) or "Failed to fetch ingress",
                "issues": [],
                "total_ingress": 0,
            }

        items = data.get("items", [])
        issues: list[dict] = []

        for ingress in items:
            ingress_issues = self._inspect_ingress(ingress)
            issues.extend(ingress_issues)

        return {
            "healthy": len(issues) == 0,
            "total_ingress": len(items),
            "issues": issues,
        }

    def _inspect_ingress(self, ingress: dict) -> list[dict]:
        metadata = ingress.get("metadata", {})
        status = ingress.get("status", {})
        spec = ingress.get("spec", {})

        name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", "default")
        load_balancer = status.get("loadBalancer", {}).get("ingress", [])
        rules = spec.get("rules", [])

        issues: list[dict] = []

        if not rules:
            issues.append(
                {
                    "ingress": name,
                    "namespace": namespace,
                    "issue": "no_rules",
                    "message": f"Ingress '{name}' has no routing rules configured",
                }
            )

        if spec.get("tls") and not load_balancer:
            issues.append(
                {
                    "ingress": name,
                    "namespace": namespace,
                    "issue": "tls_no_address",
                    "message": f"Ingress '{name}' has TLS configured but no load balancer address assigned",
                }
            )

        if rules and not load_balancer:
            issues.append(
                {
                    "ingress": name,
                    "namespace": namespace,
                    "issue": "no_load_balancer",
                    "message": f"Ingress '{name}' has no load balancer ingress address",
                }
            )

        return issues
