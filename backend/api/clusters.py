from fastapi import APIRouter

from kubernetes.clusters import ClusterDiscovery
from models.investigation import ClusterInfo, ClustersResponse

router = APIRouter()


@router.get("/clusters", response_model=ClustersResponse)
def list_clusters() -> ClustersResponse:
    data = ClusterDiscovery().list_clusters()
    return ClustersResponse(
        healthy=data["healthy"],
        error=data.get("error"),
        kubeconfig_path=data.get("kubeconfig_path", ""),
        current_context=data.get("current_context", ""),
        clusters=[ClusterInfo(**cluster) for cluster in data.get("clusters", [])],
    )
