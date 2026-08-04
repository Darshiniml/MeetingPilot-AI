from .base_agent import BaseAgent
class MeetingAgent(BaseAgent):
    tools = ("summary", "transcript", "meeting_history", "action_items")
    keywords = ("summary", "transcript", "action", "history", "meeting", "insight")
    def name(self): return "meeting"
    def description(self): return "Handles summaries, transcripts, action items, and meeting history."
