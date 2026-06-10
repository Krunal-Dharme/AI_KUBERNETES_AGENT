import os
import shutil
from pathlib import Path

from loguru import logger

# Standard mount target when using docker-compose.gke.yml
DOCKER_KUBECONFIG_PATH = "/kube/config"

DEFAULT_CANDIDATE_PATHS = (
    DOCKER_KUBECONFIG_PATH,
    "/var/lib/jenkins/.kube/config",
    "/home/kunudharme/.kube/config",
)


def _explicit_configured_path(configured: str) -> str:
    """Return the kubeconfig path explicitly set via settings or environment."""
    for path in (
        configured.strip(),
        os.environ.get("KUBECONFIG_PATH", "").strip(),
    ):
        if path:
            return path
    return ""


def _expand_candidates(configured: str) -> list[str]:
    candidates: list[str] = []

    def add(path: str) -> None:
        cleaned = path.strip()
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)

    add(configured)
    add(os.environ.get("KUBECONFIG_PATH", ""))

    kubeconfig_env = os.environ.get("KUBECONFIG", "")
    if kubeconfig_env:
        separator = ";" if ";" in kubeconfig_env else ":"
        for part in kubeconfig_env.split(separator):
            add(part)

    for path in DEFAULT_CANDIDATE_PATHS:
        add(path)

    home_config = Path.home() / ".kube" / "config"
    add(str(home_config))

    return candidates


def resolve_kubeconfig_path(configured: str = "") -> str:
    """Resolve the first existing kubeconfig file from env and defaults."""
    explicit = _explicit_configured_path(configured)

    # Honour an explicitly configured path before scanning other defaults.
    if explicit and Path(explicit).is_file():
        resolved = str(Path(explicit).resolve())
        logger.debug("Resolved kubeconfig path (explicit): {}", resolved)
        return resolved

    for path in _expand_candidates(configured):
        if Path(path).is_file():
            resolved = str(Path(path).resolve())
            logger.debug("Resolved kubeconfig path: {}", resolved)
            return resolved

    # Keep the explicitly configured path for clear error messages.
    if explicit:
        return explicit

    for path in _expand_candidates(configured):
        if path:
            return path

    return ""


def is_ssh_kubectl_enabled() -> bool:
    from core.config import settings

    return bool(settings.kubectl_ssh_host.strip())


def get_kubeconfig_status(configured: str | None = None) -> dict:
    """Return kubeconfig configuration status for API responses and startup logs."""
    from core.config import settings

    configured_path = (
        configured
        if configured is not None
        else settings.kubeconfig_path or os.environ.get("KUBECONFIG_PATH", "")
    )
    resolved = resolve_kubeconfig_path(configured_path)
    exists = bool(resolved) and Path(resolved).is_file()
    ssh_enabled = is_ssh_kubectl_enabled()

    mode = "local"
    if exists:
        mode = "local"
    elif ssh_enabled:
        mode = "ssh"

    error = None
    if mode == "local" and not exists:
        if not resolved:
            error = (
                "KUBECONFIG_PATH is not set. Add it to backend/.env, for example:\n"
                "KUBECONFIG_PATH=/home/kunudharme/.kube/config\n\n"
                "If using Docker on your GKE VM, run:\n"
                "docker compose -f docker-compose.yml -f docker-compose.gke.yml up --build\n\n"
                "If the backend runs on Windows but kubeconfig is on your GCP VM, either:\n"
                "1) Run the backend on pipeline-demo (recommended), or\n"
                "2) Set KUBECTL_SSH_HOST=kunudharme@34.47.189.50 in backend/.env"
            )
        else:
            error = (
                f"Kubeconfig file not found at: {resolved}\n\n"
                "If the backend runs in Docker on Windows but kubeconfig is on your GCP VM, "
                "run the backend on pipeline-demo instead, or set KUBECTL_SSH_HOST in backend/.env."
            )
    elif mode == "ssh" and not shutil.which("ssh"):
        error = "KUBECTL_SSH_HOST is set but the ssh client is not available in PATH."

    display_path = resolved
    if mode == "ssh":
        remote_config = settings.kubectl_ssh_kubeconfig or resolved or "/home/kunudharme/.kube/config"
        display_path = f"ssh://{settings.kubectl_ssh_host}{remote_config}"

    configured_ok = (mode == "local" and exists) or (mode == "ssh" and not error)

    return {
        "configured": configured_ok,
        "path": display_path,
        "exists": exists,
        "mode": mode,
        "error": error,
    }
