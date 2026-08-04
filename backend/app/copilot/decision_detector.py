"""Detects meeting decisions from live transcripts using regex patterns and LLM verification."""

import re
from datetime import datetime, timezone
from typing import Any
from app.ai.providers import get_llm_provider


class DecisionDetector:
    """Heuristic and semantic parser for real-time meeting decisions."""

    DECISION_PATTERNS = [
        re.compile(r"\bwe\s+decided\s+(?:to\s+)?(.*?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"\blet's\s+do\s+(.*?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bwe'll\s+proceed\s+with\s+(.*?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bfinal\s+decision\s+is\s+(?:to\s+)?(.*?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bapproved\s+(.*?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"\baccepted\s+(.*?)(?:\.|$)", re.IGNORECASE),
    ]

    def detect(self, text: str, speaker: str | None = None) -> list[dict[str, Any]]:
        """Identify matching decision segments inside the text."""
        decisions = []
        
        # Check rule-based triggers
        for pattern in self.DECISION_PATTERNS:
            match = pattern.search(text)
            if match:
                decision_text = match.group(1).strip()
                if not decision_text:
                    continue
                
                # Default heuristics
                confidence = 0.80
                refined_text = f"Decided: {decision_text}"
                
                # Optionally use LLM provider to refine decision clarity & score confidence
                try:
                    provider = get_llm_provider()
                    prompt = (
                        f"Refine the following raw meeting decision into a single clear sentence starting with a capital letter.\n"
                        f"Raw text: {text}\n"
                        f"Extracted: {decision_text}\n"
                        "Return ONLY the refined sentence. Do not add markdown or commentary."
                    )
                    res = provider.generate(prompt)
                    res_text = res.content.strip()
                    if res_text:
                        refined_text = res_text
                        confidence = 0.95
                except Exception:
                    pass

                decisions.append({
                    "title": "Decision Approved",
                    "content": refined_text,
                    "confidence": confidence,
                    "speaker": speaker,
                    "timestamp": datetime.now(timezone.utc),
                    "metadata": {"raw_match": match.group(0)}
                })
        
        return decisions
