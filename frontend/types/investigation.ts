export type Severity = "Critical" | "High" | "Medium" | "Low" | "Info";

export interface Remediation {
  immediate_fix: string;
  verification_steps: string[];
  rollback_steps: string[];
}

export interface Finding {
  id: string;
  title: string;
  severity: Severity;
  category: string;
  affected_resource: string;
  namespace: string;
  resource_type: string;
  current_state: string;
  evidence: string[] | string;
  root_cause?: string | null;
  explanation?: string | null;
  investigation_commands: string[] | string;
  remediation?: Remediation | null;
  confidence?: number | null;
  confidence_reasoning?: string | string[] | null;
}

export interface ClusterHealthSummary {
  nodes_ready: string;
  nodes_total: number;
  pods_running: number;
  pods_failed: number;
  pods_pending: number;
  pods_total: number;
  deployments_healthy: number;
  deployments_degraded: number;
  services_missing_endpoints: number;
  critical_findings: number;
  high_findings: number;
  warning_findings: number;
}

export interface TimelineStep {
  step: number;
  action: string;
  status: string;
}

export interface Diagnosis {
  root_cause: string;
  explanation: string;
  fix: string;
  kubectl_command: string;
  confidence: number;
  prevention_recommendation?: string;
  confidence_reasoning?: string | string[] | null;
  cluster_healthy?: boolean;
  executive_summary?: string;
  cluster_health_score?: number;
  cluster_health_summary?: ClusterHealthSummary;
  investigation_timeline?: TimelineStep[];
  findings?: Finding[];
  validation_commands?: string[];
  remediation_steps?: string[];
  verification_steps?: string[];
  rollback_commands?: string[];
}

export interface ClusterInfo {
  name: string;
  cluster: string;
  server: string;
  is_current: boolean;
  is_gke: boolean;
}

export interface ClustersResponse {
  healthy: boolean;
  error?: string | null;
  kubeconfig_path: string;
  current_context: string;
  clusters: ClusterInfo[];
}

export interface InvestigationPayload {
  cluster_context?: string | null;
  nodes?: Record<string, unknown>;
  pods: Record<string, unknown>;
  logs: Record<string, unknown>;
  events: Record<string, unknown>;
  deployments: Record<string, unknown>;
  network: Record<string, unknown>;
  replicasets?: Record<string, unknown>;
  ingress?: Record<string, unknown>;
  timeline?: TimelineStep[];
}

export interface InvestigateResponse {
  status: string;
  cluster_context?: string | null;
  investigation: InvestigationPayload;
  diagnosis: Diagnosis;
  session_id?: string | null;
}

export interface InvestigationHistoryItem {
  id: string;
  user_id: string;
  session_id?: string | null;
  root_cause: string;
  namespace: string;
  confidence: number;
  status: string;
  diagnosis?: Diagnosis | null;
  created_at: string;
}

export interface ProgressStep {
  id: string;
  label: string;
  status: "pending" | "in_progress" | "completed";
}

export const INVESTIGATION_STEPS: ProgressStep[] = [
  { id: "context", label: "Loading Cluster Context", status: "pending" },
  { id: "connect", label: "Connecting to GKE Cluster", status: "pending" },
  { id: "nodes", label: "Checking Nodes", status: "pending" },
  { id: "pods", label: "Checking Pods", status: "pending" },
  { id: "logs", label: "Reading Logs", status: "pending" },
  { id: "events", label: "Analyzing Events", status: "pending" },
  { id: "deployments", label: "Inspecting Deployments", status: "pending" },
  { id: "network", label: "Checking Networking", status: "pending" },
  { id: "ai", label: "AI Reasoning", status: "pending" },
  { id: "complete", label: "Diagnosis Ready", status: "pending" },
];
