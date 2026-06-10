from collections.abc import Callable

from loguru import logger

from kubernetes.deployments import DeploymentInspector
from kubernetes.events import EventsAnalyzer
from kubernetes.executor import KubectlExecutor
from kubernetes.ingress import IngressInspector
from kubernetes.logs import LogsCollector
from kubernetes.network import NetworkInspector
from kubernetes.nodes import NodeInspector
from kubernetes.pods import PodInspector
from kubernetes.replicasets import ReplicaSetInspector


class InvestigationService:
    """Orchestrate Kubernetes evidence collection like a junior DevOps engineer."""

    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        self.executor = executor or KubectlExecutor()
        self.node_inspector = NodeInspector(self.executor)
        self.pod_inspector = PodInspector(self.executor)
        self.logs_collector = LogsCollector(self.executor)
        self.events_analyzer = EventsAnalyzer(self.executor)
        self.deployment_inspector = DeploymentInspector(self.executor)
        self.network_inspector = NetworkInspector(self.executor)
        self.replicaset_inspector = ReplicaSetInspector(self.executor)
        self.ingress_inspector = IngressInspector(self.executor)

    def run(self, on_progress: Callable[[str, str, str], None] | None = None) -> dict:
        logger.info(
            "Starting Kubernetes investigation (context={})",
            self.executor.context or "current",
        )

        timeline: list[dict] = []
        timeline_step = 0

        def progress(step: str, label: str, status: str = "completed") -> None:
            nonlocal timeline_step
            if on_progress:
                on_progress(step, label, status)
            if status == "completed":
                timeline_step += 1
                timeline.append(
                    {
                        "step": timeline_step,
                        "action": label,
                        "status": "completed",
                    }
                )

        progress("context", "Collected cluster metadata")
        progress("connect", "Connected to Kubernetes API")

        progress("nodes", "Checked node readiness", "in_progress")
        nodes = self.node_inspector.inspect()
        progress("nodes", "Checked node readiness")
        logger.info("Node inspection complete: {} node(s)", nodes.get("total_nodes", 0))

        progress("pods", "Checked pod failures", "in_progress")
        pods = self.pod_inspector.inspect()
        progress("pods", "Checked pod failures")
        logger.info(
            "Pod inspection complete: {} problematic pod(s)",
            len(pods.get("problematic_pods", [])),
        )

        progress("logs", "Retrieved container logs", "in_progress")
        logs = self.logs_collector.collect(pods.get("problematic_pods", []))
        progress("logs", "Retrieved container logs")
        logger.info("Log collection complete")

        progress("events", "Retrieved cluster events", "in_progress")
        events = self.events_analyzer.analyze()
        progress("events", "Retrieved cluster events")
        logger.info(
            "Events analysis complete: {} finding(s)",
            len(events.get("findings", [])),
        )

        progress("deployments", "Checked deployment health", "in_progress")
        deployments = self.deployment_inspector.inspect()
        progress("deployments", "Checked deployment health")
        logger.info(
            "Deployment inspection complete: {} unhealthy deployment(s)",
            len(deployments.get("unhealthy_deployments", [])),
        )

        progress("network", "Checked services and endpoints", "in_progress")
        network = self.network_inspector.inspect()
        progress("network", "Checked services and endpoints")
        logger.info(
            "Network inspection complete: {} issue(s)",
            len(network.get("issues", [])),
        )

        replicasets = self.replicaset_inspector.inspect()
        logger.info(
            "ReplicaSet inspection complete: {} unhealthy replicaset(s)",
            len(replicasets.get("unhealthy_replicasets", [])),
        )

        ingress = self.ingress_inspector.inspect()
        logger.info(
            "Ingress inspection complete: {} issue(s)",
            len(ingress.get("issues", [])),
        )

        timeline.append(
            {
                "step": len(timeline) + 1,
                "action": "Generated diagnosis",
                "status": "completed",
            }
        )

        investigation = {
            "cluster_context": self.executor.context,
            "nodes": nodes,
            "pods": pods,
            "logs": logs,
            "events": events,
            "deployments": deployments,
            "network": network,
            "replicasets": replicasets,
            "ingress": ingress,
            "timeline": timeline,
        }

        logger.info("Kubernetes investigation complete")
        return investigation


def run_investigation() -> dict:
    """Backward-compatible entry point."""
    return InvestigationService().run()
