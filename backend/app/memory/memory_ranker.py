"""Composite ranking system combining similarity, recency, importance, and relevance scores."""

import math
from datetime import datetime, timezone
from typing import Any


class MemoryRanker:
    """Combines vector scores with temporal decay, utility, and context weights."""

    def __init__(
        self,
        sim_weight: float = 1.0,
        recency_weight: float = 0.5,
        importance_weight: float = 0.8,
        freq_weight: float = 0.3,
        relevance_weight: float = 0.4,
        decay_rate: float = 0.005,  # 0.5% decay per hour
    ) -> None:
        self.sim_weight = sim_weight
        self.recency_weight = recency_weight
        self.importance_weight = importance_weight
        self.freq_weight = freq_weight
        self.relevance_weight = relevance_weight
        self.decay_rate = decay_rate

    def rank(
        self,
        memories: list[dict[str, Any]],
        current_meeting_id: int | None = None,
        current_user_id: int | None = None,
        current_conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Compute composite scores and return ranked memory results."""
        now = datetime.now(timezone.utc)
        ranked_list = []

        for memory in memories:
            # 1. Similarity
            similarity = memory.get("score", 0.0)

            # 2. Recency (exponential decay based on hours old)
            created_at = memory.get("created_at")
            if not created_at:
                created_at = now
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            hours_old = max(0.0, (now - created_at).total_seconds() / 3600.0)
            recency = math.exp(-self.decay_rate * hours_old)

            # 3. Importance score
            importance = memory.get("importance_score", 0.0)

            # 4. Access frequency
            access_count = memory.get("access_count", 0)
            frequency = min(1.0, math.log1p(access_count) / 5.0)

            # 5. Relevance (matches user, meeting, conversation context)
            relevance = 0.0
            if current_meeting_id is not None and memory.get("meeting_id") == current_meeting_id:
                relevance += 0.5
            if current_conversation_id is not None and memory.get("conversation_id") == current_conversation_id:
                relevance += 0.3
            if current_user_id is not None and memory.get("user_id") == current_user_id:
                relevance += 0.2
            relevance = min(1.0, relevance)

            # Composite Score Calculation
            composite_score = (
                (self.sim_weight * similarity)
                + (self.recency_weight * recency)
                + (self.importance_weight * importance)
                + (self.freq_weight * frequency)
                + (self.relevance_weight * relevance)
            )

            ranked_memory = dict(memory)
            ranked_memory["composite_score"] = round(composite_score, 4)
            ranked_list.append(ranked_memory)

        # Sort descending by composite score
        ranked_list.sort(key=lambda x: x["composite_score"], reverse=True)
        return ranked_list
