from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    kubeconfig_configured: bool = False
    kubeconfig_path: str = ""
    kubeconfig_error: str | None = None
