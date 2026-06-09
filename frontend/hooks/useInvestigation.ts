"use client";

import { useCallback, useRef, useState } from "react";

import { useAuth } from "@/lib/auth";
import { insforge } from "@/lib/insforge";
import { runInvestigation } from "@/services/investigate";
import {
  INVESTIGATION_STEPS,
  type Diagnosis,
  type InvestigateResponse,
  type ProgressStep,
} from "@/types/investigation";

function createSessionId() {
  return `inv-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function extractNamespace(response: InvestigateResponse): string {
  const pods = response.investigation.pods?.problematic_pods as
    | Array<{ namespace?: string }>
    | undefined;
  if (pods?.[0]?.namespace) return pods[0].namespace;
  return "default";
}

export function useInvestigation(
  clusterContext: string,
  onComplete?: () => void,
) {
  const { user } = useAuth();
  const [steps, setSteps] = useState<ProgressStep[]>(INVESTIGATION_STEPS);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [activeCluster, setActiveCluster] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  const updateStep = useCallback((stepId: string, status: ProgressStep["status"]) => {
    setSteps((current) =>
      current.map((step) => (step.id === stepId ? { ...step, status } : step)),
    );
  }, []);

  const resetSteps = useCallback(() => {
    setSteps(INVESTIGATION_STEPS.map((step) => ({ ...step, status: "pending" })));
  }, []);

  const saveHistory = useCallback(
    async (response: InvestigateResponse, sessionId: string) => {
      if (!user) return;

      await insforge.database.from("investigations").insert({
        user_id: user.id,
        session_id: sessionId,
        root_cause: response.diagnosis.root_cause,
        namespace: extractNamespace(response),
        confidence: response.diagnosis.confidence,
        status: response.diagnosis.cluster_healthy ? "healthy" : "completed",
        diagnosis: {
          ...response.diagnosis,
          cluster_context: response.cluster_context,
        },
      });
    },
    [user],
  );

  const subscribeToProgress = useCallback(
    async (sessionId: string) => {
      const channel = `investigation:${sessionId}`;

      const handleProgress = (payload: { step?: string; status?: string }) => {
        if (!payload.step) return;
        const status =
          payload.status === "in_progress" ? "in_progress" : "completed";
        updateStep(payload.step, status);
      };

      insforge.realtime.on("progress", handleProgress);

      try {
        await insforge.realtime.connect();
        const response = await insforge.realtime.subscribe(channel);
        if (!response.ok) {
          console.warn("Realtime subscribe failed:", response.error?.message);
        }
      } catch (err) {
        console.warn("Realtime connection failed:", err);
      }

      unsubscribeRef.current = () => {
        insforge.realtime.off("progress", handleProgress);
        insforge.realtime.unsubscribe(channel);
      };
    },
    [updateStep],
  );

  const investigate = useCallback(async () => {
    if (!user || isRunning || !clusterContext) return;

    const sessionId = createSessionId();
    setIsRunning(true);
    setError(null);
    setDiagnosis(null);
    setActiveCluster(clusterContext);
    resetSteps();

    try {
      await subscribeToProgress(sessionId);
      updateStep("context", "in_progress");

      const response = await runInvestigation(sessionId, clusterContext);

      setSteps((current) =>
        current.map((step) => ({ ...step, status: "completed" as const })),
      );
      setDiagnosis(response.diagnosis);
      setActiveCluster(response.cluster_context || clusterContext);
      await saveHistory(response, sessionId);
      onComplete?.();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Investigation failed. Please retry.";
      setError(message);
    } finally {
      unsubscribeRef.current?.();
      unsubscribeRef.current = null;
      setIsRunning(false);
    }
  }, [
    user,
    isRunning,
    clusterContext,
    resetSteps,
    subscribeToProgress,
    updateStep,
    saveHistory,
    onComplete,
  ]);

  return {
    steps,
    diagnosis,
    activeCluster,
    error,
    isRunning,
    investigate,
  };
}
