import json
import re
from typing import Any

from loguru import logger

from ai.llm_client import LLMClientError, OpenRouterClient
from ai.prompt_builder import build_messages
from services.finding_builder import build_findings_from_investigation
from services.report_builder import build_sre_report


class RootCauseAnalyzer:
    """Analyze investigation evidence and produce a structured SRE report."""

    def __init__(self, llm_client: OpenRouterClient | None = None) -> None:
        self.llm_client = llm_client or OpenRouterClient()

    def analyze(self, investigation: dict[str, Any]) -> dict[str, Any]:
        logger.info("Starting AI SRE report analysis")

        pre_detected = build_findings_from_investigation(investigation)
        messages = build_messages(investigation, pre_detected)
        raw_response = self.llm_client.chat_completion(messages)
        parsed = self._parse_response(raw_response)

        report = build_sre_report(
            investigation,
            llm_response=parsed,
            cluster_healthy=False,
        )

        logger.info(
            "SRE report complete: {} finding(s), score={}%",
            len(report.get("findings", [])),
            report.get("cluster_health_score"),
        )
        return report

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
            "executive_summary": "AI returned an unstructured response. Rule-based findings are shown below.",
            "findings": [],
            "prevention_recommendation": "Ensure OPENROUTER_MODEL supports JSON output.",
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
            return self._fallback_report(investigation, str(exc))

    def _fallback_report(self, investigation: dict[str, Any], error_message: str) -> dict[str, Any]:
        report = build_sre_report(investigation, llm_response=None, cluster_healthy=False)
        report["executive_summary"] = (
            f"Kubernetes evidence collected but AI enrichment unavailable: {error_message}"
        )
        report["confidence"] = min(report.get("confidence", 50), 40)
        report["confidence_reasoning"] = "Rule-based findings only; AI analysis did not run."
        return report
