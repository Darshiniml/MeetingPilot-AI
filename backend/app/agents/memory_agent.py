from .base_agent import AgentResult, BaseAgent
class MemoryAgent(BaseAgent):
    tools = ()
    keywords = ("remember", "memory", "previous", "preference", "history")
    def name(self): return "memory"
    def description(self): return "Maintains shared conversation, working, and reflection memory."
    def execute(self, request):
        memory = self.context.conversation_store.get_working_memory(request.conversation_id or f"user:{request.user_id}")
        return AgentResult(self.name(), str(memory.context()))
