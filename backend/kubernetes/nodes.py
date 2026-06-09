from kubernetes.executor import KubectlExecutor, summarize_stderr


class NodeInspector:
    """Inspect node health in the selected cluster."""

    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        self.executor = executor or KubectlExecutor()

    def inspect(self) -> dict:
        data, result = self.executor.run_json("get", "nodes")

        if data is None:
            return {
                "healthy": False,
                "error": summarize_stderr(result.stderr) or "Failed to fetch nodes",
                "total_nodes": 0,
                "not_ready_nodes": [],
            }

        items = data.get("items", [])
        not_ready = []

        for node in items:
            name = node.get("metadata", {}).get("name", "unknown")
            conditions = node.get("status", {}).get("conditions", [])
            ready = next((c for c in conditions if c.get("type") == "Ready"), {})
            if ready.get("status") != "True":
                not_ready.append(
                    {
                        "name": name,
                        "reason": ready.get("reason", "NotReady"),
                        "message": ready.get("message", "")[:200],
                    }
                )

        return {
            "healthy": len(not_ready) == 0,
            "total_nodes": len(items),
            "not_ready_nodes": not_ready,
        }
