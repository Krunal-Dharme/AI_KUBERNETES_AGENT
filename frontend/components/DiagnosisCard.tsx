"use client";

import type { Diagnosis } from "@/types/investigation";

interface DiagnosisCardProps {
  diagnosis: Diagnosis | null;
  clusterContext?: string | null;
}

export function DiagnosisCard({ diagnosis, clusterContext }: DiagnosisCardProps) {
  if (!diagnosis) return null;

  const isHealthy = diagnosis.cluster_healthy;

  return (
    <section
      className={`rounded-xl border p-5 ${
        isHealthy
          ? "border-emerald-700 bg-emerald-950/20"
          : "border-slate-800 bg-slate-900/60"
      }`}
    >
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
        Diagnosis
        {clusterContext && (
          <span className="ml-2 normal-case text-slate-500">— {clusterContext}</span>
        )}
      </h2>

      {isHealthy && (
        <div className="mb-4 rounded-lg border border-emerald-700/50 bg-emerald-950/40 px-3 py-2 text-sm text-emerald-300">
          No critical Kubernetes issues detected. Cluster appears healthy.
        </div>
      )}

      <div className="space-y-4 text-sm">
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

        <div>
          <p className="text-slate-500">Command</p>
          <code className="mt-1 block rounded-lg bg-slate-950 px-3 py-2 font-mono text-xs text-emerald-300">
            {diagnosis.kubectl_command}
          </code>
        </div>

        <div>
          <p className="text-slate-500">Confidence</p>
          <p className="mt-1 text-2xl font-bold text-blue-400">{diagnosis.confidence}%</p>
        </div>
      </div>
    </section>
  );
}
