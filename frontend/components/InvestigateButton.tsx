"use client";

export function InvestigateButton() {
  const handleClick = () => {
    // Placeholder: investigation flow will be implemented later
  };

  return (
    <button
      onClick={handleClick}
      className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-slate-950"
    >
      Investigate Cluster
    </button>
  );
}
