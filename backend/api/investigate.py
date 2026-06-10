from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import ValidationError

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
from services.report_builder import build_sre_report

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

    try:
        if cluster_healthy:
            diagnosis_data = healthy_cluster_diagnosis(cluster_context, investigation_data)
            diagnosis_data["cluster_healthy"] = True
            publisher.publish("complete", "Cluster Healthy", "completed")
        else:
            diagnosis_data = AIAgent().diagnose(investigation_data)
            diagnosis_data["cluster_healthy"] = False
            publisher.publish("ai", "AI Reasoning", "completed")
            publisher.publish("complete", "Root Cause Found", "completed")
    except Exception as exc:
        logger.error("Diagnosis build failed, returning rule-based report: {}", exc)
        diagnosis_data = build_sre_report(investigation_data, llm_response=None, cluster_healthy=False)
        diagnosis_data["cluster_healthy"] = False
        diagnosis_data["executive_summary"] = (
            "Investigation completed. AI enrichment failed; showing rule-based findings."
        )
        publisher.publish("ai", "AI Reasoning", "completed")
        publisher.publish("complete", "Root Cause Found", "completed")

    try:
        investigation_payload = InvestigationPayload(**investigation_data)
        diagnosis = Diagnosis(**diagnosis_data)
    except ValidationError as exc:
        logger.error("Response validation failed, returning safe minimal diagnosis: {}", exc)
        investigation_payload = InvestigationPayload(
            cluster_context=investigation_data.get("cluster_context"),
            pods=investigation_data.get("pods", {}),
            logs=investigation_data.get("logs", {}),
            events=investigation_data.get("events", {}),
            deployments=investigation_data.get("deployments", {}),
            network=investigation_data.get("network", {}),
        )
        diagnosis = Diagnosis(
            root_cause="Investigation completed with partial results",
            explanation="Some report fields could not be validated. Review raw investigation data.",
            fix="Re-run investigation or inspect cluster manually.",
            kubectl_command="kubectl get pods -A",
            confidence=50,
            cluster_healthy=cluster_healthy,
            executive_summary="Investigation evidence collected; report formatting encountered validation issues.",
        )

    return InvestigateResponse(
        status="success",
        cluster_context=cluster_context,
        investigation=investigation_payload,
        diagnosis=diagnosis,
        session_id=session_id,
    )
