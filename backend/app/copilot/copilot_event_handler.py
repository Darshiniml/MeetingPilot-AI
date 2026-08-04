"""Decouples EventBus payloads and routes them to the active CopilotService."""

import logging
from app.agent.events.event_models import BaseAgentEvent
from app.agent.events.event_types import EventType

logger = logging.getLogger(__name__)


class CopilotEventHandler:
    """Subscriber callback handler routing EventBus notifications to the Copilot Service."""

    def __init__(self, copilot_service) -> None:
        self._copilot_service = copilot_service

    def on_event(self, event: BaseAgentEvent) -> None:
        """Route incoming EventBus events to specific copilot parsing streams."""
        event_type = event.event_type
        meeting_id = event.meeting_id
        payload = event.payload or {}
        user_id = event.user_id

        # Skip events that are not associated with a meeting
        if meeting_id is None:
            return

        try:
            if event_type == EventType.MEETING_STARTED:
                self._copilot_service.handle_meeting_started(meeting_id=meeting_id, user_id=user_id)
            elif event_type == EventType.MEETING_STOPPED:
                self._copilot_service.handle_meeting_stopped(meeting_id=meeting_id)
            elif event_type == EventType.TRANSCRIPT_SAVED:
                self._copilot_service.handle_transcript_saved(meeting_id=meeting_id, payload=payload)
            elif event_type == EventType.SPEAKER_CHANGED:
                self._copilot_service.handle_speaker_changed(meeting_id=meeting_id, payload=payload)
            elif event_type == EventType.VISION_UPDATED:
                self._copilot_service.handle_vision_updated(meeting_id=meeting_id, payload=payload)
        except Exception as e:
            logger.exception(
                "CopilotEventHandler failed to process event: type=%s meeting=%s: %s",
                event_type.value, meeting_id, e
            )
stream_handler = None
