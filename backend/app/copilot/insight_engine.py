"""Coordinates live meeting segment detectors to extract decisions, deadlines, risks, questions, and commitments."""

import logging
from datetime import datetime, timezone
from typing import Any

from app.copilot.copilot_models import LiveMeetingState, CopilotInsight
from app.copilot.decision_detector import DecisionDetector
from app.copilot.risk_detector import RiskDetector
from app.copilot.deadline_detector import DeadlineDetector
from app.copilot.question_detector import QuestionDetector
from app.copilot.commitment_detector import CommitmentDetector
from app.memory.memory_manager import get_memory_manager

logger = logging.getLogger(__name__)


class InsightEngine:
    """Invokes and aggregates real-time detector outputs over conversation segments."""

    def __init__(self) -> None:
        self.decision_detector = DecisionDetector()
        self.risk_detector = RiskDetector()
        self.deadline_detector = DeadlineDetector()
        self.question_detector = QuestionDetector()
        self.commitment_detector = CommitmentDetector()

    def process_segment(self, state: LiveMeetingState, text: str, speaker: str | None = None) -> list[CopilotInsight]:
        """Detect and log insights from a newly arrived transcript segment, persisting to Database."""
        new_insights = []

        # Run individual detectors
        raw_decisions = self.decision_detector.detect(text, speaker)
        raw_risks = self.risk_detector.detect(text, speaker)
        raw_deadlines = self.deadline_detector.detect(text, speaker)
        raw_questions = self.question_detector.detect(text, speaker)
        raw_commitments = self.commitment_detector.detect(text, speaker)

        # 1. Decisions
        for d in raw_decisions:
            insight = self._create_insight(state, "decision", d)
            new_insights.append(insight)

        # 2. Risks
        for r in raw_risks:
            insight = self._create_insight(state, "risk", r)
            new_insights.append(insight)

        # 3. Deadlines
        for dl in raw_deadlines:
            insight = self._create_insight(state, "deadline", dl)
            new_insights.append(insight)
            # Add to state action item candidates list
            state.action_items.append({
                "task": dl["metadata"]["task"],
                "owner": dl["metadata"]["owner"],
                "deadline": dl["metadata"]["deadline"]
            })

        # 4. Questions
        for q in raw_questions:
            insight = self._create_insight(state, "question", q)
            new_insights.append(insight)
            state.open_questions.append(q["metadata"]["question_text"])

        # 5. Commitments
        for c in raw_commitments:
            insight = self._create_insight(state, "commitment", c)
            new_insights.append(insight)

        # Look for question resolutions in text
        resolved_list = self.question_detector.check_resolution(text, state.open_questions)
        for q_text in resolved_list:
            if q_text in state.open_questions:
                state.open_questions.remove(q_text)
                state.resolved_questions.append(q_text)
                resolution_insight = CopilotInsight(
                    meeting_id=state.meeting_id,
                    insight_type="question_resolved",
                    title="Question Resolved",
                    content=f"Resolved: '{q_text}'",
                    confidence=0.85,
                    timestamp=datetime.now(timezone.utc),
                    metadata={"resolved_question": q_text}
                )
                new_insights.append(resolution_insight)

        # Persist new insights to the long-term memory system
        for insight in new_insights:
            try:
                # Log metrics for debugging
                logger.info(
                    "Copilot Insight Generated: meeting_id=%d type=%s content='%s' confidence=%.2f source=%s",
                    insight.meeting_id,
                    insight.insight_type,
                    insight.content,
                    insight.confidence,
                    insight.speaker or "system"
                )
                
                mgr = get_memory_manager()
                mgr.add_custom_memory(
                    user_id=state.user_id,
                    meeting_id=state.meeting_id,
                    memory_type="CopilotInsight",
                    title=insight.title,
                    content=insight.content,
                    metadata={
                        "insight_type": insight.insight_type,
                        "confidence": insight.confidence,
                        "speaker": insight.speaker,
                        **insight.metadata
                    }
                )
            except Exception as e:
                logger.warning("Could not persist copilot insight to long-term memory: %s", e)

        return new_insights

    def _create_insight(self, state: LiveMeetingState, type_name: str, raw_data: dict[str, Any]) -> CopilotInsight:
        return CopilotInsight(
            meeting_id=state.meeting_id,
            insight_type=type_name,
            title=raw_data["title"],
            content=raw_data["content"],
            confidence=raw_data["confidence"],
            speaker=raw_data["speaker"],
            timestamp=raw_data["timestamp"],
            metadata=raw_data.get("metadata", {})
        )
