"use client";

import { limitAnalysis, safeString } from "@/lib/report-format";
import type { ClusterHealthSummary, Diagnosis } from "@/types/investigation";

interface ExecutiveDashboardProps {
  diagnosis: Diagnosis;
  isHealthy: boolean;
}

function healthScoreColor(score: number): string {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-amber-400";
  return "text-red-400";
}

function healthScoreRing(score: number): string {
  if (score >= 80) return "border-emerald-500/50 bg-emerald-950/30";
  if (score >= 60) return "border-amber-500/50 bg-amber-950/30";
  return "border-red-500/50 bg-red-950/30";
}

function CountBadge({
  label,
  count,
  tone,
}: {
  label: string;
  count: number;
  tone: "critical" | "high" | "medium";
}) {
  const styles = {
    critical: "border-red-700/60 bg-red-950/50 text-red-300",
    high: "border-orange-700/60 bg-orange-950/50 text-orange-300",
    medium: "border-amber-700/60 bg-amber-950/50 text-amber-300",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${styles[tone]}`}
    >
      <span>{label}</span>
      <span className="rounded-full bg-black/20 px-1.5 py-0.5 text-sm font-bold">{count}</span>
    </span>
  );
}

function buildExecutiveSummary(diagnosis: Diagnosis, isHealthy: boolean): string {
  const summary = safeString(diagnosis.executive_summary).trim();
  if (summary) return limitAnalysis(summary, 4);

  if (isHealthy) {
    return "The cluster appears healthy with no critical issues detected. Continue monitoring workloads and events.";
  }

  const parts: string[] = [];
  if (diagnosis.root_cause) {
    parts.push(safeString(diagnosis.root_cause));
  }
  if (diagnosis.explanation) {
    parts.push(limitAnalysis(diagnosis.explanation, 2));
  }
  return parts.join(" ").trim() || "Investigation completed. Review findings below for details.";
}

function buildOverview(summary: ClusterHealthSummary | undefined, diagnosis: Diagnosis) {
  const findings = diagnosis.findings ?? [];
  const critical =
    summary?.critical_findings ??
    findings.filter((f) => f.severity === "Critical").length;
  const high =
    summary?.high_findings ?? findings.filter((f) => f.severity === "High").length;
  const medium =
    summary?.medium_findings ??
    findings.filter((f) => f.severity === "Medium").length;

  const crashloop =
    summary?.pods_crashloop ??
    findings.filter((f) => f.current_state?.includes("CrashLoop")).length;

  return {
    nodes: summary?.nodes_ready ?? "—",
    podsRunning: summary?.pods_running ?? 0,
    podsPending: summary?.pods_pending ?? 0,
    podsFailed: summary?.pods_failed ?? 0,
    podsCrashloop: crashloop,
    deploymentsHealthy: summary?.deployments_healthy ?? 0,
    deploymentsDegraded: summary?.deployments_degraded ?? 0,
    missingEndpoints: summary?.services_missing_endpoints ?? 0,
    critical,
    high,
    medium,
  };
}

export function ExecutiveDashboard({ diagnosis, isHealthy }: ExecutiveDashboardProps) {
  const score = diagnosis.cluster_health_score ?? (isHealthy ? 100 : 50);
  const summary = diagnosis.cluster_health_summary;
  const overview = buildOverview(summary, diagnosis);
  const executiveSummary = buildExecutiveSummary(diagnosis, isHealthy);

  return (
    <div className="sticky top-0 z-10 -mx-5 -mt-5 mb-6 space-y-4 border-b border-slate-800 bg-slate-950/95 px-5 pb-5 pt-5 backdrop-blur-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1 space-y-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Executive Summary
            </p>
            <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-slate-200">
              {executiveSummary}
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Cluster Overview
            </p>
            <div className="mt-2 grid gap-1.5 text-sm text-slate-300 sm:grid-cols-2">
              <p>
                <span className="text-slate-500">Nodes:</span> {overview.nodes} Ready
              </p>
              <p>
                <span className="text-slate-500">Pods:</span> {overview.podsRunning} Running,{" "}
                {overview.podsPending} Pending
                {overview.podsFailed > 0 && `, ${overview.podsFailed} Failed`}
                {overview.podsCrashloop > 0 && `, ${overview.podsCrashloop} CrashLoopBackOff`}
              </p>
              <p>
                <span className="text-slate-500">Deployments:</span> {overview.deploymentsHealthy}{" "}
                Healthy, {overview.deploymentsDegraded} Degraded
              </p>
              <p>
                <span className="text-slate-500">Missing Endpoints:</span> {overview.missingEndpoints}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <CountBadge label="Critical" count={overview.critical} tone="critical" />
            <CountBadge label="High" count={overview.high} tone="high" />
            <CountBadge label="Medium" count={overview.medium} tone="medium" />
          </div>
        </div>

        <div
          className={`flex shrink-0 flex-col items-center justify-center rounded-xl border px-6 py-4 ${healthScoreRing(score)}`}
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Cluster Health Score
          </p>
          <p className={`mt-1 text-4xl font-bold tabular-nums ${healthScoreColor(score)}`}>
            {score}%
          </p>
        </div>
      </div>
    </div>
  );
}
