"""Generates real-time meeting coaching recommendations and alerts."""

from datetime import datetime, timezone
from typing import Any
from app.copilot.copilot_models import LiveMeetingState, CopilotInsight


class RecommendationEngine:
    """Coaches meeting participants on task assignments, participation shares, and timeline alerts."""

    def generate(self, state: LiveMeetingState, meeting_duration_minutes: float) -> list[CopilotInsight]:
        """Generate non-destructive suggestions based on active state indicators."""
        recommendations = []

        # 1. Silent participant alert
        for participant in state.participants:
            speaking_time = state.speaking_times.get(participant, 0.0)
            # If the meeting has been going on for > 3 minutes, and participant has spoken for < 2 seconds
            if meeting_duration_minutes >= 3.0 and speaking_time < 2.0:
                recommendations.append(CopilotInsight(
                    meeting_id=state.meeting_id,
                    insight_type="recommendation",
                    title="Silent Participant Alert",
                    content=f"⚠ {participant} has not spoken for a while. Consider inviting their input.",
                    confidence=0.85,
                    timestamp=datetime.now(timezone.utc),
                    metadata={"target_participant": participant}
                ))

        # 2. Action items with no owner
        unowned_actions = [item for item in state.action_items if item.get("owner", "").lower() in ("unassigned", "unowned", "")]
        if len(unowned_actions) >= 3:
            recommendations.append(CopilotInsight(
                meeting_id=state.meeting_id,
                insight_type="recommendation",
                title="Action Items Assignee Alert",
                content=f"⚠ {len(unowned_actions)} action items have no owner. Recommend assigning assignees.",
                confidence=0.80,
                timestamp=datetime.now(timezone.utc),
                metadata={"unowned_count": len(unowned_actions)}
            ))

        # 3. Topic discussion without decision (e.g. Budget)
        # Search transcript text for "budget", "pricing", "cost", "funding"
        has_budget_topic = False
        for chunk in state.transcript_chunks:
            text = chunk.get("text", "").lower()
            if any(w in text for w in ("budget", "pricing", "cost", "funding")):
                has_budget_topic = True
                break

        if has_budget_topic:
            # Check if any decision has "budget", "pricing", "cost" in it
            has_budget_decision = False
            for insight in state.insights:
                if insight.insight_type == "decision" and any(w in insight.content.lower() for w in ("budget", "pricing", "cost", "funding")):
                    has_budget_decision = True
                    break
            
            if not has_budget_decision:
                recommendations.append(CopilotInsight(
                    meeting_id=state.meeting_id,
                    insight_type="recommendation",
                    title="Decision Gap Alert",
                    content="⚠ Budget/pricing discussion has occurred without a logged decision. Confirm outcome.",
                    confidence=0.75,
                    timestamp=datetime.now(timezone.utc),
                    metadata={"topic": "budget"}
                ))

        # 4. Deadline without assignee
        for insight in state.insights:
            if insight.insight_type == "deadline":
                owner = insight.metadata.get("owner", "")
                if owner.lower() in ("unassigned", "unowned", ""):
                    recommendations.append(CopilotInsight(
                        meeting_id=state.meeting_id,
                        insight_type="recommendation",
                        title="Deadline Assignee Gap",
                        content=f"⚠ Deadline '{insight.metadata.get('deadline')}' mentioned without assignee for task '{insight.metadata.get('task')[:40]}'.",
                        confidence=0.80,
                        timestamp=datetime.now(timezone.utc),
                        metadata={"deadline": insight.metadata.get("deadline"), "task": insight.metadata.get("task")}
                    ))

        # 5. Over scheduled duration (e.g. if meeting exceeds 30 minutes, or some threshold)
        # Default threshold: 30 minutes
        if meeting_duration_minutes > 30.0:
            recommendations.append(CopilotInsight(
                meeting_id=state.meeting_id,
                insight_type="recommendation",
                title="Meeting Duration Alert",
                content=f"⚠ Meeting running over scheduled duration ({round(meeting_duration_minutes, 1)} minutes elapsed). Suggest wrap-up.",
                confidence=0.90,
                timestamp=datetime.now(timezone.utc),
                metadata={"elapsed_minutes": meeting_duration_minutes}
            ))

        return recommendations
