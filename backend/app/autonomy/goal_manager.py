from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AutonomyGoal(BaseModel):
    name: str
    description: str
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, HIGHEST
    status: str = "PENDING"   # PENDING, ACTIVE, COMPLETED

class GoalManager:
    """Orchestrates dynamic agent goals based on reasoning context variables."""
    
    def __init__(self) -> None:
        self._goals: list[AutonomyGoal] = []
        self._initialize_default_goals()

    def get_goals(self, context: dict[str, Any]) -> list[AutonomyGoal]:
        """Evaluate context dynamically to update goals activation states and priorities."""
        insights = context.get("copilot_insights", [])
        
        # Reset and re-prioritize
        for goal in self._goals:
            goal.status = "PENDING"
            goal.priority = "MEDIUM"

            # Dynamic prioritization mapping logic
            if goal.name == "Monitor deadlines":
                # If there's an active deadline today, elevate priority to HIGH
                has_deadline = any(ins.get("insight_type") == "deadline" for ins in insights)
                if has_deadline:
                    goal.priority = "HIGH"
                    goal.status = "ACTIVE"
                    
            elif goal.name == "Track commitments":
                # If commitments are found, make it ACTIVE
                has_task = any(ins.get("insight_type") == "commitment" for ins in insights)
                if has_task:
                    goal.status = "ACTIVE"
                    
            elif goal.name == "Resolve unanswered questions":
                # Emergency risk checking
                has_risk = any(ins.get("insight_type") == "risk" for ins in insights)
                if has_risk:
                    goal.priority = "HIGHEST"
                    goal.status = "ACTIVE"
                    
            elif goal.name == "Maintain memory":
                # Memory cleanup is LOW priority
                goal.priority = "LOW"
                goal.status = "ACTIVE"

        return self._goals

    def _initialize_default_goals(self) -> None:
        self._goals = [
            AutonomyGoal(name="Improve meeting quality", description="Analyze speaker balance and suggest recommendations."),
            AutonomyGoal(name="Track commitments", description="Extract and structure meeting action items."),
            AutonomyGoal(name="Resolve unanswered questions", description="Identify critical unanswered questions or emergency risks."),
            AutonomyGoal(name="Monitor deadlines", description="Track deadlines and raise notifications."),
            AutonomyGoal(name="Assist scheduling", description="Verify availability and suggest calendar slots."),
            AutonomyGoal(name="Assist follow-ups", description="Draft email responses for meeting summaries."),
            AutonomyGoal(name="Maintain memory", description="Refresh vectorized embeddings index databases.")
        ]
