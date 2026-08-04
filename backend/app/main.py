"""FastAPI application composition for MeetingPilot AI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.meeting_routes import router as meeting_router
from app.api.meeting_history_routes import router as meeting_history_router
from app.api.chat_routes import router as chat_router
from app.api.system_routes import router as system_router
from app.api.auth_routes import router as auth_router
from app.api.scheduler_routes import router as scheduler_router
from app.api.google_calendar_routes import router as google_calendar_router
from app.api.gmail_routes import router as gmail_router
from app.api.contact_routes import router as contact_router
from app.config.settings import get_settings
from app.database.initialization import create_database_tables
from app.transcription.whisper_service import get_whisper_service
from app.websocket.transcript_socket import router as transcript_socket_router
from app.copilot.copilot_service import router as copilot_socket_router
from app.a2a.a2a_server import a2a_router
from app.api.provider_routes import router as provider_router


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    """Initialize local infrastructure before the API accepts requests."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True
    )
    create_database_tables()
    settings = get_settings()
    if settings.whisper_load_on_startup:
        get_whisper_service().warmup()
    yield
    get_whisper_service().shutdown()


def create_app() -> FastAPI:
    """Create and configure the MeetingPilot ASGI application."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Meeting-Id"],
    )

    application.include_router(system_router)
    application.include_router(auth_router)
    application.include_router(meeting_router)
    application.include_router(meeting_history_router)
    application.include_router(chat_router)
    application.include_router(scheduler_router)
    application.include_router(google_calendar_router)
    application.include_router(gmail_router)
    application.include_router(contact_router)
    application.include_router(transcript_socket_router)
    application.include_router(copilot_socket_router)
    application.include_router(a2a_router)
    application.include_router(provider_router)
    return application


app = create_app()
