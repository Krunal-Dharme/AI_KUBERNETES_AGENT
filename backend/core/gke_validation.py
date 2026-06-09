import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field

from loguru import logger

from core.config import settings
from core.kubeconfig import get_kubeconfig_status


@dataclass
class GkeHealthStatus:
    gcloud_installed: bool = False
    gcloud_path: str = ""
    gcloud_authenticated: bool = False
    gcloud_accounts: list[str] = field(default_factory=list)
    kubectl_connected: bool = False
    current_context: str = ""
    node_count: int = 0
    kubeconfig_configured: bool = False
    kubeconfig_path: str = ""
    kubeconfig_error: str | None = None
    error: str | None = None

    @property
    def ready(self) -> bool:
        return (
            self.kubeconfig_configured
            and self.gcloud_installed
            and self.gcloud_authenticated
            and self.kubectl_connected
            and bool(self.current_context)
        )

    @property
    def status(self) -> str:
        return "healthy" if self.ready else "unhealthy"


def _gke_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("USE_GKE_GCLOUD_AUTH_PLUGIN", "True")
    if settings.kubeconfig_path:
        env["KUBECONFIG"] = settings.kubeconfig_path
    cloudsdk = os.environ.get("CLOUDSDK_CONFIG", "/root/.config/gcloud")
    env["CLOUDSDK_CONFIG"] = cloudsdk
    return env


def _run_command(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_gke_env(),
    )


def check_gcloud_installed() -> tuple[bool, str]:
    path = shutil.which("gcloud")
    return bool(path), path or ""


def check_gcloud_auth() -> tuple[bool, list[str]]:
    installed, path = check_gcloud_installed()
    if not installed:
        return False, []

    result = _run_command([path, "auth", "list", "--format=json"], timeout=20)
    if result.returncode != 0:
        logger.warning("gcloud auth list failed: {}", result.stderr.strip())
        return False, []

    try:
        accounts = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return False, []

    active = [
        item.get("account", "")
        for item in accounts
        if item.get("status") == "ACTIVE" and item.get("account")
    ]
    return bool(active), active


def check_kubectl_connectivity() -> tuple[bool, str, int, str | None]:
    kubeconfig = get_kubeconfig_status()
    if not kubeconfig["configured"] or kubeconfig.get("mode") == "ssh":
        return False, "", 0, kubeconfig.get("error")

    kubeconfig_path = settings.kubeconfig_path
    if not kubeconfig_path:
        return False, "", 0, "Kubeconfig path is not configured."

    context_result = _run_command(
        ["kubectl", f"--kubeconfig={kubeconfig_path}", "config", "current-context"],
        timeout=15,
    )
    current_context = context_result.stdout.strip() if context_result.returncode == 0 else ""

    nodes_result = _run_command(
        [
            "kubectl",
            f"--kubeconfig={kubeconfig_path}",
            "get",
            "nodes",
            "--request-timeout=20s",
            "--no-headers",
        ],
        timeout=30,
    )

    if nodes_result.returncode != 0:
        error = nodes_result.stderr.strip() or nodes_result.stdout.strip() or "kubectl get nodes failed"
        return False, current_context, 0, error

    node_count = len([line for line in nodes_result.stdout.splitlines() if line.strip()])
    return True, current_context, node_count, None


def get_gke_health_status() -> GkeHealthStatus:
    kubeconfig = get_kubeconfig_status()
    status = GkeHealthStatus(
        kubeconfig_configured=kubeconfig["configured"],
        kubeconfig_path=kubeconfig["path"],
        kubeconfig_error=kubeconfig.get("error"),
    )

    status.gcloud_installed, status.gcloud_path = check_gcloud_installed()
    if not status.gcloud_installed:
        status.error = "gcloud is not installed or not in PATH."
        return status

    status.gcloud_authenticated, status.gcloud_accounts = check_gcloud_auth()
    if not status.gcloud_authenticated:
        status.error = (
            "gcloud is installed but no active account was found. "
            "Ensure /root/.config/gcloud is mounted and contains valid credentials."
        )
        return status

    connected, context, node_count, kubectl_error = check_kubectl_connectivity()
    status.kubectl_connected = connected
    status.current_context = context
    status.node_count = node_count

    if not connected:
        status.error = kubectl_error or "kubectl could not reach the GKE cluster."
        if "executable file not found" in (kubectl_error or "").lower() and "gcloud" in (kubectl_error or "").lower():
            status.error = (
                "GKE authentication failed: gke-gcloud-auth-plugin could not run gcloud. "
                "Install google-cloud-cli in the backend image."
            )

    return status


def validate_gke_startup() -> GkeHealthStatus:
    """Validate GKE access during startup. Raises RuntimeError when unavailable."""
    status = get_gke_health_status()

    logger.info("GKE startup validation:")
    logger.info("  gcloud: {} ({})", status.gcloud_path or "missing", status.gcloud_installed)
    logger.info("  gcloud accounts: {}", ", ".join(status.gcloud_accounts) or "none")
    logger.info("  kubeconfig: {}", status.kubeconfig_path)
    logger.info("  context: {}", status.current_context or "none")
    logger.info("  kubectl connected: {} ({} nodes)", status.kubectl_connected, status.node_count)

    if not status.ready:
        raise RuntimeError(status.error or "GKE authentication is unavailable.")

    logger.info("GKE startup validation passed")
    return status
