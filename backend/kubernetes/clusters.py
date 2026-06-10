from loguru import logger

from core.config import settings
from core.errors import friendly_kubectl_error
from core.kubeconfig import get_kubeconfig_status
from kubernetes.executor import KubectlExecutor
from kubernetes.kubeconfig_parser import (
    parse_clusters_from_kubeconfig,
    parse_clusters_from_yaml,
)


class ClusterDiscovery:
    """Discover Kubernetes clusters from kubeconfig."""

    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        self.executor = executor or KubectlExecutor()

    def list_clusters(self) -> dict:
        status = get_kubeconfig_status(
            self.executor.kubeconfig_path or settings.kubeconfig_path
        )
        kubeconfig_path = self.executor.kubeconfig_path or settings.kubeconfig_path

        if not status["configured"]:
            return {
                "healthy": False,
                "error": status["error"],
                "kubeconfig_path": kubeconfig_path or status["path"],
                "current_context": "",
                "clusters": [],
            }

        if status.get("mode") == "ssh":
            return self._list_clusters_via_kubectl(kubeconfig_path, status["path"])

        parsed = parse_clusters_from_kubeconfig(kubeconfig_path)
        if parsed["healthy"]:
            return {**parsed, "kubeconfig_path": kubeconfig_path}

        logger.warning(
            "Direct kubeconfig parse failed ({}), falling back to kubectl",
            parsed.get("error"),
        )
        return self._list_clusters_via_kubectl(kubeconfig_path, kubeconfig_path)

    def _list_clusters_via_kubectl(self, kubeconfig_path: str, display_path: str) -> dict:
        result = self.executor.run(
            "config",
            "view",
            "--kubeconfig",
            kubeconfig_path,
            "--minify=false",
        )

        if not result.success or not result.stdout.strip():
            return {
                "healthy": False,
                "error": friendly_kubectl_error(result),
                "kubeconfig_path": display_path,
                "current_context": "",
                "clusters": [],
            }

        parsed = parse_clusters_from_yaml(result.stdout)
        logger.info("Discovered {} cluster context(s) via kubectl", len(parsed["clusters"]))

        return {
            **parsed,
            "kubeconfig_path": display_path,
        }

    def verify_connection(self, context: str | None = None) -> dict:
        executor = KubectlExecutor(
            kubeconfig_path=self.executor.kubeconfig_path,
            context=context,
        )

        result = executor.run("get", "nodes", "--request-timeout=15s", timeout=20)

        if not result.success:
            return {
                "connected": False,
                "context": context or "default",
                "error": friendly_kubectl_error(result),
            }

        node_count = len(
            [line for line in result.stdout.splitlines() if line.strip() and not line.startswith("NAME")]
        )

        return {
            "connected": True,
            "context": context or executor.context or "current",
            "node_count": node_count,
            "error": None,
        }
