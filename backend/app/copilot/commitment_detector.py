"""Detects task commitments and promises made by speakers during meetings."""

import re
from datetime import datetime, timezone
from typing import Any


class CommitmentDetector:
    """Heuristic parser identifying voluntary commitments and action obligations."""

    COMMITMENT_PATTERNS = [
        re.compile(r"\bi'll\s+(send|complete|deliver|review|update|take\s+care\s+of|handle|do|check)\b\s*(.*?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bi\s+will\s+(send|complete|deliver|review|update|take\s+care\s+of|handle|do|check)\b\s*(.*?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bwe'll\s+(send|complete|deliver|review|update|take\s+care\s+of|handle|do|check)\b\s*(.*?)(?:\.|$)", re.IGNORECASE),
        re.compile(r"\bwe\s+will\s+(send|complete|deliver|review|update|take\s+care\s+of|handle|do|check)\b\s*(.*?)(?:\.|$)", re.IGNORECASE),
    ]

    def detect(self, text: str, speaker: str | None = None) -> list[dict[str, Any]]:
        """Identify commitment phrases in the text."""
        commitments = []
        
        for pattern in self.COMMITMENT_PATTERNS:
            match = pattern.search(text)
            if match:
                action_verb = match.group(1).strip()
                action_detail = match.group(2).strip()
                
                content = f"{speaker or 'Someone'} committed to {action_verb} {action_detail or 'it'}."
                commitments.append({
                    "title": "Commitment Detected",
                    "content": content,
                    "confidence": 0.80,
                    "speaker": speaker,
                    "timestamp": datetime.now(timezone.utc),
                    "metadata": {
                        "action_verb": action_verb,
                        "action_detail": action_detail,
                        "raw_match": match.group(0)
                    }
                })
                break

        return commitments
