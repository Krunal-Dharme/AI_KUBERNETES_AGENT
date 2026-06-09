"use client";

import { useHealthCheck } from "@/hooks/useHealthCheck";

export function SystemStatus() {
  const { data, isLoading, isError } = useHealthCheck();

  const statusText = isLoading
    ? "Checking..."
    : isError
      ? "Unavailable"
      : data?.status === "healthy"
        ? "Ready"
        : "Unknown";

  const statusColor = isLoading
    ? "text-slate-400"
    : isError
      ? "text-red-400"
      : "text-emerald-400";

  return (
    <p className="text-sm text-slate-400">
      System Status:{" "}
      <span className={`font-medium ${statusColor}`}>{statusText}</span>
    </p>
  );
}
