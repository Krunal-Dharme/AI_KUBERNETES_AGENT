from fastapi import APIRouter, HTTPException
from loguru import logger

from ai.root_cause_analyzer import AIAgent
from core.kubeconfig import get_kubeconfig_status
from kubernetes.clusters import ClusterDiscovery
from kubernetes.executor import KubectlExecutor
from models.investigation import (
    Diagnosis,
    InvestigateRequest,
    InvestigateResponse,
    InvestigationPayload,
)
from services.health_check import healthy_cluster_diagnosis, is_cluster_healthy
from services.investigation import InvestigationService
from services.progress import ProgressPublisher

router = APIRouter()


@router.post("/investigate", response_model=InvestigateResponse)
def investigate(request: InvestigateRequest | None = None) -> InvestigateResponse:
    request = request or InvestigateRequest()
    session_id = request.session_id
    cluster_context = request.cluster_context

    kubeconfig_status = get_kubeconfig_status()
    if not kubeconfig_status["configured"]:
        raise HTTPException(status_code=400, detail=kubeconfig_status["error"])

    discovery = ClusterDiscovery()
    available = discovery.list_clusters()

    if not available["healthy"]:
        raise HTTPException(status_code=400, detail=available.get("error", "No clusters found"))

    if cluster_context:
        context_names = {c["name"] for c in available["clusters"]}
        if cluster_context not in context_names:
            raise HTTPException(
                status_code=400,
                detail=f"Cluster context '{cluster_context}' not found in kubeconfig.",
            )
    else:
        cluster_context = available.get("current_context") or available["clusters"][0]["name"]

    logger.info(
        "POST /investigate - cluster={} session={}",
        cluster_context,
        session_id,
    )

    publisher = ProgressPublisher(session_id)
    on_progress = publisher.callback()

    publisher.publish("context", "Loading Cluster Context", "in_progress")
    publisher.publish("context", "Loading Cluster Context", "completed")

    connection = discovery.verify_connection(cluster_context)
    publisher.publish("connect", "Connecting to GKE Cluster", "in_progress")

    if not connection["connected"]:
        publisher.publish("connect", "Connecting to GKE Cluster", "completed")
        raise HTTPException(status_code=503, detail=connection["error"])

    publisher.publish("connect", "Connecting to GKE Cluster", "completed")

    executor = KubectlExecutor(context=cluster_context)
    investigation_data = InvestigationService(executor).run(on_progress=on_progress)

    cluster_healthy = is_cluster_healthy(investigation_data)

    publisher.publish("ai", "AI Reasoning", "in_progress")

    if cluster_healthy:
        diagnosis_data = healthy_cluster_diagnosis(cluster_context)
        diagnosis_data["cluster_healthy"] = True
        publisher.publish("complete", "Cluster Healthy", "completed")
    else:
        diagnosis_data = AIAgent().diagnose(investigation_data)
        diagnosis_data["cluster_healthy"] = False
        publisher.publish("ai", "AI Reasoning", "completed")
        publisher.publish("complete", "Root Cause Found", "completed")

    return InvestigateResponse(
        status="success",
        cluster_context=cluster_context,
        investigation=InvestigationPayload(**investigation_data),
        diagnosis=Diagnosis(**diagnosis_data),
        session_id=session_id,
    )
