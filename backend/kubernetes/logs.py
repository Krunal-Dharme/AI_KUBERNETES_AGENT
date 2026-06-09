import re

from kubernetes.executor import KubectlExecutor

MAX_LOG_LINES = 80
MAX_PODS_TO_COLLECT = 10

RELEVANT_PATTERNS = [
    re.compile(r"exception", re.IGNORECASE),
    re.compile(r"error", re.IGNORECASE),
    re.compile(r"failed", re.IGNORECASE),
    re.compile(r"connection refused", re.IGNORECASE),
    re.compile(r"connection reset", re.IGNORECASE),
    re.compile(r"no such file", re.IGNORECASE),
    re.compile(r"env(?:ironment)? variable", re.IGNORECASE),
    re.compile(r"imagepull", re.IGNORECASE),
    re.compile(r"crash", re.IGNORECASE),
    re.compile(r"panic", re.IGNORECASE),
    re.compile(r"fatal", re.IGNORECASE),
    re.compile(r"startup", re.IGNORECASE),
]


class LogsCollector:
    """Collect concise logs from problematic pods."""

    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        self.executor = executor or KubectlExecutor()

    def collect(self, problematic_pods: list[dict]) -> dict:
        if not problematic_pods:
            return {
                "collected": False,
                "message": "No problematic pods to collect logs from",
                "entries": [],
            }

        entries = []
        pods_to_check = problematic_pods[:MAX_PODS_TO_COLLECT]

        for pod in pods_to_check:
            name = pod.get("name")
            namespace = pod.get("namespace", "default")
            if not name:
                continue

            log_entry = self._collect_pod_logs(name, namespace, pod.get("status", ""))
            entries.append(log_entry)

        return {
            "collected": True,
            "pods_checked": len(entries),
            "entries": entries,
        }

    def _collect_pod_logs(self, name: str, namespace: str, status: str) -> dict:
        raw_logs = self._fetch_logs(name, namespace, previous=False)
        previous_logs = ""

        if status == "CrashLoopBackOff":
            previous_logs = self._fetch_logs(name, namespace, previous=True)

        combined = self._merge_log_sources(raw_logs, previous_logs)
        concise_logs = self._extract_relevant_lines(combined)

        return {
            "pod": name,
            "namespace": namespace,
            "status": status,
            "log_lines_returned": len(concise_logs.splitlines()) if concise_logs else 0,
            "logs": concise_logs or "No relevant log lines found",
        }

    def _fetch_logs(self, name: str, namespace: str, previous: bool) -> str:
        args = ["logs", name, "-n", namespace, f"--tail={MAX_LOG_LINES}"]
        if previous:
            args.append("--previous")

        result = self.executor.run(*args, timeout=30)

        if not result.success:
            return result.stderr.strip() or "Unable to fetch logs"

        return result.stdout.strip()

    def _merge_log_sources(self, current: str, previous: str) -> str:
        parts = []
        if current:
            parts.append(f"--- current ---\n{current}")
        if previous and previous != current:
            parts.append(f"--- previous ---\n{previous}")
        return "\n\n".join(parts)

    def _extract_relevant_lines(self, raw_logs: str) -> str:
        if not raw_logs:
            return ""

        lines = raw_logs.splitlines()
        relevant = [line for line in lines if any(p.search(line) for p in RELEVANT_PATTERNS)]

        if relevant:
            return "\n".join(relevant[-MAX_LOG_LINES:])

        return "\n".join(lines[-30:])
