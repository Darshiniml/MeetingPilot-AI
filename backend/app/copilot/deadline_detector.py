"""Detects task deadlines mentioned in live meeting transcripts."""

import re
import json
from datetime import datetime, timezone
from typing import Any
from app.ai.providers import get_llm_provider


class DeadlineDetector:
    """Heuristic and semantic parser identifying timeline milestones and task deadlines."""

    DEADLINE_KEYWORDS = [
        r"\b(tomorrow|tonight|today)\b",
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b(next\s+week|by\s+next|next\s+monday|next\s+friday)\b",
        r"\b(end\s+of\s+the\s+month|end\s+of\s+month)\b",
        r"\b(asap|soon|as\s+soon\s+as\s+possible)\b",
        r"\b(before\s+release|before\s+deployment)\b",
    ]

    def detect(self, text: str, speaker: str | None = None) -> list[dict[str, Any]]:
        """Scan the text for mentions of task deadlines."""
        deadlines = []
        has_deadline = False
        
        for pattern in self.DEADLINE_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                has_deadline = True
                break

        if has_deadline:
            # Standard fallbacks
            confidence = 0.70
            deadline_str = "Unspecified / ASAP"
            owner = speaker or "Unassigned"
            task = text.strip()

            # Attempt LLM extraction for higher precision
            try:
                provider = get_llm_provider()
                prompt = (
                    f"Analyze this sentence: '{text}'. Extract the task being discussed, who is responsible (owner), and the deadline date/phrase.\n"
                    "Return ONLY a valid JSON object of shape:\n"
                    '{"task": "clean short summary of task", "owner": "name or Unassigned", "deadline": "date or phrase"}'
                )
                res = provider.generate(prompt)
                data = json.loads(res.content.strip())
                task = data.get("task", task)
                owner = data.get("owner", owner)
                deadline_str = data.get("deadline", deadline_str)
                confidence = 0.90
            except Exception:
                # Try simple heuristic extract
                match = re.search(r"(?:by|before|on|due)\s+([A-Za-z0-9\s]+)", text, re.IGNORECASE)
                if match:
                    deadline_str = match.group(1).strip()

            deadlines.append({
                "title": "Deadline Detected",
                "content": f"Task: {task} | Deadline: {deadline_str} | Owner: {owner}",
                "confidence": confidence,
                "speaker": speaker,
                "timestamp": datetime.now(timezone.utc),
                "metadata": {
                    "task": task,
                    "owner": owner,
                    "deadline": deadline_str
                }
            })

        return deadlines
