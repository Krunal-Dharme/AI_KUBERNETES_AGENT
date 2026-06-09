from typing import Any

from pydantic import BaseModel, Field


class ClusterInfo(BaseModel):
    name: str
    cluster: str
    server: str
    is_current: bool = False
    is_gke: bool = False


class ClustersResponse(BaseModel):
    healthy: bool
    error: str | None = None
    kubeconfig_path: str
    current_context: str
    clusters: list[ClusterInfo]


class InvestigationPayload(BaseModel):
    cluster_context: str | None = None
    nodes: dict[str, Any] = {}
    pods: dict[str, Any]
    logs: dict[str, Any]
    events: dict[str, Any]
    deployments: dict[str, Any]
    network: dict[str, Any]


class Diagnosis(BaseModel):
    root_cause: str
    explanation: str
    fix: str
    kubectl_command: str
    confidence: int = Field(ge=0, le=100)
    prevention_recommendation: str = ""
    confidence_reasoning: str = ""
    cluster_healthy: bool = False


class InvestigateRequest(BaseModel):
    session_id: str | None = None
    cluster_context: str | None = None


class InvestigateResponse(BaseModel):
    status: str
    cluster_context: str | None = None
    investigation: InvestigationPayload
    diagnosis: Diagnosis
    session_id: str | None = None
