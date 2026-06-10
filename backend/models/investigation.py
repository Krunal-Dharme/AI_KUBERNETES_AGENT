from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["Critical", "High", "Medium", "Low", "Info"]


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


class Remediation(BaseModel):
    immediate_fix: str = ""
    verification_steps: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    id: str
    title: str
    severity: Severity
    category: str
    affected_resource: str
    namespace: str
    resource_type: str
    current_state: str
    evidence: list[str] = Field(default_factory=list)
    root_cause: str = ""
    explanation: str = ""
    investigation_commands: list[str] = Field(default_factory=list)
    remediation: Remediation = Field(default_factory=Remediation)
    confidence: int = Field(default=0, ge=0, le=100)
    confidence_reasoning: str = ""


class ClusterHealthSummary(BaseModel):
    nodes_ready: str = ""
    nodes_total: int = 0
    pods_running: int = 0
    pods_failed: int = 0
    pods_pending: int = 0
    pods_total: int = 0
    deployments_healthy: int = 0
    deployments_degraded: int = 0
    services_missing_endpoints: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    warning_findings: int = 0


class TimelineStep(BaseModel):
    step: int
    action: str
    status: str = "completed"


class InvestigationPayload(BaseModel):
    cluster_context: str | None = None
    nodes: dict[str, Any] = {}
    pods: dict[str, Any]
    logs: dict[str, Any]
    events: dict[str, Any]
    deployments: dict[str, Any]
    network: dict[str, Any]
    replicasets: dict[str, Any] = {}
    ingress: dict[str, Any] = {}
    timeline: list[TimelineStep] = Field(default_factory=list)


class Diagnosis(BaseModel):
    # Backward-compatible primary fields (first/most severe finding)
    root_cause: str
    explanation: str
    fix: str
    kubectl_command: str
    confidence: int = Field(ge=0, le=100)
    prevention_recommendation: str = ""
    confidence_reasoning: str = ""
    cluster_healthy: bool = False

    # SRE report extensions
    executive_summary: str = ""
    cluster_health_score: int = Field(default=100, ge=0, le=100)
    cluster_health_summary: ClusterHealthSummary = Field(default_factory=ClusterHealthSummary)
    investigation_timeline: list[TimelineStep] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    remediation_steps: list[str] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    rollback_commands: list[str] = Field(default_factory=list)


class InvestigateRequest(BaseModel):
    session_id: str | None = None
    cluster_context: str | None = None


class InvestigateResponse(BaseModel):
    status: str
    cluster_context: str | None = None
    investigation: InvestigationPayload
    diagnosis: Diagnosis
    session_id: str | None = None
