from .base_agent import BaseAgent
class EmailAgent(BaseAgent):
    tools = ("gmail",)
    keywords = ("email", "send", "invitation", "reminder", "follow-up")
    def name(self): return "email"
    def description(self): return "Handles email drafts, invitations, reminders, and follow-ups."
