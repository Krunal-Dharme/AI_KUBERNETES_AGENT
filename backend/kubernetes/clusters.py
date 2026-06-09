from loguru import logger

from core.config import settings
from core.errors import friendly_kubectl_error
from core.kubeconfig import get_kubeconfig_status
from kubernetes.executor import KubectlExecutor, summarize_stderr


class ClusterDiscovery:
    """Discover Kubernetes clusters from kubeconfig."""

    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        self.executor = executor or KubectlExecutor()

    def list_clusters(self) -> dict:
        status = get_kubeconfig_status(
            self.executor.kubeconfig_path or settings.kubeconfig_path
        )
        kubeconfig_path = status["path"]

        if not status["configured"]:
            return {
                "healthy": False,
                "error": status["error"],
                "kubeconfig_path": kubeconfig_path,
                "current_context": "",
                "clusters": [],
            }

        config, result = self.executor.run_json("config", "view", "--minify=false")

        if config is None:
            return {
                "healthy": False,
                "error": friendly_kubectl_error(result),
                "kubeconfig_path": kubeconfig_path,
                "current_context": "",
                "clusters": [],
            }

        current_context = config.get("current-context", "")
        cluster_map = {
            item.get("name", ""): item.get("cluster", {})
            for item in config.get("clusters", [])
        }

        clusters = []
        for ctx in config.get("contexts", []):
            name = ctx.get("name", "")
            context = ctx.get("context", {})
            cluster_name = context.get("cluster", "")
            cluster_info = cluster_map.get(cluster_name, {})
            server = cluster_info.get("server", "unknown")

            clusters.append(
                {
                    "name": name,
                    "cluster": cluster_name,
                    "server": server,
                    "is_current": name == current_context,
                    "is_gke": "gke" in name.lower() or "googleapis.com" in server,
                }
            )

        logger.info("Discovered {} cluster context(s)", len(clusters))

        return {
            "healthy": len(clusters) > 0,
            "error": None if clusters else "No cluster contexts found in kubeconfig.",
            "kubeconfig_path": kubeconfig_path,
            "current_context": current_context,
            "clusters": clusters,
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
