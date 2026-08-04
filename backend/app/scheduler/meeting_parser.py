"""Meeting details extraction using AI."""

import json
from pydantic import ValidationError
from app.ai.providers import LLMProvider
from app.scheduler.schemas import MeetingDetails

class MeetingParserError(Exception):
    """Raised when the LLM fails to output valid MeetingDetails JSON."""

class MeetingParser:
    """Extracts structured meeting information from natural language."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    def parse(self, request: str) -> MeetingDetails:
        """Parse natural language into MeetingDetails with a 1-time retry on failure."""
        prompt = self._build_prompt(request)
        result = self._llm.generate(prompt)
        
        try:
            return self._extract_json(result.content)
        except (ValueError, ValidationError) as e:
            # Automatic 1-time retry
            corrective_prompt = self._build_corrective_prompt(request, result.content, str(e))
            retry_result = self._llm.generate(corrective_prompt)
            try:
                return self._extract_json(retry_result.content)
            except (ValueError, ValidationError) as retry_error:
                raise MeetingParserError(f"Failed to parse meeting details after retry: {retry_error}") from retry_error

    def _extract_json(self, content: str) -> MeetingDetails:
        """Attempt to extract and validate JSON from the LLM response."""
        text = content.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e
            
        return MeetingDetails.model_validate(data)

    def _build_prompt(self, request: str) -> str:
        return (
            "You are a Meeting Scheduler AI. Extract the meeting details from the following request.\n"
            "You MUST return ONLY a valid JSON object matching this schema exactly:\n"
            "{\n"
            '  "title": "meeting title",\n'
            '  "date": "date mentioned (e.g. next Tuesday or YYYY-MM-DD)",\n'
            '  "time": "time mentioned (e.g. 2 PM)",\n'
            '  "duration": "duration mentioned or 1h default",\n'
            '  "timezone": "timezone if mentioned, else UTC",\n'
            '  "attendees": ["list", "of", "attendees"]\n'
            "}\n"
            "Do not output any additional text, markdown formatting, or explanations.\n\n"
            f"Request: {request}"
        )

    def _build_corrective_prompt(self, request: str, previous_output: str, error: str) -> str:
        return (
            "You are a Meeting Scheduler AI. I previously asked you to extract meeting details into JSON.\n"
            "Your previous output was invalid.\n"
            f"Error: {error}\n"
            f"Previous Output:\n{previous_output}\n\n"
            "Please try again. Extract the details from the request and return ONLY a valid JSON object.\n"
            "{\n"
            '  "title": "meeting title",\n'
            '  "date": "date mentioned (e.g. next Tuesday or YYYY-MM-DD)",\n'
            '  "time": "time mentioned (e.g. 2 PM)",\n'
            '  "duration": "duration mentioned or 1h default",\n'
            '  "timezone": "timezone if mentioned, else UTC",\n'
            '  "attendees": ["list", "of", "attendees"]\n'
            "}\n"
            "Do NOT include markdown, backticks, or any other text.\n\n"
            f"Request: {request}"
        )
