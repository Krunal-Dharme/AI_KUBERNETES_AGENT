from kubernetes.executor import KubectlExecutor, summarize_stderr


class NetworkInspector:
    """Inspect services, endpoints, and basic networking issues."""

    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        self.executor = executor or KubectlExecutor()

    def inspect(self) -> dict:
        services_data, svc_result = self.executor.run_json("get", "svc", "-A")
        endpoints_data, ep_result = self.executor.run_json("get", "endpoints", "-A")
        pods_data, pods_result = self.executor.run_json("get", "pods", "-A")

        if services_data is None:
            return {
                "healthy": False,
                "error": summarize_stderr(svc_result.stderr) or "Failed to fetch services",
                "issues": [],
            }

        endpoints_map = self._build_endpoints_map(endpoints_data or {"items": []})
        pod_labels_by_ns = self._build_pod_labels_map(pods_data or {"items": []})

        issues: list[dict] = []
        services = services_data.get("items", [])

        for service in services:
            service_issues = self._inspect_service(
                service, endpoints_map, pod_labels_by_ns
            )
            issues.extend(service_issues)

        return {
            "healthy": len(issues) == 0,
            "total_services": len(services),
            "issues": issues,
            "errors": self._collect_errors(svc_result, ep_result, pods_result),
        }

    def _build_endpoints_map(self, endpoints_data: dict) -> dict:
        endpoints_map: dict[tuple[str, str], dict] = {}

        for endpoint in endpoints_data.get("items", []):
            metadata = endpoint.get("metadata", {})
            key = (metadata.get("namespace", "default"), metadata.get("name", ""))
            endpoints_map[key] = endpoint

        return endpoints_map

    def _build_pod_labels_map(self, pods_data: dict) -> dict:
        labels_by_ns: dict[str, list[dict]] = {}

        for pod in pods_data.get("items", []):
            metadata = pod.get("metadata", {})
            namespace = metadata.get("namespace", "default")
            labels_by_ns.setdefault(namespace, []).append(metadata.get("labels", {}))

        return labels_by_ns

    def _inspect_service(
        self,
        service: dict,
        endpoints_map: dict,
        pod_labels_by_ns: dict,
    ) -> list[dict]:
        metadata = service.get("metadata", {})
        spec = service.get("spec", {})

        name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", "default")
        service_type = spec.get("type", "ClusterIP")
        selector = spec.get("selector") or {}
        cluster_ip = spec.get("clusterIP", "")

        if service_type == "ExternalName":
            return []

        issues: list[dict] = []
        endpoint = endpoints_map.get((namespace, name))
        has_endpoints = self._has_ready_endpoints(endpoint)

        if selector and not has_endpoints:
            issues.append(
                {
                    "service": name,
                    "namespace": namespace,
                    "type": service_type,
                    "issue": "missing_endpoints",
                    "message": f"Service '{name}' has no ready endpoints",
                    "selector": selector,
                }
            )

        if selector and not self._selector_matches_pods(
            namespace, selector, pod_labels_by_ns
        ):
            issues.append(
                {
                    "service": name,
                    "namespace": namespace,
                    "type": service_type,
                    "issue": "selector_mismatch",
                    "message": f"Service '{name}' selector does not match any pod labels",
                    "selector": selector,
                }
            )

        if cluster_ip == "None" and service_type == "ClusterIP" and not has_endpoints:
            issues.append(
                {
                    "service": name,
                    "namespace": namespace,
                    "type": service_type,
                    "issue": "headless_no_endpoints",
                    "message": f"Headless service '{name}' has no backing endpoints (possible DNS issue)",
                    "selector": selector,
                }
            )

        return issues

    def _has_ready_endpoints(self, endpoint: dict | None) -> bool:
        if not endpoint:
            return False

        subsets = endpoint.get("subsets") or []
        for subset in subsets:
            addresses = subset.get("addresses") or []
            if addresses:
                return True

        return False

    def _selector_matches_pods(
        self,
        namespace: str,
        selector: dict,
        pod_labels_by_ns: dict,
    ) -> bool:
        pods_in_ns = pod_labels_by_ns.get(namespace, [])

        for pod_labels in pods_in_ns:
            if all(pod_labels.get(k) == v for k, v in selector.items()):
                return True

        return False

    def _collect_errors(self, *results) -> list[str]:
        errors = []
        for result in results:
            if not result.success and result.stderr:
                errors.append(summarize_stderr(result.stderr))
        return errors
