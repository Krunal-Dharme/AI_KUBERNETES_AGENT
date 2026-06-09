"use client";

import { useEffect, useState } from "react";

import { useClusters } from "@/hooks/useClusters";

interface ClusterSelectorProps {
  selected: string;
  onSelect: (context: string) => void;
}

export function ClusterSelector({ selected, onSelect }: ClusterSelectorProps) {
  const { data, isLoading, error } = useClusters();
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (!data || initialized) return;

    const defaultContext =
      data.clusters.find((c) => c.is_current)?.name || data.clusters[0]?.name || "";

    if (defaultContext && !selected) {
      onSelect(defaultContext);
    }
    setInitialized(true);
  }, [data, initialized, onSelect, selected]);

  if (isLoading) {
    return (
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <p className="text-sm text-slate-400">Discovering clusters from kubeconfig...</p>
      </section>
    );
  }

  if (error || !data?.healthy) {
    return (
      <section className="rounded-xl border border-red-900 bg-red-950/30 p-5">
        <h2 className="text-sm font-semibold text-red-300">Cluster Discovery Failed</h2>
        <p className="mt-2 whitespace-pre-line text-sm text-red-200">
          {data?.error || "Unable to load clusters. Check KUBECONFIG_PATH on the backend."}
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
        Available Clusters
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        From: {data.kubeconfig_path}
      </p>

      <ul className="mt-4 space-y-2">
        {data.clusters.map((cluster) => (
          <li key={cluster.name}>
            <button
              type="button"
              onClick={() => onSelect(cluster.name)}
              className={`w-full rounded-lg border px-4 py-3 text-left transition-colors ${
                selected === cluster.name
                  ? "border-blue-500 bg-blue-950/40"
                  : "border-slate-700 bg-slate-950 hover:border-slate-600"
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`h-2 w-2 rounded-full ${
                    selected === cluster.name ? "bg-blue-400" : "bg-slate-600"
                  }`}
                />
                <span className="text-sm font-medium text-white">{cluster.name}</span>
                {cluster.is_gke && (
                  <span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-400">
                    GKE
                  </span>
                )}
                {cluster.is_current && (
                  <span className="text-xs text-slate-500">(current)</span>
                )}
              </div>
              <p className="mt-1 truncate pl-4 text-xs text-slate-500">{cluster.server}</p>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
