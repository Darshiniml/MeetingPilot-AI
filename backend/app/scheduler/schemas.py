"""Data schemas for the AI Meeting Scheduler."""

from pydantic import BaseModel, Field

class SchedulerPlanRequest(BaseModel):
    request: str = Field(..., description="Natural language request to schedule a meeting.")

class MeetingDetails(BaseModel):
    title: str = Field(description="The title of the meeting.")
    date: str = Field(description="The date of the meeting, e.g. '2023-11-05' or 'next Tuesday'.")
    time: str = Field(description="The time of the meeting, e.g. '14:00' or '2 PM'.")
    duration: str = Field(description="The duration of the meeting, e.g. '1h' or '30m'.")
    timezone: str = Field(default="UTC", description="The timezone of the meeting.")
    attendees: list[str] = Field(default_factory=list, description="List of attendees mentioned.")

class CalendarPreview(BaseModel):
    provider: str
    available: bool
    conflicts: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

class AttendeeCandidate(BaseModel):
    contact_id: int
    display_name: str
    email: str | None
    company: str | None
    confidence_score: float

class AttendeeResolution(BaseModel):
    input_name: str
    resolved_email: str | None = None
    status: str = "RESOLVED"  # "RESOLVED", "AMBIGUOUS", "NOT_FOUND"
    confidence_score: float = 0.0
    source: str | None = None  # "CONTACTS", "INPUT"
    candidates: list[AttendeeCandidate] = []

class SchedulerPlanResponse(BaseModel):
    title: str
    date: str
    time: str
    duration: str
    attendees: list[str]
    email_draft: str
    calendar_preview: CalendarPreview
    attendee_resolutions: list[AttendeeResolution] = []

class SendInvitesRequest(BaseModel):
    meeting_id: int
    attendees: list[str] = Field(..., description="List of emails to send invites to.")
