from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.kubeconfig import resolve_kubeconfig_path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    kubeconfig_path: str = ""

    # Remote kubectl via SSH when local kubeconfig is unavailable (Windows dev → GCP VM).
    kubectl_ssh_host: str = ""
    kubectl_ssh_kubeconfig: str = "/home/kunudharme/.kube/config"
    kubectl_ssh_options: str = "-o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"

    # When true, fail startup unless gcloud auth and kubectl get nodes succeed.
    gke_validate_on_startup: bool = False

    insforge_base_url: str = ""
    insforge_anon_key: str = ""

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://34.47.189.50:3000",
        "http://34.47.189.50:8000",
    ]

    @model_validator(mode="after")
    def resolve_kubeconfig(self) -> "Settings":
        resolved = resolve_kubeconfig_path(self.kubeconfig_path)
        if resolved and Path(resolved).is_file():
            self.kubeconfig_path = resolved
        elif not self.kubeconfig_path:
            self.kubeconfig_path = resolved
        return self


settings = Settings()
