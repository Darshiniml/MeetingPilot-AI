from .base_agent import BaseAgent
class SchedulerAgent(BaseAgent):
    tools = ("contacts", "scheduler", "calendar")
    keywords = ("schedule", "calendar", "availability", "conflict", "invite", "meeting with")
    def name(self): return "scheduler"
    def description(self): return "Handles scheduling, availability, calendar, and contact resolution."
