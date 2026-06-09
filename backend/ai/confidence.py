from typing import Any


class ConfidenceEngine:
    """Validate and adjust confidence scores based on evidence strength."""

    def evaluate(
        self,
        investigation: dict[str, Any],
        llm_confidence: int,
        confidence_reasoning: str,
    ) -> dict[str, Any]:
        evidence_score = self._score_evidence(investigation)
        adjusted = self._adjust_confidence(llm_confidence, evidence_score)
        reasoning = self._build_reasoning(
            investigation, confidence_reasoning, evidence_score, adjusted, llm_confidence
        )

        return {
            "confidence": adjusted,
            "confidence_reasoning": reasoning,
        }

    def _score_evidence(self, investigation: dict[str, Any]) -> int:
        score = 0

        pods = investigation.get("pods", {})
        logs = investigation.get("logs", {})
        events = investigation.get("events", {})
        deployments = investigation.get("deployments", {})
        network = investigation.get("network", {})

        if pods.get("problematic_pods"):
            score += 20
        if logs.get("entries"):
            score += 25
        if events.get("findings"):
            score += 20
        if deployments.get("unhealthy_deployments"):
            score += 15
        if network.get("issues"):
            score += 10

        correlated = 0
        if pods.get("problematic_pods") and logs.get("entries"):
            correlated += 15
        if pods.get("problematic_pods") and events.get("findings"):
            correlated += 10
        if deployments.get("unhealthy_deployments") and pods.get("problematic_pods"):
            correlated += 10

        return min(score + correlated, 100)

    def _adjust_confidence(self, llm_confidence: int, evidence_score: int) -> int:
        llm_confidence = max(0, min(llm_confidence, 100))

        if evidence_score >= 70:
            return max(llm_confidence, 75)
        if evidence_score >= 40:
            return min(llm_confidence, 90)
        if evidence_score < 20:
            return min(llm_confidence, 50)

        return llm_confidence

    def _build_reasoning(
        self,
        investigation: dict[str, Any],
        llm_reasoning: str,
        evidence_score: int,
        adjusted: int,
        original: int,
    ) -> str:
        signals = []

        pods = investigation.get("pods", {})
        logs = investigation.get("logs", {})
        events = investigation.get("events", {})

        if pods.get("problematic_pods"):
            statuses = {p.get("status") for p in pods["problematic_pods"]}
            signals.append(f"problematic pod states: {', '.join(sorted(statuses))}")

        if logs.get("entries"):
            signals.append("logs contain failure signals")

        if events.get("findings"):
            reasons = {f.get("reason") for f in events["findings"][:5]}
            signals.append(f"events include: {', '.join(sorted(reasons))}")

        evidence_note = (
            f"Evidence strength score: {evidence_score}/100."
            if signals
            else "Limited Kubernetes evidence available."
        )

        parts = [llm_reasoning.strip()] if llm_reasoning.strip() else []
        if signals:
            parts.append("Supporting signals: " + "; ".join(signals) + ".")
        parts.append(evidence_note)

        if adjusted != original:
            parts.append(
                f"Confidence adjusted from {original}% to {adjusted}% based on evidence correlation."
            )

        return " ".join(parts)
