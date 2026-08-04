from .base_agent import BaseAgent
class ResearchAgent(BaseAgent):
    tools = ("rag_chat",)
    keywords = ("search", "research", "question", "find", "knowledge")
    def name(self): return "research"
    def description(self): return "Handles RAG, semantic search, and knowledge retrieval."
