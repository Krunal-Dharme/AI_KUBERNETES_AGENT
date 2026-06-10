from services.report_builder import build_sre_report


def is_cluster_healthy(investigation: dict) -> bool:
    """Return True when no critical Kubernetes issues were found."""
    pods = investigation.get("pods", {})
    events = investigation.get("events", {})
    deployments = investigation.get("deployments", {})
    network = investigation.get("network", {})
    nodes = investigation.get("nodes", {})
    replicasets = investigation.get("replicasets", {})
    ingress = investigation.get("ingress", {})

    has_pod_issues = bool(pods.get("problematic_pods"))
    has_event_issues = bool(events.get("findings"))
    has_deployment_issues = bool(deployments.get("unhealthy_deployments"))
    has_network_issues = bool(network.get("issues"))
    has_node_issues = bool(nodes.get("not_ready_nodes"))
    has_replicaset_issues = bool(replicasets.get("unhealthy_replicasets"))
    has_ingress_issues = bool(ingress.get("issues"))
    has_errors = any(
        section.get("error")
        for section in [pods, events, deployments, network, nodes, replicasets, ingress]
        if isinstance(section, dict)
    )

    return not any(
        [
            has_pod_issues,
            has_event_issues,
            has_deployment_issues,
            has_network_issues,
            has_node_issues,
            has_replicaset_issues,
            has_ingress_issues,
            has_errors,
        ]
    )


def healthy_cluster_diagnosis(cluster_context: str, investigation: dict | None = None) -> dict:
    investigation = investigation or {"timeline": [], "pods": {}, "nodes": {}, "deployments": {}, "network": {}}
    report = build_sre_report(
        investigation,
        llm_response={
            "executive_summary": (
                f"Cluster '{cluster_context}' appears healthy. "
                "No critical pod, node, deployment, network, or ingress issues detected."
            ),
            "cluster_health_score": 100,
            "prevention_recommendation": (
                "Run investigations regularly and keep resource limits, probes, and alerts configured."
            ),
            "findings": [],
        },
        cluster_healthy=True,
    )
    return report
