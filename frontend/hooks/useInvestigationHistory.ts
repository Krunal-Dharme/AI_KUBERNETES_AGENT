"use client";

import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/lib/auth";
import { insforge } from "@/lib/insforge";
import type { InvestigationHistoryItem } from "@/types/investigation";

export function useInvestigationHistory() {
  const { user } = useAuth();

  return useQuery<InvestigationHistoryItem[]>({
    queryKey: ["investigation-history", user?.id],
    enabled: !!user,
    queryFn: async () => {
      const { data, error } = await insforge.database
        .from("investigations")
        .select("id, user_id, session_id, root_cause, namespace, confidence, status, created_at")
        .order("created_at", { ascending: false })
        .limit(10);

      if (error) throw new Error(error.message || "Failed to load history");
      return (data || []) as InvestigationHistoryItem[];
    },
  });
}
