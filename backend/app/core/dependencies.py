"""Application dependency composition for HTTP request handling."""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.session import SessionLocal
from app.models.user import User
from app.core.security import decode_token
from app.audio.audio_service import AudioService, get_audio_service
from app.audio.buffer import AudioChunk
from app.repositories.meeting_repository import MeetingRepository
from app.repositories.meeting_history_repository import MeetingHistoryRepository
from app.repositories.action_item_repository import ActionItemRepository
from app.repositories.summary_repository import SummaryRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.repositories.vector_repository import VectorRepository
from app.services.meeting_service import MeetingService
from app.services.meeting_history_service import MeetingHistoryService
from app.services.transcript_service import TranscriptService
from app.services.summary_service import SummaryService
from app.services.action_item_service import ActionItemService
from app.services.chat_service import ChatService
from app.services.embedding_service import get_embedding_service
from app.ai.providers import get_llm_provider
from app.transcription.pipeline import TranscriptPersistencePipeline
from app.transcription.whisper_service import WhisperService, get_whisper_service
from app.scheduler.meeting_parser import MeetingParser
from app.scheduler.email_draft_service import EmailDraftService
from app.scheduler.calendar_service import MockCalendarProvider
from app.scheduler.scheduler_service import SchedulerService
from app.integrations.gmail.gmail_provider import GmailProvider
from app.contacts.contact_service import ContactService


DatabaseSession = Annotated[Session, Depends(get_db)]

security = HTTPBearer()

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: DatabaseSession
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    
    user = session.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]


def build_chunk_processor(
    *, meeting_id: int, meeting_started_at: datetime, whisper_service: WhisperService
) -> Callable[[AudioChunk], None]:
    """Build a worker-safe processor with a fresh database session per chunk."""
    def process(audio_chunk: AudioChunk) -> None:
        with SessionLocal() as session:
            pipeline = TranscriptPersistencePipeline(
                meeting_id=meeting_id,
                meeting_started_at=meeting_started_at,
                whisper_service=whisper_service,
                transcript_service=TranscriptService(TranscriptRepository(session)),
            )
            pipeline.handle_audio_chunk(audio_chunk)

    return process


def build_post_processing_runner() -> Callable[[int], None]:
    """Create post-processing work that owns its own background DB session."""
    def process(meeting_id: int) -> None:
        with SessionLocal() as session:
            transcript_repository = TranscriptRepository(session)
            SummaryService(
                transcript_repository,
                SummaryRepository(session),
                get_llm_provider(),
            ).generate_for_meeting(meeting_id)
            ActionItemService(
                transcript_repository,
                ActionItemRepository(session),
                get_llm_provider(),
            ).extract_for_meeting(meeting_id)

    return process


def get_meeting_service(session: DatabaseSession, user: CurrentUser) -> MeetingService:
    """Build a request-scoped MeetingService with its repository dependency."""
    return MeetingService(
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


def get_meeting_history_service(session: DatabaseSession, user: CurrentUser) -> MeetingHistoryService:
    """Build the read-only meeting history service for one request."""
    return MeetingHistoryService(MeetingHistoryRepository(session, user_id=user.id))


def get_chat_service(session: DatabaseSession, user: CurrentUser) -> ChatService:
    """Build local retrieval chat dependencies for one request."""
    return ChatService(
        TranscriptRepository(session, user_id=user.id),
        VectorRepository(session),
        get_embedding_service(),
        get_llm_provider(),
    )

def get_gmail_provider(session: DatabaseSession, user: CurrentUser) -> GmailProvider:
    """Build the Gmail provider instance."""
    return GmailProvider(session, user_id=user.id)

def get_scheduler_service(session: DatabaseSession, user: CurrentUser) -> SchedulerService:
    """Build the AI Meeting Scheduler service."""
    llm = get_llm_provider()
    
    from app.integrations.google_calendar.token_store import TokenStore
    from app.integrations.google_calendar.calendar_provider import GoogleCalendarProvider
    
    token_store = TokenStore(session)
    token_record = token_store.get_token(user.id)
    
    if token_record and token_record.is_connected:
        calendar_provider = GoogleCalendarProvider(session, user_id=user.id)
    else:
        calendar_provider = MockCalendarProvider()
        
    email_provider = get_gmail_provider(session, user)
        
    return SchedulerService(
        session=session,
        parser=MeetingParser(llm),
        email_service=EmailDraftService(llm),
        calendar_provider=calendar_provider,
        email_provider=email_provider
    )

def get_contact_service(session: DatabaseSession, user: CurrentUser) -> ContactService:
    """Build the ContactService dependency."""
    return ContactService(session, user_id=user.id)
