from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

class PolicyEngine:
    """Enforces safety guards and filters candidate decisions based on active execution mode policies."""
    
    def __init__(self, mode: str = "Semi-Autonomous") -> None:
        # Policy Tiers: Observation, Recommendation, Semi-Autonomous, Fully Autonomous
        self.mode = mode
        
        self.safe_actions = {
            "generate_reminder",
            "generate_summary",
            "refresh_embeddings",
            "create_workflow",
            "store_memory",
            "update_timeline"
        }
        self.unsafe_actions = {
            "calendar_creation",
            "email_sending",
            "contact_updates"
        }

    def evaluate_policy(self, action_name: str) -> str:
        """Determines the execution action status: BLOCKED, RECOMMEND, AUTO_EXECUTE, or QUEUE_APPROVAL."""
        mode_lower = self.mode.lower()
        
        if mode_lower == "observation":
            return "BLOCKED"
            
        elif mode_lower == "recommendation":
            return "RECOMMEND"
            
        elif mode_lower == "semi-autonomous":
            if action_name in self.safe_actions:
                return "AUTO_EXECUTE"
            else:
                return "QUEUE_APPROVAL"
                
        elif mode_lower == "fully autonomous":
            return "AUTO_EXECUTE"
            
        return "QUEUE_APPROVAL"

    def is_action_safe(self, action_name: str) -> bool:
        return action_name in self.safe_actions
