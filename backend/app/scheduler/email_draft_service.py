"""Email drafting service."""

from app.ai.providers import LLMProvider
from app.scheduler.schemas import MeetingDetails

class EmailDraftService:
    """Drafts meeting invitations using AI."""
    
    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    def generate_draft(self, details: MeetingDetails) -> str:
        prompt = (
            "You are an assistant. Draft a professional meeting invitation email for the following meeting:\n\n"
            f"Title: {details.title}\n"
            f"Date: {details.date}\n"
            f"Time: {details.time}\n"
            f"Duration: {details.duration}\n"
            f"Timezone: {details.timezone}\n"
            f"Attendees: {', '.join(details.attendees)}\n\n"
            "Include a placeholder for the meeting link, e.g., [Insert Meeting Link Here].\n"
            "Output only the email content, without any extra commentary or markdown blocks."
        )
        result = self._llm.generate(prompt)
        return result.content.strip()
