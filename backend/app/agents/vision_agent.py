from .base_agent import BaseAgent
class VisionAgent(BaseAgent):
    tools = ("vision",)
    keywords = ("vision", "ocr", "speaker", "participant", "camera")
    def name(self): return "vision"
    def description(self): return "Handles participant, speaker, and visual meeting observations."
