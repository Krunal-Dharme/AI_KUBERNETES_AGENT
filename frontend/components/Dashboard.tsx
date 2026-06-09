"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { ClusterSelector } from "@/components/ClusterSelector";
import { DiagnosisCard } from "@/components/DiagnosisCard";
import { InvestigationHistory } from "@/components/InvestigationHistory";
import { InvestigationProgress } from "@/components/InvestigationProgress";
import { useInvestigation } from "@/hooks/useInvestigation";
import { useAuth } from "@/lib/auth";

export function Dashboard() {
  const { user, signOut } = useAuth();
  const queryClient = useQueryClient();
  const [selectedCluster, setSelectedCluster] = useState("");

  const { steps, diagnosis, activeCluster, error, isRunning, investigate } =
    useInvestigation(selectedCluster, () => {
      queryClient.invalidateQueries({ queryKey: ["investigation-history"] });
    });

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-8">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">AI Kubernetes Agent</h1>
            <p className="mt-1 text-sm text-slate-400">Signed in as {user?.email}</p>
          </div>
          <button
            onClick={() => signOut()}
            className="text-sm text-slate-400 transition-colors hover:text-white"
          >
            Sign out
          </button>
        </header>

        <ClusterSelector selected={selectedCluster} onSelect={setSelectedCluster} />

        <div className="text-center">
          <button
            onClick={() => investigate()}
            disabled={isRunning || !selectedCluster}
            className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRunning ? "Investigating..." : "Investigate Cluster"}
          </button>
          {!selectedCluster && (
            <p className="mt-2 text-xs text-slate-500">Select a cluster above to investigate</p>
          )}
        </div>

        {error && (
          <div className="rounded-lg border border-red-900 bg-red-950/40 px-4 py-3 text-sm text-red-300 whitespace-pre-line">
            {error}
          </div>
        )}

        <InvestigationProgress
          steps={steps}
          isRunning={isRunning}
          clusterName={activeCluster || selectedCluster}
        />
        <DiagnosisCard diagnosis={diagnosis} clusterContext={activeCluster} />
        <InvestigationHistory />
      </div>
    </div>
  );
}
