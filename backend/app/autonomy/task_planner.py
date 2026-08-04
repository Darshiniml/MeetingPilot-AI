from __future__ import annotations

import logging
from typing import Any
from app.workflows.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)

class TaskPlanner:
    """Delegates goal action triggers directly to the core app WorkflowEngine."""
    
    def __init__(self) -> None:
        self.workflow_engine = WorkflowEngine()

    def plan_and_delegate(self, goal_name: str, payload: dict[str, Any]) -> bool:
        """Constructs and starts a workflow corresponding to an active goal task."""
        logger.info("[TaskPlanner] Planning workflow task for goal '%s'.", goal_name)
        
        # Map goal names to existing workflow event/insight categories
        if goal_name == "Track commitments":
            wf = self.workflow_engine.create_workflow_from_insight("commitment", payload)
            return wf is not None
            
        elif goal_name == "Monitor deadlines":
            wf = self.workflow_engine.create_workflow_from_event("meeting_scheduled", payload)
            return wf is not None
            
        logger.warning("[TaskPlanner] No workflow mapping configured for goal: %s", goal_name)
        return False
