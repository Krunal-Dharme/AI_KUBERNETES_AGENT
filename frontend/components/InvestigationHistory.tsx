"use client";

import { useInvestigationHistory } from "@/hooks/useInvestigationHistory";

export function InvestigationHistory() {
  const { data, isLoading, error } = useInvestigationHistory();

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
        Recent Investigations
      </h2>

      {isLoading && <p className="text-sm text-slate-500">Loading history...</p>}
      {error && (
        <p className="text-sm text-red-400">Could not load investigation history.</p>
      )}

      {!isLoading && !error && (!data || data.length === 0) && (
        <p className="text-sm text-slate-500">No investigations yet.</p>
      )}

      {data && data.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-slate-500">
                <th className="pb-2 pr-4 font-medium">Root Cause</th>
                <th className="pb-2 pr-4 font-medium">Namespace</th>
                <th className="pb-2 pr-4 font-medium">Confidence</th>
                <th className="pb-2 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr key={item.id} className="border-b border-slate-800/60">
                  <td className="py-3 pr-4 text-slate-200">{item.root_cause}</td>
                  <td className="py-3 pr-4 text-slate-400">{item.namespace}</td>
                  <td className="py-3 pr-4 text-blue-400">{item.confidence}%</td>
                  <td className="py-3 text-slate-500">
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
