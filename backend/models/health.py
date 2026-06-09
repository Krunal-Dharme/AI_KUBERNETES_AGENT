from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    kubeconfig_configured: bool = False
    kubeconfig_path: str = ""
    kubeconfig_error: str | None = None
    gcloud_installed: bool = False
    gcloud_path: str = ""
    gcloud_authenticated: bool = False
    gcloud_accounts: list[str] = []
    kubectl_connected: bool = False
    current_context: str = ""
    node_count: int = 0
    gke_error: str | None = None
