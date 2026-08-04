"""Schemas for Google Calendar Integration."""

from datetime import datetime
from pydantic import BaseModel, Field

class GoogleAuthUrlResponse(BaseModel):
    url: str = Field(..., description="The Google OAuth 2.0 authorization URL.")

class GoogleStatusResponse(BaseModel):
    is_connected: bool = Field(..., description="True if the user has a linked Google Calendar.")
    google_email: str | None = Field(None, description="The connected Google account email.")

class GoogleEventDetails(BaseModel):
    event_id: str
    calendar_link: str
    meeting_start: datetime
    meeting_end: datetime
