"""Coordinates conversational engagement modeling and active recommendation rules."""

import logging
from datetime import datetime, timezone
from typing import Any

from app.copilot.copilot_models import LiveMeetingState, CopilotInsight
from app.copilot.engagement_analyzer import EngagementAnalyzer
from app.copilot.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


class LiveAnalyzer:
    """Manages active speaker ratios, interruption counters, and prompts recommendation triggers."""

    def __init__(self) -> None:
        self.engagement_analyzer = EngagementAnalyzer()
        self.recommendation_engine = RecommendationEngine()

    def analyze_meeting(self, state: LiveMeetingState, interruptions_count: int = 0) -> dict[str, Any]:
        """Process active speaking times and compute real-time coaching suggestions."""
        # Calculate meeting elapsed duration in minutes
        elapsed_seconds = (datetime.now(timezone.utc) - state.started_at).total_seconds()
        elapsed_minutes = max(0.05, elapsed_seconds / 60.0)

        # 1. Run Engagement analysis
        engagement_report = self.engagement_analyzer.analyze(
            speaking_times=state.speaking_times,
            participants=state.participants,
            interruptions_count=interruptions_count
        )

        # 2. Run Recommendation engine
        recommendations = self.recommendation_engine.generate(state, elapsed_minutes)

        # Append new recommendations to state if not already present (avoid duplicates)
        new_recs = []
        for rec in recommendations:
            if not any(item.content == rec.content for item in state.insights):
                state.insights.append(rec)
                new_recs.append(rec)
                
                # Persist recommendations to long-term memory
                try:
                    from app.memory.memory_manager import get_memory_manager
                    mgr = get_memory_manager()
                    mgr.add_custom_memory(
                        user_id=state.user_id,
                        meeting_id=state.meeting_id,
                        memory_type="CopilotInsight",
                        title=rec.title,
                        content=rec.content,
                        metadata={
                            "insight_type": "recommendation",
                            "confidence": rec.confidence,
                            **rec.metadata
                        }
                    )
                except Exception as e:
                    logger.warning("Could not persist recommendation alert to memory: %s", e)

        return {
            "engagement": engagement_report,
            "new_recommendations": new_recs,
            "elapsed_minutes": elapsed_minutes
        }
