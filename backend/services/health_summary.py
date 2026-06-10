from models.investigation import ClusterHealthSummary

SEVERITY_WEIGHTS = {
    "Critical": 25,
    "High": 15,
    "Medium": 8,
    "Low": 4,
    "Info": 1,
}


def build_cluster_health_summary(
    investigation: dict,
    findings: list[dict] | None = None,
) -> ClusterHealthSummary:
    nodes = investigation.get("nodes", {})
    pods = investigation.get("pods", {})
    deployments = investigation.get("deployments", {})
    network = investigation.get("network", {})

    total_nodes = nodes.get("total_nodes", 0)
    not_ready = len(nodes.get("not_ready_nodes", []))
    ready_nodes = max(total_nodes - not_ready, 0)

    status_counts = pods.get("status_counts", {})
    total_deployments = deployments.get("total_deployments", 0)
    unhealthy_deployments = len(deployments.get("unhealthy_deployments", []))

    critical = sum(1 for f in (findings or []) if f.get("severity") == "Critical")
    high = sum(1 for f in (findings or []) if f.get("severity") == "High")
    medium = sum(1 for f in (findings or []) if f.get("severity") == "Medium")
    warning = sum(1 for f in (findings or []) if f.get("severity") == "Low")

    crashloop = sum(
        1
        for pod in pods.get("problematic_pods", [])
        if pod.get("status") == "CrashLoopBackOff"
    )

    return ClusterHealthSummary(
        nodes_ready=f"{ready_nodes}/{total_nodes}" if total_nodes else "0/0",
        nodes_total=total_nodes,
        pods_running=status_counts.get("running", 0),
        pods_failed=status_counts.get("failed", 0),
        pods_pending=status_counts.get("pending", 0),
        pods_total=pods.get("total_pods", 0),
        pods_crashloop=crashloop,
        deployments_healthy=max(total_deployments - unhealthy_deployments, 0),
        deployments_degraded=unhealthy_deployments,
        services_missing_endpoints=sum(
            1 for issue in network.get("issues", []) if issue.get("issue") == "missing_endpoints"
        ),
        critical_findings=critical,
        high_findings=high,
        medium_findings=medium,
        warning_findings=warning,
    )


def calculate_cluster_health_score(findings: list[dict]) -> int:
    if not findings:
        return 100

    penalty = sum(SEVERITY_WEIGHTS.get(f.get("severity", "Info"), 1) for f in findings)
    return max(0, min(100, 100 - penalty))
