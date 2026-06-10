"use client";

import { useState } from "react";

import {
  limitAnalysis,
  safeString,
  toBulletLines,
  toTextLines,
} from "@/lib/report-format";
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
  const label = SEVERITY_STYLES[severity] ? severity : "Medium";
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLES[label]}`}>
      {label}
    </span>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <ul className="mt-1 list-disc space-y-1 pl-5 text-slate-300">
      {items.map((item, i) => (
        <li key={`${i}-${item.slice(0, 24)}`} className="whitespace-pre-wrap break-words">
          {item}
        </li>
      ))}
    </ul>
  );
}

function CommandList({ commands }: { commands: string[] }) {
  if (!commands.length) return null;
  return (
    <div className="mt-1 space-y-1">
      {commands.map((cmd, i) => (
        <code
          key={`${i}-${cmd.slice(0, 24)}`}
          className="block whitespace-pre-wrap break-all rounded bg-slate-900 px-3 py-2 font-mono text-xs text-emerald-300"
        >
          {cmd}
        </code>
      ))}
    </div>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(
    finding.severity === "Critical" || finding.severity === "High",
  );

  const evidence = toTextLines(finding.evidence as unknown);
  const commands = toTextLines(finding.investigation_commands as unknown, 3, 500);
  const verification = toTextLines(
    finding.remediation?.verification_steps as unknown,
    3,
    500,
  );
  const confidenceReasons = toBulletLines(
    finding.confidence_reasoning as unknown,
  );
  const rootCause = safeString(finding.root_cause);
  const analysis = limitAnalysis(finding.explanation);
  const immediateFix = safeString(finding.remediation?.immediate_fix);

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
          {rootCause && (
            <div>
              <p className="text-slate-500">Root Cause</p>
              <p className="mt-1 whitespace-pre-wrap break-words font-medium text-white">
                {rootCause}
              </p>
            </div>
          )}

          {analysis && (
            <div>
              <p className="text-slate-500">Analysis</p>
              <p className="mt-1 whitespace-pre-wrap break-words text-slate-300">{analysis}</p>
            </div>
          )}

          {evidence.length > 0 && (
            <div>
              <p className="text-slate-500">Evidence</p>
              <BulletList items={evidence} />
            </div>
          )}

          {commands.length > 0 && (
            <div>
              <p className="text-slate-500">Investigation Commands</p>
              <CommandList commands={commands} />
            </div>
          )}

          {immediateFix && (
            <div>
              <p className="text-slate-500">Immediate Fix</p>
              <p className="mt-1 whitespace-pre-wrap break-words text-slate-300">
                {immediateFix}
              </p>
            </div>
          )}

          {verification.length > 0 && (
            <div>
              <p className="text-slate-500">Verification</p>
              <CommandList commands={verification} />
            </div>
          )}

          <div>
            <p className="text-slate-500">Confidence: {finding.confidence ?? 0}%</p>
            {confidenceReasons.length > 0 && <BulletList items={confidenceReasons} />}
          </div>
        </div>
      )}
    </article>
  );
}

export function DiagnosisCard({ diagnosis, clusterContext }: DiagnosisCardProps) {
  if (!diagnosis) return null;

  const isHealthy = Boolean(diagnosis.cluster_healthy);
  const findings = Array.isArray(diagnosis.findings) ? diagnosis.findings : [];

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

      {findings.length > 0 ? (
        <div className="space-y-3">
          <p className="text-sm text-slate-500">Findings ({findings.length})</p>
          {findings.map((finding) => (
            <FindingCard key={finding.id || `${finding.namespace}-${finding.affected_resource}`} finding={finding} />
          ))}
        </div>
      ) : (
        !isHealthy && (
          <div className="space-y-4 text-sm">
            <div>
              <p className="text-slate-500">Root Cause</p>
              <p className="mt-1 whitespace-pre-wrap break-words font-medium text-white">
                {safeString(diagnosis.root_cause)}
              </p>
            </div>
            {diagnosis.explanation && (
              <div>
                <p className="text-slate-500">Analysis</p>
                <p className="mt-1 whitespace-pre-wrap break-words text-slate-300">
                  {limitAnalysis(diagnosis.explanation)}
                </p>
              </div>
            )}
            {diagnosis.fix && (
              <div>
                <p className="text-slate-500">Immediate Fix</p>
                <p className="mt-1 whitespace-pre-wrap break-words text-slate-300">
                  {safeString(diagnosis.fix)}
                </p>
              </div>
            )}
            {diagnosis.kubectl_command && (
              <code className="block whitespace-pre-wrap break-all rounded-lg bg-slate-950 px-3 py-2 font-mono text-xs text-emerald-300">
                {safeString(diagnosis.kubectl_command)}
              </code>
            )}
            <p className="text-slate-500">Confidence: {diagnosis.confidence ?? 0}%</p>
            <BulletList items={toBulletLines(diagnosis.confidence_reasoning)} />
          </div>
        )
      )}
    </section>
  );
}
