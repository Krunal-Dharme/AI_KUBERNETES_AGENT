from collections.abc import Callable

import httpx
from loguru import logger

from core.config import settings

ProgressCallback = Callable[[str, str, str], None]


class ProgressPublisher:
    """Publish investigation progress to InsForge realtime."""

    def __init__(self, session_id: str | None) -> None:
        self.session_id = session_id
        self.enabled = bool(
            session_id and settings.insforge_base_url and settings.insforge_anon_key
        )

    def publish(self, step: str, label: str, status: str = "completed") -> None:
        if not self.enabled or not self.session_id:
            return

        url = (
            f"{settings.insforge_base_url.rstrip('/')}"
            "/api/database/rest/v1/rpc/publish_investigation_progress"
        )
        headers = {
            "apikey": settings.insforge_anon_key,
            "Authorization": f"Bearer {settings.insforge_anon_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "p_session_id": self.session_id,
            "p_step": step,
            "p_label": label,
            "p_status": status,
        }

        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(url, headers=headers, json=payload)

            if response.status_code >= 400:
                logger.warning(
                    "Failed to publish investigation progress ({}): {}",
                    response.status_code,
                    response.text[:200],
                )
            else:
                logger.debug("Published progress: {} - {}", step, status)
        except httpx.RequestError as exc:
            logger.warning("Progress publish network error: {}", exc)

    def callback(self) -> ProgressCallback:
        def on_progress(step: str, label: str, status: str) -> None:
            self.publish(step, label, status)

        return on_progress
