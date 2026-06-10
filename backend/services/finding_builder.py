"""Rule-based multi-issue finding extraction from investigation evidence."""

from __future__ import annotations

from typing import Any

from services.investigation_commands import (
    deployment_commands,
    ingress_commands,
    node_commands,
    pod_commands,
    replicaset_commands,
    service_commands,
)

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Info"]

POD_SEVERITY = {
    "CrashLoopBackOff": "Critical",
    "ImagePullBackOff": "Critical",
    "ErrImagePull": "Critical",
    "OOMKilled": "Critical",
    "Error": "Critical",
    "CreateContainerConfigError": "High",
    "ContainerCreating": "Medium",
    "Pending": "High",
    "Failed": "Critical",
}


def _severity_rank(severity: str) -> int:
    try:
        return SEVERITY_ORDER.index(severity)
    except ValueError:
        return len(SEVERITY_ORDER)


def _related_events(
    events: dict[str, Any],
    namespace: str,
    resource_name: str,
) -> list[str]:
    lines: list[str] = []
    for event in events.get("findings", []):
        if event.get("namespace") != namespace:
            continue
        if resource_name and event.get("object_name") != resource_name:
            continue
        reason = event.get("reason", "")
        message = event.get("message", "")
        ts = event.get("last_timestamp", "")
        prefix = f"[{ts}] " if ts else ""
        lines.append(f"{prefix}{reason}: {message}".strip(": "))
    return lines[:8]


def _related_logs(
    logs: dict[str, Any],
    namespace: str,
    pod_name: str,
) -> list[str]:
    for entry in logs.get("entries", []):
        if entry.get("namespace") == namespace and entry.get("pod") == pod_name:
            return [line for line in entry.get("logs", [])[:10]]
    return []


