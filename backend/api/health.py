from fastapi import APIRouter

from core.kubeconfig import get_kubeconfig_status
from models.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    kubeconfig = get_kubeconfig_status()
    return HealthResponse(
        status="healthy",
        service="ai-kubernetes-agent",
        kubeconfig_configured=kubeconfig["configured"],
        kubeconfig_path=kubeconfig["path"],
        kubeconfig_error=kubeconfig["error"],
    )
