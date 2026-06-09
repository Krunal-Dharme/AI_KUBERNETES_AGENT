"use client";

import type { ProgressStep } from "@/types/investigation";

interface InvestigationProgressProps {
  steps: ProgressStep[];
  isRunning: boolean;
  clusterName?: string;
}

function StepIcon({ status }: { status: ProgressStep["status"] }) {
  if (status === "completed") {
    return <span className="text-emerald-400">✓</span>;
  }
  if (status === "in_progress") {
    return (
      <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
    );
  }
  return <span className="text-slate-600">○</span>;
}

export function InvestigationProgress({
  steps,
  isRunning,
  clusterName,
}: InvestigationProgressProps) {
  if (!isRunning && steps.every((step) => step.status === "pending")) {
    return null;
  }

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-400">
        Investigation Status
      </h2>
      {isRunning && (
        <p className="mb-4 text-sm text-blue-300">
          Investigating Kubernetes cluster
          {clusterName ? `: ${clusterName}` : "..."}
        </p>
      )}

      <ul className="space-y-2">
        {steps.map((step) => (
          <li key={step.id} className="flex items-center gap-3 text-sm">
            <StepIcon status={step.status} />
            <span
              className={
                step.status === "completed"
                  ? "text-slate-200"
                  : step.status === "in_progress"
                    ? "text-blue-300"
                    : "text-slate-500"
              }
            >
              {step.label}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
