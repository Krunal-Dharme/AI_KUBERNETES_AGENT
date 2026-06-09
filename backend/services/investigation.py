from collections.abc import Callable

from loguru import logger

from kubernetes.deployments import DeploymentInspector
from kubernetes.events import EventsAnalyzer
from kubernetes.executor import KubectlExecutor
from kubernetes.logs import LogsCollector
from kubernetes.network import NetworkInspector
from kubernetes.nodes import NodeInspector
from kubernetes.pods import PodInspector


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

    def run(self, on_progress: Callable[[str, str, str], None] | None = None) -> dict:
        logger.info(
            "Starting Kubernetes investigation (context={})",
            self.executor.context or "current",
        )

        def progress(step: str, label: str, status: str = "completed") -> None:
            if on_progress:
                on_progress(step, label, status)

        progress("context", "Loading Cluster Context", "completed")

        progress("connect", "Connecting to GKE Cluster", "in_progress")
        progress("connect", "Connecting to GKE Cluster", "completed")

        progress("nodes", "Checking Nodes", "in_progress")
        nodes = self.node_inspector.inspect()
        progress("nodes", "Checking Nodes", "completed")
        logger.info("Node inspection complete: {} node(s)", nodes.get("total_nodes", 0))

        progress("pods", "Checking Pods", "in_progress")
        pods = self.pod_inspector.inspect()
        progress("pods", "Checking Pods", "completed")
        logger.info(
            "Pod inspection complete: {} problematic pod(s)",
            len(pods.get("problematic_pods", [])),
        )

        progress("logs", "Reading Logs", "in_progress")
        logs = self.logs_collector.collect(pods.get("problematic_pods", []))
        progress("logs", "Reading Logs", "completed")
        logger.info("Log collection complete")

        progress("events", "Analyzing Events", "in_progress")
        events = self.events_analyzer.analyze()
        progress("events", "Analyzing Events", "completed")
        logger.info(
            "Events analysis complete: {} finding(s)",
            len(events.get("findings", [])),
        )

        progress("deployments", "Inspecting Deployments", "in_progress")
        deployments = self.deployment_inspector.inspect()
        progress("deployments", "Inspecting Deployments", "completed")
        logger.info(
            "Deployment inspection complete: {} unhealthy deployment(s)",
            len(deployments.get("unhealthy_deployments", [])),
        )

        progress("network", "Checking Networking", "in_progress")
        network = self.network_inspector.inspect()
        progress("network", "Checking Networking", "completed")
        logger.info(
            "Network inspection complete: {} issue(s)",
            len(network.get("issues", [])),
        )

        investigation = {
            "cluster_context": self.executor.context,
            "nodes": nodes,
            "pods": pods,
            "logs": logs,
            "events": events,
            "deployments": deployments,
            "network": network,
        }

        logger.info("Kubernetes investigation complete")
        return investigation


def run_investigation() -> dict:
    """Backward-compatible entry point."""
    return InvestigationService().run()
