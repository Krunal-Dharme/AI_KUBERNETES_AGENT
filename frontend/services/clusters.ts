import api from "@/services/api";
import type { ClustersResponse } from "@/types/investigation";

export async function fetchClusters(): Promise<ClustersResponse> {
  const { data } = await api.get<ClustersResponse>("/clusters");
  return data;
}
