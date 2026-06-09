import json
import re
from typing import Any

from loguru import logger

from ai.confidence import ConfidenceEngine
from ai.fix_recommendation import FixRecommendationEngine
from ai.llm_client import LLMClientError, OpenRouterClient
from ai.prompt_builder import build_messages


class RootCauseAnalyzer:
    """Analyze investigation evidence and produce a structured diagnosis."""

    def __init__(
        self,
        llm_client: OpenRouterClient | None = None,
        fix_engine: FixRecommendationEngine | None = None,
        confidence_engine: ConfidenceEngine | None = None,
    ) -> None:
        self.llm_client = llm_client or OpenRouterClient()
        self.fix_engine = fix_engine or FixRecommendationEngine()
        self.confidence_engine = confidence_engine or ConfidenceEngine()

    def analyze(self, investigation: dict[str, Any]) -> dict[str, Any]:
        logger.info("Starting AI root cause analysis")

        messages = build_messages(investigation)
        raw_response = self.llm_client.chat_completion(messages)
        parsed = self._parse_response(raw_response)

        fix_fields = self.fix_engine.build(parsed, investigation)
        confidence_fields = self.confidence_engine.evaluate(
            investigation,
            int(parsed.get("confidence", 50)),
            str(parsed.get("confidence_reasoning", "")),
        )

        diagnosis = {
            "root_cause": str(parsed.get("root_cause", "Unable to determine root cause")).strip(),
            "explanation": str(
                parsed.get("explanation", "Insufficient evidence to explain the failure.")
            ).strip(),
            "fix": fix_fields["fix"],
            "kubectl_command": fix_fields["kubectl_command"],
            "prevention_recommendation": fix_fields["prevention_recommendation"],
            "confidence": confidence_fields["confidence"],
            "confidence_reasoning": confidence_fields["confidence_reasoning"],
        }

        logger.info(
            "AI diagnosis complete (confidence: {}%)",
            diagnosis["confidence"],
        )
        return diagnosis

    def _parse_response(self, raw_response: str) -> dict[str, Any]:
        cleaned = raw_response.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse LLM JSON response: {}", exc)

        return {
            "root_cause": "LLM returned an unstructured response",
            "explanation": raw_response[:500],
            "fix": "Re-run investigation and verify OpenRouter model configuration.",
            "kubectl_command": "kubectl get pods -A",
            "prevention_recommendation": "Ensure OPENROUTER_MODEL supports JSON output.",
            "confidence": 30,
            "confidence_reasoning": "Low confidence due to unstructured LLM response.",
        }


class AIAgent:
    """Senior Kubernetes SRE agent that reasons over investigation evidence."""

    def __init__(self, analyzer: RootCauseAnalyzer | None = None) -> None:
        self.analyzer = analyzer or RootCauseAnalyzer()

    def diagnose(self, investigation: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.analyzer.analyze(investigation)
        except LLMClientError as exc:
            logger.error("AI diagnosis failed: {}", exc)
            return self._fallback_diagnosis(investigation, str(exc))

    def _fallback_diagnosis(
        self, investigation: dict[str, Any], error_message: str
    ) -> dict[str, Any]:
        pods = investigation.get("pods", {}).get("problematic_pods", [])
        pod_hint = ""
        if pods:
            p = pods[0]
            pod_hint = f" Pod '{p.get('name')}' in namespace '{p.get('namespace')}' shows {p.get('status')}."

        return {
            "root_cause": "AI reasoning unavailable",
            "explanation": (
                f"Kubernetes evidence was collected but AI analysis could not run: {error_message}."
                f"{pod_hint}"
            ),
            "fix": "Configure OPENROUTER_API_KEY and OPENROUTER_MODEL in backend/.env, then retry.",
            "kubectl_command": self.fix_engine_fallback(investigation),
            "prevention_recommendation": "Store API keys in environment variables, never in source code.",
            "confidence": 0,
            "confidence_reasoning": "No AI analysis performed.",
        }

    def fix_engine_fallback(self, investigation: dict[str, Any]) -> str:
        return FixRecommendationEngine().suggest_fallback_command(investigation)
