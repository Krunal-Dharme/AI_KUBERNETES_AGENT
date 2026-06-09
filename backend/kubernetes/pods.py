from datetime import datetime, timezone

from kubernetes.executor import KubectlExecutor, summarize_stderr

UNHEALTHY_WAITING_REASONS = {
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "CreateContainerConfigError",
    "ContainerCreating",
}

UNHEALTHY_TERMINATED_REASONS = {"OOMKilled", "Error"}

UNHEALTHY_PHASES = {"Pending", "Failed"}

STUCK_CONTAINER_CREATING_SECONDS = 300


class PodInspector:
    """Inspect pod health across all namespaces."""

    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        self.executor = executor or KubectlExecutor()

    def inspect(self) -> dict:
        data, result = self.executor.run_json("get", "pods", "-A")

        if data is None:
            return {
                "healthy": False,
                "error": summarize_stderr(result.stderr) or "Failed to fetch pods",
                "problematic_pods": [],
                "total_pods": 0,
            }

        items = data.get("items", [])
        problematic_pods: list[dict] = []

        for pod in items:
            issue = self._detect_pod_issue(pod)
            if issue:
                problematic_pods.append(issue)

        return {
            "healthy": len(problematic_pods) == 0,
            "problematic_pods": problematic_pods,
            "total_pods": len(items),
        }

    def _detect_pod_issue(self, pod: dict) -> dict | None:
        metadata = pod.get("metadata", {})
        status = pod.get("status", {})
        name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", "default")
        phase = status.get("phase", "Unknown")

        container_statuses = status.get("containerStatuses") or []
        init_container_statuses = status.get("initContainerStatuses") or []
        all_statuses = container_statuses + init_container_statuses

        detected_status = None
        details = []

        for container_status in all_statuses:
            container_name = container_status.get("name", "unknown")
            state = container_status.get("state", {})

            waiting = state.get("waiting")
            if waiting:
                reason = waiting.get("reason", "")
                message = waiting.get("message", "")

                if reason in UNHEALTHY_WAITING_REASONS:
                    if reason == "ContainerCreating" and not self._is_stuck_creating(
                        metadata, STUCK_CONTAINER_CREATING_SECONDS
                    ):
                        continue
                    detected_status = reason
                    details.append(
                        f"container '{container_name}' waiting: {reason}"
                        + (f" - {message}" if message else "")
                    )

            terminated = state.get("terminated")
            if terminated:
                reason = terminated.get("reason", "")
                exit_code = terminated.get("exitCode")
                if reason in UNHEALTHY_TERMINATED_REASONS or (
                    exit_code is not None and exit_code != 0
                ):
                    detected_status = reason or "Error"
                    details.append(
                        f"container '{container_name}' terminated: {reason} (exit {exit_code})"
                    )

        if phase in UNHEALTHY_PHASES and not detected_status:
            detected_status = phase
            details.append(f"pod phase is {phase}")

        if not detected_status:
            return None

        return {
            "name": name,
            "namespace": namespace,
            "status": detected_status,
            "phase": phase,
            "details": details,
        }

    def _is_stuck_creating(self, metadata: dict, threshold_seconds: int) -> bool:
        creation_timestamp = metadata.get("creationTimestamp")
        if not creation_timestamp:
            return True

        try:
            created_at = datetime.fromisoformat(
                creation_timestamp.replace("Z", "+00:00")
            )
        except ValueError:
            return True

        age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
        return age_seconds >= threshold_seconds


def inspect_pods() -> dict:
    """Backward-compatible entry point."""
    return PodInspector().inspect()
