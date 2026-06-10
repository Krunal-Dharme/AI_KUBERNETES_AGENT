import { sanitizeDiagnosis } from "@/lib/report-format";
import api from "@/services/api";
import type { InvestigateResponse } from "@/types/investigation";

function extractApiError(error: unknown): string {
  if (error && typeof error === "object" && "response" in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response;
    if (typeof response?.data?.detail === "string") {
      return response.data.detail;
    }
  }
  if (error instanceof Error) return error.message;
  return "Investigation failed. Please retry.";
}

export async function runInvestigation(
  sessionId: string,
  clusterContext: string,
): Promise<InvestigateResponse> {
  try {
    const { data } = await api.post<InvestigateResponse>(
      "/investigate",
      { session_id: sessionId, cluster_context: clusterContext },
      { timeout: 180000 },
    );
    return {
      ...data,
      diagnosis: sanitizeDiagnosis(data.diagnosis) ?? data.diagnosis,
    };
  } catch (error) {
    throw new Error(extractApiError(error));
  }
}
