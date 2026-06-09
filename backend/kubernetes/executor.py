import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from core.config import settings
from core.kubeconfig import is_ssh_kubectl_enabled, resolve_kubeconfig_path


@dataclass
class KubectlResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
    command: list[str]


def summarize_stderr(stderr: str) -> str:
    """Return a concise, human-readable kubectl error message."""
    if not stderr:
        return "Command failed"

    for line in reversed(stderr.strip().splitlines()):
        cleaned = line.strip()
        if not cleaned or "memcache.go" in cleaned:
            continue
        if cleaned.startswith("E") and "err=" in cleaned:
            continue
        return cleaned

    lines = [line.strip() for line in stderr.strip().splitlines() if line.strip()]
    return lines[-1] if lines else "Command failed"


class KubectlExecutor:
    """Safely execute kubectl commands via subprocess (local or SSH remote)."""

    def __init__(
        self,
        kubeconfig_path: str | None = None,
        context: str | None = None,
    ) -> None:
        self.kubeconfig_path = resolve_kubeconfig_path(
            kubeconfig_path or settings.kubeconfig_path
        )
        self.context = context

    def _use_ssh(self) -> bool:
        if not is_ssh_kubectl_enabled():
            return False
        if self.kubeconfig_path and Path(self.kubeconfig_path).is_file():
            return False
        return True

    def _build_kubectl_command(self, *args: str) -> list[str]:
        command = ["kubectl"]
        if self.context:
            command.extend(["--context", self.context])
        command.extend(args)
        return command

    def _build_ssh_command(self, kubectl_args: list[str]) -> list[str]:
        remote_kubeconfig = settings.kubectl_ssh_kubeconfig or self.kubeconfig_path
        remote_parts = [f"KUBECONFIG={shlex.quote(remote_kubeconfig)}", "kubectl"]
        if self.context:
            remote_parts.extend(["--context", shlex.quote(self.context)])
        remote_parts.extend(shlex.quote(arg) for arg in kubectl_args)
        remote_command = " ".join(remote_parts)

        ssh_command = ["ssh"]
        if settings.kubectl_ssh_options.strip():
            ssh_command.extend(shlex.split(settings.kubectl_ssh_options))
        ssh_command.extend([settings.kubectl_ssh_host.strip(), remote_command])
        return ssh_command

    def run(self, *args: str, timeout: int = 60) -> KubectlResult:
        kubectl_command = self._build_kubectl_command(*args)

        if self._use_ssh():
            command = self._build_ssh_command(list(args))
            env = os.environ.copy()
        else:
            command = kubectl_command
            env = os.environ.copy()
            if self.kubeconfig_path:
                env["KUBECONFIG"] = self.kubeconfig_path

        logger.info("Running kubectl command: {}", " ".join(command))

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
        except FileNotFoundError:
            missing = "ssh" if self._use_ssh() else "kubectl"
            logger.error("{} binary not found in PATH", missing)
            return KubectlResult(
                success=False,
                stdout="",
                stderr=f"{missing} not found. Ensure {missing} is installed and in PATH.",
                return_code=127,
                command=command,
            )
        except subprocess.TimeoutExpired:
            logger.error("kubectl command timed out: {}", " ".join(command))
            return KubectlResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                return_code=-1,
                command=command,
            )

        if result.returncode != 0:
            logger.warning(
                "kubectl command failed (exit {}): {}",
                result.returncode,
                result.stderr.strip() or result.stdout.strip(),
            )
        else:
            logger.debug("kubectl command succeeded")

        return KubectlResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
            command=command,
        )

    def run_json(self, *args: str, timeout: int = 60) -> tuple[dict | list | None, KubectlResult]:
        """Run kubectl with JSON output and parse the response."""
        result = self.run(*args, "-o", "json", timeout=timeout)

        if not result.success or not result.stdout.strip():
            return None, result

        try:
            return json.loads(result.stdout), result
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse kubectl JSON output: {}", exc)
            result.stderr = f"{result.stderr}\nJSON parse error: {exc}".strip()
            return None, result
