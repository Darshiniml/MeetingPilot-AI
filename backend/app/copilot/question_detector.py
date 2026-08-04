"""Detects questions and monitors open and resolved questions in active meetings."""

import re
from datetime import datetime, timezone
from typing import Any


class QuestionDetector:
    """Heuristic and semantic parser identifying questions asked in conversation."""

    QUESTION_INDICATORS = [
        r"\?",
        r"\b(who|what|why|where|when|how|is|are|can|could|should|would)\b.*\?$",
        r"\b(can\s+someone|does\s+anyone|is\s+there\s+any)\b",
    ]

    def detect(self, text: str, speaker: str | None = None) -> list[dict[str, Any]]:
        """Scan transcript text to identify question patterns."""
        questions = []
        clean_text = text.strip()

        is_question = clean_text.endswith("?")
        if not is_question:
            # Check for starting indicator
            for pattern in self.QUESTION_INDICATORS:
                if re.search(pattern, clean_text, re.IGNORECASE):
                    is_question = True
                    break

        if is_question:
            questions.append({
                "title": "Question Detected",
                "content": clean_text,
                "confidence": 0.85,
                "speaker": speaker,
                "timestamp": datetime.now(timezone.utc),
                "metadata": {"question_text": clean_text}
            })

        return questions

    def check_resolution(self, text: str, open_questions: list[str]) -> list[str]:
        """Check if open questions have been answered or resolved by new conversation."""
        resolved = []
        lower_text = text.lower()
        
        # Simple heuristics for resolution confirmation
        resolution_triggers = [
            "that answers it",
            "resolved",
            "makes sense now",
            "got it",
            "i understand",
            "answered"
        ]

        if any(trigger in lower_text for trigger in resolution_triggers):
            # Resolve the most recent open question as a heuristic
            if open_questions:
                resolved.append(open_questions[-1])

        return resolved
