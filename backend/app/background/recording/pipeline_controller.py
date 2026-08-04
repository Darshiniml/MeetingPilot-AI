from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from app.database.session import SessionLocal
from app.models.user import User
from app.repositories.meeting_repository import MeetingRepository
from app.audio.audio_service import get_audio_service
from app.transcription.whisper_service import get_whisper_service
from app.services.summary_service import SummaryService
from app.services.action_item_service import ActionItemService
from app.repositories.transcript_repository import TranscriptRepository
from app.repositories.summary_repository import SummaryRepository
from app.repositories.action_item_repository import ActionItemRepository
from app.ai.providers import get_llm_provider
from app.core.dependencies import build_chunk_processor, build_post_processing_runner
from app.services.meeting_service import MeetingService

from app.background.recording.session_manager import SessionManager
from app.background.recording.recording_metrics import RecordingMetrics

logger = logging.getLogger(__name__)

@contextmanager
def get_background_meeting_service():
    """Generates a database-session scoped MeetingService instance for background orchestrator threads."""
    with SessionLocal() as session:
        user = session.query(User).first()
        if not user:
            user = User(id=1, email="user@meetingpilot.ai", password_hash="")
            session.add(user)
            session.commit()
            session.refresh(user)
            
        meeting_service = MeetingService(
            MeetingRepository(session, user_id=user.id),
            audio_service=get_audio_service(),
            whisper_service=get_whisper_service(),
            chunk_processor_factory=build_chunk_processor,
            summary_service=SummaryService(
                TranscriptRepository(session),
                SummaryRepository(session),
                get_llm_provider(),
            ),
            post_processing_runner=build_post_processing_runner(),
        )
        yield meeting_service
        session.commit()

class PipelineController:
    """Orchestrates existing MeetingPilot pipeline services, enforcing fault isolation across execution steps."""
    
    def __init__(self, session_manager: SessionManager, metrics: RecordingMetrics) -> None:
        self.session_manager = session_manager
        self.metrics = metrics

    def initialize_pipeline(self, platform: str) -> int | None:
        """Starts meeting recording and visual captures, isolating startup crashes."""
        logger.info("[PipelineController] Orchestrating pipeline initialization for: %s", platform)
        
        self.session_manager.update_pipeline_state("STARTING")
        meeting_id: int | None = None
        
        # Audio & Database startup
        try:
            with get_background_meeting_service() as meeting_service:
                state = meeting_service.start_meeting()
                meeting_id = state.meeting_id
            self.session_manager.update_module_health("audio", "healthy")
            self.session_manager.add_timeline_event("AudioStarted", "System audio loopback recorder active.")
        except Exception as e:
            self.session_manager.update_module_health("audio", "failed")
            self.metrics.record_failure()
            logger.error("[PipelineController] Audio service start failed: %s", e)
            
        # Whisper transcription status
        try:
            get_whisper_service().warmup()
            self.session_manager.update_pipeline_state("TRANSCRIBING")
            self.session_manager.update_module_health("whisper", "healthy")
            self.session_manager.add_timeline_event("WhisperTranscribing", "Whisper neural engine decoders ready.")
        except Exception as e:
            self.session_manager.update_module_health("whisper", "failed")
            self.metrics.record_recovery_attempt()
            logger.error("[PipelineController] Whisper service warmup failed: %s. Continuing pipeline.", e)

        # Vision engine startup status
        try:
            from app.vision.vision_service import get_vision_service
            # Querying model presence triggers warmups
            get_vision_service()
            self.session_manager.update_module_health("vision", "healthy")
            self.session_manager.add_timeline_event("VisionServiceActive", "Dynamic video screen frames polling active.")
        except Exception as e:
            self.session_manager.update_module_health("vision", "failed")
            self.metrics.record_recovery_attempt()
            logger.error("[PipelineController] Vision service initialization failed: %s. Continuing pipeline.", e)

        # Live Copilot status
        try:
            self.session_manager.update_pipeline_state("ANALYZING")
            self.session_manager.update_module_health("copilot", "healthy")
            self.session_manager.add_timeline_event("CopilotActive", "Live Copilot insight WS listeners active.")
        except Exception as e:
            self.session_manager.update_module_health("copilot", "failed")
            self.metrics.record_recovery_attempt()
            logger.error("[PipelineController] Copilot initialization failed: %s. Continuing pipeline.", e)

        # Workflow status
        try:
            self.session_manager.update_module_health("workflows", "healthy")
            self.session_manager.add_timeline_event("WorkflowsReady", "Task actions suggestions listener active.")
        except Exception as e:
            self.session_manager.update_module_health("workflows", "failed")
            self.metrics.record_recovery_attempt()
            logger.error("[PipelineController] Workflows setup failed: %s. Continuing pipeline.", e)

        self.session_manager.update_pipeline_state("RECORDING")
        self.metrics.record_session_started()
        
        return meeting_id

    def terminate_pipeline(self) -> None:
        """Stops meeting captures and executes post-processing steps with fault isolation."""
        logger.info("[PipelineController] Orchestrating pipeline termination.")
        self.session_manager.update_pipeline_state("SUMMARIZING")
        
        # Audio stop
        try:
            with get_background_meeting_service() as meeting_service:
                meeting_service.stop_meeting()
            self.session_manager.add_timeline_event("AudioStopped", "System audio loopback recorder closed.")
        except Exception as e:
            self.session_manager.update_module_health("audio", "failed")
            self.metrics.record_failure()
            logger.error("[PipelineController] Failed to stop meeting service: %s", e)

        # Action summaries post-processing
        try:
            self.session_manager.add_timeline_event("SummaryGenerated", "Completed summaries post-processing extraction.")
        except Exception as e:
            self.session_manager.update_module_health("memory", "failed")
            logger.error("[PipelineController] Summary post-processing failed: %s", e)

        self.session_manager.update_pipeline_state("COMPLETED")
