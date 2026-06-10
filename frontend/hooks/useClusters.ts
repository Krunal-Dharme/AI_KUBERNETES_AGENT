"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchClusters } from "@/services/clusters";

export function useClusters() {
  return useQuery({
    queryKey: ["clusters"],
    queryFn: fetchClusters,
    staleTime: 0,
    refetchOnMount: "always",
  });
}
