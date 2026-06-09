import { useQuery } from "@tanstack/react-query";

import api from "@/services/api";
import type { HealthResponse } from "@/types";

export function useHealthCheck() {
  return useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: async () => {
      const { data } = await api.get<HealthResponse>("/health");
      return data;
    },
    refetchInterval: 30000,
  });
}
