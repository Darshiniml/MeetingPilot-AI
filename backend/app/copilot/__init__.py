"""Live AI Copilot Package with EventBus dynamic integrations and hooks."""

import logging
from typing import Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def initialize_copilot_hooks() -> None:
    """Register package runtime monkeypatches to capture live activities on the EventBus."""
    logger.info("Initializing Live AI Copilot event capture hooks...")

    # 1. Hook EventBus.publish to feed events to LiveCopilotService
    try:
        from app.agent.events.event_bus import EventBus
        from app.copilot.copilot_event_handler import CopilotEventHandler
        from app.copilot.copilot_service import get_live_copilot_service
        
        handler = CopilotEventHandler(get_live_copilot_service())
        
        _original_bus_publish = EventBus.publish
        def wrapped_bus_publish(self, event: Any) -> None:
            _original_bus_publish(self, event)
            try:
                handler.on_event(event)
            except Exception as ex:
                logger.exception("Copilot EventHandler publish hook failed: %s", ex)
        EventBus.publish = wrapped_bus_publish
        logger.info(" -> EventBus.publish hooked for copilot successfully.")
    except Exception as e:
        logger.error("Could not hook EventBus.publish for copilot: %s", e)

    # 2. Hook TranscriptService.persist_whisper_result to dispatch TranscriptSavedEvent
    try:
        from app.services.transcript_service import TranscriptService
        from app.agent.events.event_models import TranscriptSavedEvent
        from app.agent.events.event_bus import EventBus
        
        _original_persist = TranscriptService.persist_whisper_result
        def wrapped_persist(self, *args, **kwargs) -> list[Any]:
            transcripts = _original_persist(self, *args, **kwargs)
            try:
                # Find meeting_id from arguments or keyword args
                meeting_id = kwargs.get("meeting_id")
                if meeting_id is None and len(args) > 0:
                    meeting_id = args[0]  # positional check
                
                # Default user_id fallback
                user_id = 1
                try:
                    from app.memory import current_user_id
                    user_id = current_user_id.get(1)
                except Exception:
                    pass

                bus = EventBus()
                for t in transcripts:
                    event = TranscriptSavedEvent(
                        user_id=user_id,
                        meeting_id=t.meeting_id if hasattr(t, "meeting_id") else meeting_id,
                        payload={
                            "text": t.text,
                            "speaker_name": t.speaker_name,
                            "speaker_id": t.speaker_id,
                            "chunk_index": t.chunk_index,
                            "segment_index": t.segment_index,
                            "start_seconds": t.start_seconds,
                            "end_seconds": t.end_seconds,
                            "confidence": t.confidence,
                        }
                    )
                    bus.publish(event)
            except Exception as ex:
                logger.exception("TranscriptService.persist_whisper_result hook dispatch failed: %s", ex)
            return transcripts
        TranscriptService.persist_whisper_result = wrapped_persist
        logger.info(" -> TranscriptService.persist_whisper_result hooked successfully.")
    except Exception as e:
        logger.error("Could not hook TranscriptService.persist_whisper_result: %s", e)

    # 3. Hook MeetingService.start_meeting and stop_meeting to dispatch lifecycle events
    try:
        from app.services.meeting_service import MeetingService
        from app.agent.events.event_models import MeetingStartedEvent, MeetingStoppedEvent
        from app.agent.events.event_bus import EventBus
        
        _original_start = MeetingService.start_meeting
        def wrapped_start(self, *args, **kwargs) -> Any:
            state = _original_start(self, *args, **kwargs)
            try:
                meeting_id = getattr(state, "meeting_id", None)
                if meeting_id:
                    bus = EventBus()
                    bus.publish(MeetingStartedEvent(
                        user_id=1,
                        meeting_id=meeting_id,
                        payload={"running": True}
                    ))
            except Exception as ex:
                logger.exception("MeetingService.start_meeting hook dispatch failed: %s", ex)
            return state
        MeetingService.start_meeting = wrapped_start
        
        _original_stop = MeetingService.stop_meeting
        def wrapped_stop(self, *args, **kwargs) -> Any:
            state = _original_stop(self, *args, **kwargs)
            try:
                meeting_id = getattr(state, "meeting_id", None)
                if meeting_id:
                    bus = EventBus()
                    bus.publish(MeetingStoppedEvent(
                        user_id=1,
                        meeting_id=meeting_id,
                        payload={"running": False}
                    ))
            except Exception as ex:
                logger.exception("MeetingService.stop_meeting hook dispatch failed: %s", ex)
            return state
        MeetingService.stop_meeting = wrapped_stop
        logger.info(" -> MeetingService lifecycle methods hooked successfully.")
    except Exception as e:
        logger.error("Could not hook MeetingService methods: %s", e)

    # 4. Hook VisionService.inspect_once to dispatch VisionUpdatedEvent and SpeakerChangedEvent
    try:
        from app.vision.vision_service import VisionService
        from app.agent.events.event_models import VisionUpdatedEvent, SpeakerChangedEvent
        from app.agent.events.event_bus import EventBus
        
        _original_inspect_once = VisionService.inspect_once
        _last_active_speaker = [None]
        
        def wrapped_inspect_once(self, *args, **kwargs) -> Any:
            result = _original_inspect_once(self, *args, **kwargs)
            try:
                # Extract participants list
                active = None
                participants_list = []
                for p in result.participants:
                    participants_list.append(p.display_name)
                    if p.is_active_speaker:
                        active = p.display_name
                
                # Resolve current meeting ID
                meeting_id = None
                try:
                    from app.memory import current_meeting_id
                    meeting_id = current_meeting_id.get(None)
                except Exception:
                    pass
                
                if meeting_id is None:
                    try:
                        from app.database.session import SessionLocal
                        with SessionLocal() as session:
                            from app.repositories.meeting_repository import MeetingRepository
                            repo = MeetingRepository(session)
                            running = repo.list_running_meetings(limit=1)
                            if running:
                                meeting_id = running[0].id
                    except Exception:
                        pass
                
                if meeting_id is not None:
                    bus = EventBus()
                    
                    # Publish VisionUpdatedEvent
                    bus.publish(VisionUpdatedEvent(
                        user_id=1,
                        meeting_id=meeting_id,
                        payload={"participants": participants_list}
                    ))
                    
                    # Publish SpeakerChangedEvent if needed
                    if active != _last_active_speaker[0]:
                        old_speaker = _last_active_speaker[0]
                        _last_active_speaker[0] = active
                        bus.publish(SpeakerChangedEvent(
                            user_id=1,
                            meeting_id=meeting_id,
                            payload={
                                "old_speaker": old_speaker,
                                "new_speaker": active
                            }
                        ))
            except Exception as ex:
                logger.exception("VisionService.inspect_once hook dispatch failed: %s", ex)
            return result
        VisionService.inspect_once = wrapped_inspect_once
        logger.info(" -> VisionService.inspect_once hooked successfully.")
    except Exception as e:
        logger.error("Could not hook VisionService.inspect_once: %s", e)

    # 5. Hook Planner.plan to inject live copilot insights
    try:
        from app.agent.planner import Planner
        from app.copilot.copilot_service import get_live_copilot_service
        from app.agent.models import ExecutionPlan
        
        _original_planner_plan = Planner.plan
        def wrapped_planner_plan(self, user_message: str, memory_context: dict | None = None) -> ExecutionPlan:
            if memory_context is None:
                memory_context = {}
                
            meeting_id = None
            try:
                from app.memory import current_meeting_id
                meeting_id = current_meeting_id.get(None)
            except Exception:
                pass
            
            if meeting_id is not None:
                try:
                    service = get_live_copilot_service()
                    state = service.get_meeting_state(meeting_id)
                    if state:
                        # Format live copilot insights for LLM prompt context injection
                        memory_context["live_copilot_insights"] = [
                            {
                                "type": i.insight_type,
                                "title": i.title,
                                "content": i.content,
                                "speaker": i.speaker
                            }
                            for i in state.insights
                        ]
                        logger.info("Injected %d live copilot insights into Planner context", len(state.insights))
                except Exception as ex:
                    logger.exception("Failed to inject live copilot insights into planner: %s", ex)
            return _original_planner_plan(self, user_message, memory_context)
        Planner.plan = wrapped_planner_plan
        logger.info(" -> Planner.plan hooked for copilot successfully.")
    except Exception as e:
        logger.error("Could not hook Planner.plan for copilot: %s", e)


# Run hooks immediately on package import
initialize_copilot_hooks()
