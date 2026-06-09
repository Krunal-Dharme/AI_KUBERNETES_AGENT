def is_cluster_healthy(investigation: dict) -> bool:
    """Return True when no critical Kubernetes issues were found."""
    pods = investigation.get("pods", {})
    events = investigation.get("events", {})
    deployments = investigation.get("deployments", {})
    network = investigation.get("network", {})
    nodes = investigation.get("nodes", {})

    has_pod_issues = bool(pods.get("problematic_pods"))
    has_event_issues = bool(events.get("findings"))
    has_deployment_issues = bool(deployments.get("unhealthy_deployments"))
    has_network_issues = bool(network.get("issues"))
    has_node_issues = bool(nodes.get("not_ready_nodes"))
    has_errors = any(
        section.get("error")
        for section in [pods, events, deployments, network, nodes]
        if isinstance(section, dict)
    )

    return not any(
        [
            has_pod_issues,
            has_event_issues,
            has_deployment_issues,
            has_network_issues,
            has_node_issues,
            has_errors,
        ]
    )


def healthy_cluster_diagnosis(cluster_context: str) -> dict:
    return {
        "root_cause": "No critical Kubernetes issues detected",
        "explanation": (
            f"Cluster '{cluster_context}' appears healthy. "
            "Pods, nodes, deployments, events, and networking show no critical problems."
        ),
        "fix": "No action required. Continue monitoring the cluster.",
        "kubectl_command": f"kubectl --context {cluster_context} get pods -A",
        "prevention_recommendation": (
            "Run investigations regularly and keep resource limits, probes, and alerts configured."
        ),
        "confidence": 88,
        "confidence_reasoning": (
            "No unhealthy pods, failed deployments, warning events, or network issues were found."
        ),
    }
