from fastapi import APIRouter

from core.gke_validation import get_gke_health_status
from models.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    gke = get_gke_health_status()
    return HealthResponse(
        status=gke.status,
        service="ai-kubernetes-agent",
        kubeconfig_configured=gke.kubeconfig_configured,
        kubeconfig_path=gke.kubeconfig_path,
        kubeconfig_error=gke.kubeconfig_error,
        gcloud_installed=gke.gcloud_installed,
        gcloud_path=gke.gcloud_path,
        gcloud_authenticated=gke.gcloud_authenticated,
        gcloud_accounts=gke.gcloud_accounts,
        kubectl_connected=gke.kubectl_connected,
        current_context=gke.current_context,
        node_count=gke.node_count,
        gke_error=gke.error,
    )
