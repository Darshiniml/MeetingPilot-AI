"""Detects risks, blockers, and escalations in live meeting conversations."""

import re
from datetime import datetime, timezone
from typing import Any
from app.ai.providers import get_llm_provider


class RiskDetector:
    """Heuristic and semantic parser identifying project and technical risks."""

    RISK_KEYWORDS = [
        (r"\b(blocked|blockers?|stuck|waiting on)\b", "high", "Blocked Work"),
        (r"\b(unhappy|frustrated|dissatisfied|complaining|complaint)\b", "medium", "Customer Dissatisfaction"),
        (r"\b(not sure|unclear|uncertain|risks?|might fail)\b", "low", "Uncertainty / Risk"),
        (r"\b(depends on|dependent|waiting for)\b", "medium", "Dependency Issue"),
        (r"\b(understaffed|short on|lack of|resource shortages?)\b", "medium", "Resource Shortage"),
        (r"\b(escalat(e|ed|ing|ion)|urgent|critical|broken|system down)\b", "high", "Escalation"),
    ]

    def detect(self, text: str, speaker: str | None = None) -> list[dict[str, Any]]:
        """Identify matching risk segments inside the text."""
        risks = []
        
        for pattern, severity, category in self.RISK_KEYWORDS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                confidence = 0.75
                explanation = f"Detected {category.lower()} pattern: '{match.group(0)}' in conversation."
                
                # Refine using LLM if available
                try:
                    provider = get_llm_provider()
                    prompt = (
                        f"Summarize the technical or project risk mentioned in this sentence: '{text}'.\n"
                        "Return ONLY a short explanation. Do not add markdown or commentary."
                    )
                    res = provider.generate(prompt)
                    res_text = res.content.strip()
                    if res_text:
                        explanation = res_text
                        confidence = 0.90
                except Exception:
                    pass

                risks.append({
                    "title": f"Risk Detected ({category})",
                    "content": explanation,
                    "confidence": confidence,
                    "speaker": speaker,
                    "timestamp": datetime.now(timezone.utc),
                    "metadata": {
                        "severity": severity,
                        "category": category,
                        "raw_match": match.group(0)
                    }
                })
                # Break to avoid duplicate triggers on the same segment
                break

        return risks
