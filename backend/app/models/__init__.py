"""Domain and persistence models for MeetingPilot.

Importing each mapped class here ensures SQLAlchemy can resolve relationship
targets even when a caller imports only one individual model module.
"""

from app.models.action_item import ActionItem
from app.models.meeting import Meeting, MeetingState, MeetingStatus
from app.models.summary import Summary
from app.models.transcript import Transcript
from app.models.google_calendar_token import GoogleCalendarToken
from app.models.email_log import EmailLog
from app.contacts.contact_model import Contact

from app.models.provider_models import ProviderConfig, LocalCalendarEvent, LocalEmail, LocalNotification

__all__ = [
    "ActionItem",
    "Meeting",
    "MeetingState",
    "MeetingStatus",
    "Summary",
    "Transcript",
    "GoogleCalendarToken",
    "EmailLog",
    "Contact",
    "ProviderConfig",
    "LocalCalendarEvent",
    "LocalEmail",
    "LocalNotification",
]