def build_findings_from_investigation(investigation: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract ALL detected issues with evidence and investigation commands."""
    findings: list[dict[str, Any]] = []
    counter = 1

    pods = investigation.get("pods", {})
    logs = investigation.get("logs", {})
    events = investigation.get("events", {})
    deployments = investigation.get("deployments", {})
    network = investigation.get("network", {})
    nodes = investigation.get("nodes", {})
    replicasets = investigation.get("replicasets", {})
    ingress = investigation.get("ingress", {})

    for pod in pods.get("problematic_pods", []):
        name = pod.get("name", "")
        namespace = pod.get("namespace", "default")
        status = pod.get("status", "Unknown")
        severity = POD_SEVERITY.get(status, "High")

        evidence = [
            f"Pod: {name}",
            f"Status: {status}",
            f"Phase: {pod.get('phase', 'Unknown')}",
        ]
        evidence.extend(f"Detail: {detail}" for detail in pod.get("details", [])[:5])
        evidence.extend(_related_events(events, namespace, name))
        evidence.extend(_related_logs(logs, namespace, name))

        findings.append(
            {
                "id": f"finding-{counter}",
                "title": f"{status} — pod/{name}",
                "severity": severity,
                "category": "pod",
                "affected_resource": name,
                "namespace": namespace,
                "resource_type": "Pod",
                "current_state": status,
                "evidence": evidence,
                "investigation_commands": pod_commands(name, namespace),
                "confidence": 90 if _related_events(events, namespace, name) else 75,
            }
        )
        counter += 1

    for pod in pods.get("restarting_pods", []):
        name = pod.get("name", "")
        namespace = pod.get("namespace", "default")
        restart_count = pod.get("restart_count", 0)

        findings.append(
            {
                "id": f"finding-{counter}",
                "title": f"Restarting pod — pod/{name}",
                "severity": "Info",
                "category": "pod",
                "affected_resource": name,
                "namespace": namespace,
                "resource_type": "Pod",
                "current_state": f"Restarting ({restart_count} restarts)",
                "evidence": [
                    f"Pod: {name}",
                    f"Restart count: {restart_count}",
                    f"Phase: {pod.get('phase', 'Running')}",
                ],
                "investigation_commands": pod_commands(name, namespace),
                "confidence": 70,
            }
        )
        counter += 1

    for node in nodes.get("not_ready_nodes", []):
        name = node.get("name", "")
        findings.append(
            {
                "id": f"finding-{counter}",
                "title": f"Node not ready — node/{name}",
                "severity": "Critical",
                "category": "node",
                "affected_resource": name,
                "namespace": "cluster",
                "resource_type": "Node",
                "current_state": node.get("reason", "NotReady"),
                "evidence": [
                    f"Node: {name}",
                    f"Reason: {node.get('reason', 'NotReady')}",
                    f"Message: {node.get('message', '')}",
                ],
                "investigation_commands": node_commands(name),
                "confidence": 85,
            }
        )
        counter += 1

    for dep in deployments.get("unhealthy_deployments", []):
        name = dep.get("name", "")
        namespace = dep.get("namespace", "default")
        evidence = [
            f"Deployment: {name}",
            f"Desired: {dep.get('desired_replicas', 0)}",
            f"Available: {dep.get('available_replicas', 0)}",
            f"Ready: {dep.get('ready_replicas', 0)}",
        ]
        evidence.extend(f"Issue: {issue}" for issue in dep.get("issues", []))
        for condition in dep.get("conditions", [])[:3]:
            evidence.append(
                f"Condition {condition.get('type')}: {condition.get('reason')} — {condition.get('message', '')}"
            )

        findings.append(
            {
                "id": f"finding-{counter}",
                "title": f"Deployment unavailable — deployment/{name}",
                "severity": "Medium",
                "category": "deployment",
                "affected_resource": name,
                "namespace": namespace,
                "resource_type": "Deployment",
                "current_state": "; ".join(dep.get("issues", ["Unavailable"])),
                "evidence": evidence,
                "investigation_commands": deployment_commands(name, namespace),
                "confidence": 80,
            }
        )
        counter += 1

    for rs in replicasets.get("unhealthy_replicasets", []):
        name = rs.get("name", "")
        namespace = rs.get("namespace", "default")
        findings.append(
            {
                "id": f"finding-{counter}",
                "title": f"ReplicaSet degraded — replicaset/{name}",
                "severity": "Medium",
                "category": "replicaset",
                "affected_resource": name,
                "namespace": namespace,
                "resource_type": "ReplicaSet",
                "current_state": "; ".join(rs.get("issues", ["Degraded"])),
                "evidence": [
                    f"ReplicaSet: {name}",
                    f"Desired: {rs.get('desired_replicas', 0)}",
                    f"Ready: {rs.get('ready_replicas', 0)}",
                    f"Available: {rs.get('available_replicas', 0)}",
                ],
                "investigation_commands": replicaset_commands(name, namespace),
                "confidence": 75,
            }
        )
        counter += 1

    for issue in network.get("issues", []):
        name = issue.get("service", "")
        namespace = issue.get("namespace", "default")
        issue_type = issue.get("issue", "network_issue")
        severity = "Medium" if issue_type == "missing_endpoints" else "High"

        findings.append(
            {
                "id": f"finding-{counter}",
                "title": f"Service {issue_type.replace('_', ' ')} — svc/{name}",
                "severity": severity,
                "category": "network",
                "affected_resource": name,
                "namespace": namespace,
                "resource_type": "Service",
                "current_state": issue.get("message", issue_type),
                "evidence": [
                    f"Service: {name}",
                    f"Issue: {issue_type}",
                    f"Message: {issue.get('message', '')}",
                    f"Selector: {issue.get('selector', {})}",
                ],
                "investigation_commands": service_commands(name, namespace),
                "confidence": 78,
            }
        )
        counter += 1

    for issue in ingress.get("issues", []):
        name = issue.get("ingress", "")
        namespace = issue.get("namespace", "default")
        findings.append(
            {
                "id": f"finding-{counter}",
                "title": f"Ingress issue — ingress/{name}",
                "severity": "Medium",
                "category": "ingress",
                "affected_resource": name,
                "namespace": namespace,
                "resource_type": "Ingress",
                "current_state": issue.get("message", issue.get("issue", "")),
                "evidence": [
                    f"Ingress: {name}",
                    f"Issue: {issue.get('issue', '')}",
                    f"Message: {issue.get('message', '')}",
                ],
                "investigation_commands": ingress_commands(name, namespace),
                "confidence": 72,
            }
        )
        counter += 1

    # Standalone warning events not already tied to a pod finding
    covered_objects = {
        (f.get("namespace"), f.get("affected_resource"))
        for f in findings
        if f.get("resource_type") in {"Pod", "Deployment", "Service"}
    }
    for event in events.get("findings", []):
        namespace = event.get("namespace", "default")
        object_name = event.get("object_name", "")
        if (namespace, object_name) in covered_objects:
            continue
        if event.get("reason") not in {"FailedScheduling", "FailedMount", "FailedCreate"}:
            continue

        findings.append(
            {
                "id": f"finding-{counter}",
                "title": f"{event.get('reason')} — {event.get('object_kind', 'Resource')}/{object_name}",
                "severity": "High" if event.get("reason") == "FailedScheduling" else "Medium",
                "category": "event",
                "affected_resource": object_name,
                "namespace": namespace,
                "resource_type": event.get("object_kind", "Resource"),
                "current_state": event.get("reason", "Warning"),
                "evidence": [
                    f"Event: {event.get('reason')}",
                    f"Type: {event.get('type', '')}",
                    f"Message: {event.get('message', '')}",
                    f"Count: {event.get('count', 1)}",
                ],
                "investigation_commands": _event_commands(event),
                "confidence": 70,
            }
        )
        counter += 1

    findings.sort(key=lambda f: _severity_rank(f.get("severity", "Info")))
    return findings


def _event_commands(event: dict[str, Any]) -> list[str]:
    kind = event.get("object_kind", "")
    name = event.get("object_name", "")
    namespace = event.get("namespace", "default")

    if kind == "Pod" and name:
        return pod_commands(name, namespace)
    if kind == "Deployment" and name:
        return deployment_commands(name, namespace)
    return [f"kubectl get events -n {namespace} --sort-by=.lastTimestamp"]
