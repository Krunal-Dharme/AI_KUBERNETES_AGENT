from kubernetes.executor import KubectlExecutor, summarize_stderr

INTERESTING_EVENT_REASONS = {
    "FailedScheduling",
    "BackOff",
    "FailedMount",
    "FailedPull",
    "ErrImagePull",
    "Unhealthy",
    "Failed",
    "Killing",
    "FailedCreate",
}


class EventsAnalyzer:
    """Analyze Kubernetes events for troubleshooting signals."""

    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        self.executor = executor or KubectlExecutor()

    def analyze(self) -> dict:
        data, result = self.executor.run_json(
            "get", "events", "-A", "--sort-by=.lastTimestamp"
        )

        if data is None:
            return {
                "healthy": False,
                "error": summarize_stderr(result.stderr) or "Failed to fetch events",
                "findings": [],
                "total_events": 0,
            }

        items = data.get("items", [])
        findings: list[dict] = []

        for event in items:
            finding = self._analyze_event(event)
            if finding:
                findings.append(finding)

        warning_count = sum(1 for f in findings if f.get("type") == "Warning")

        return {
            "healthy": len(findings) == 0,
            "total_events": len(items),
            "warning_count": warning_count,
            "findings": findings[-50:],
        }

    def _analyze_event(self, event: dict) -> dict | None:
        reason = event.get("reason", "")
        event_type = event.get("type", "")

        if reason not in INTERESTING_EVENT_REASONS and event_type != "Warning":
            return None

        involved = event.get("involvedObject", {})
        message = event.get("message", "")

        return {
            "reason": reason,
            "type": event_type,
            "namespace": event.get("metadata", {}).get("namespace", "default"),
            "object_kind": involved.get("kind", ""),
            "object_name": involved.get("name", ""),
            "message": message[:300],
            "count": event.get("count", 1),
            "last_timestamp": event.get("lastTimestamp")
            or event.get("eventTime")
            or event.get("firstTimestamp", ""),
        }
