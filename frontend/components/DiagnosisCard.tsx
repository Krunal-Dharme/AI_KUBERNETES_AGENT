"use client";

import { useState } from "react";

import type { Diagnosis, Finding, Severity } from "@/types/investigation";

interface DiagnosisCardProps {
  diagnosis: Diagnosis | null;
  clusterContext?: string | null;
}

const SEVERITY_STYLES: Record<Severity, string> = {
  Critical: "border-red-700 bg-red-950/40 text-red-300",
  High: "border-orange-700 bg-orange-950/40 text-orange-300",
  Medium: "border-amber-700 bg-amber-950/40 text-amber-300",
  Low: "border-yellow-700 bg-yellow-950/40 text-yellow-300",
  Info: "border-slate-600 bg-slate-900/60 text-slate-300",
};

function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLES[severity]}`}>
      {severity}
    </span>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(finding.severity === "Critical" || finding.severity === "High");

  return (
    <article className="rounded-lg border border-slate-700 bg-slate-950/60">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <span className="text-sm font-medium text-white">{finding.title}</span>
          </div>
          <p className="text-xs text-slate-500">
            {finding.resource_type}/{finding.affected_resource} — {finding.namespace}
          </p>
        </div>
        <span className="text-xs text-slate-500">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <div className="space-y-4 border-t border-slate-800 px-4 py-4 text-sm">
          <div>
            <p className="text-slate-500">Current State</p>
            <p className="mt-1 text-slate-300">{finding.current_state}</p>
          </div>

          {finding.evidence.length > 0 && (
            <div>
              <p className="text-slate-500">Evidence</p>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-slate-300">
                {finding.evidence.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {finding.root_cause && (
            <div>
              <p className="text-slate-500">Root Cause</p>
              <p className="mt-1 text-white">{finding.root_cause}</p>
            </div>
          )}

          {finding.explanation && (
            <div>
              <p className="text-slate-500">Analysis</p>
              <p className="mt-1 text-slate-300">{finding.explanation}</p>
            </div>
          )}

          {finding.investigation_commands.length > 0 && (
            <div>
              <p className="text-slate-500">Investigation Commands</p>
              <div className="mt-1 space-y-1">
                {finding.investigation_commands.map((cmd) => (
                  <code
                    key={cmd}
                    className="block rounded bg-slate-900 px-3 py-2 font-mono text-xs text-emerald-300"
                  >
                    {cmd}
                  </code>
                ))}
              </div>
            </div>
          )}

          {finding.remediation?.immediate_fix && (
            <div>
              <p className="text-slate-500">Immediate Fix</p>
              <p className="mt-1 text-slate-300">{finding.remediation.immediate_fix}</p>
            </div>
          )}

          {finding.remediation?.verification_steps?.length > 0 && (
            <div>
              <p className="text-slate-500">Verification</p>
              <div className="mt-1 space-y-1">
                {finding.remediation.verification_steps.map((cmd) => (
                  <code
                    key={cmd}
                    className="block rounded bg-slate-900 px-3 py-2 font-mono text-xs text-blue-300"
                  >
                    {cmd}
                  </code>
                ))}
              </div>
            </div>
          )}

          {finding.remediation?.rollback_steps?.length > 0 && (
            <div>
              <p className="text-slate-500">Rollback</p>
              <div className="mt-1 space-y-1">
                {finding.remediation.rollback_steps.map((cmd) => (
                  <code
                    key={cmd}
                    className="block rounded bg-slate-900 px-3 py-2 font-mono text-xs text-amber-300"
                  >
                    {cmd}
                  </code>
                ))}
              </div>
            </div>
          )}

          <div>
            <p className="text-slate-500">Confidence: {finding.confidence}%</p>
            {finding.confidence_reasoning && (
              <p className="mt-1 text-xs text-slate-400">{finding.confidence_reasoning}</p>
            )}
          </div>
        </div>
      )}
    </article>
  );
}

export function DiagnosisCard({ diagnosis, clusterContext }: DiagnosisCardProps) {
  if (!diagnosis) return null;

  const isHealthy = diagnosis.cluster_healthy;
  const findings = diagnosis.findings ?? [];
  const summary = diagnosis.cluster_health_summary;
  const timeline = diagnosis.investigation_timeline ?? [];

  return (
    <section
      className={`rounded-xl border p-5 ${
        isHealthy
          ? "border-emerald-700 bg-emerald-950/20"
          : "border-slate-800 bg-slate-900/60"
      }`}
    >
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
        Investigation Report
        {clusterContext && (
          <span className="ml-2 normal-case text-slate-500">— {clusterContext}</span>
        )}
      </h2>

      {isHealthy && (
        <div className="mb-4 rounded-lg border border-emerald-700/50 bg-emerald-950/40 px-3 py-2 text-sm text-emerald-300">
          No critical Kubernetes issues detected. Cluster appears healthy.
        </div>
      )}

      <div className="space-y-6 text-sm">
        {diagnosis.executive_summary && (
          <div>
            <p className="text-slate-500">Executive Summary</p>
            <p className="mt-1 text-slate-200">{diagnosis.executive_summary}</p>
          </div>
        )}

        {typeof diagnosis.cluster_health_score === "number" && (
          <div className="flex items-center gap-4">
            <div>
              <p className="text-slate-500">Cluster Health Score</p>
              <p className="mt-1 text-3xl font-bold text-blue-400">
                {diagnosis.cluster_health_score}%
              </p>
            </div>
            {summary && (
              <div className="grid flex-1 grid-cols-2 gap-2 text-xs text-slate-400 md:grid-cols-3">
                <p>Nodes: {summary.nodes_ready}</p>
                <p>
                  Pods: {summary.pods_running} running, {summary.pods_failed} failed,{" "}
                  {summary.pods_pending} pending
                </p>
                <p>
                  Deployments: {summary.deployments_healthy} healthy,{" "}
                  {summary.deployments_degraded} degraded
                </p>
                <p>Missing endpoints: {summary.services_missing_endpoints}</p>
                <p>Critical: {summary.critical_findings}</p>
                <p>High: {summary.high_findings}</p>
              </div>
            )}
          </div>
        )}

        {timeline.length > 0 && (
          <div>
            <p className="text-slate-500">Investigation Timeline</p>
            <ol className="mt-2 space-y-1 text-xs text-slate-400">
              {timeline.map((step) => (
                <li key={step.step}>
                  Step {step.step}: {step.action}
                </li>
              ))}
            </ol>
          </div>
        )}

        {findings.length > 0 ? (
          <div className="space-y-3">
            <p className="text-slate-500">
              Findings ({findings.length})
            </p>
            {findings.map((finding) => (
              <FindingCard key={finding.id} finding={finding} />
            ))}
          </div>
        ) : (
          !isHealthy && (
            <div className="space-y-4">
              <div>
                <p className="text-slate-500">Root Cause</p>
                <p className="mt-1 font-medium text-white">{diagnosis.root_cause}</p>
              </div>
              <div>
                <p className="text-slate-500">Explanation</p>
                <p className="mt-1 text-slate-300">{diagnosis.explanation}</p>
              </div>
              <div>
                <p className="text-slate-500">Suggested Fix</p>
                <p className="mt-1 text-slate-300">{diagnosis.fix}</p>
              </div>
              <code className="block rounded-lg bg-slate-950 px-3 py-2 font-mono text-xs text-emerald-300">
                {diagnosis.kubectl_command}
              </code>
            </div>
          )
        )}

        {diagnosis.prevention_recommendation && (
          <div>
            <p className="text-slate-500">Prevention</p>
            <p className="mt-1 text-slate-300">{diagnosis.prevention_recommendation}</p>
          </div>
        )}
      </div>
    </section>
  );
}
