"""FastAPI application composition for MeetingPilot AI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.meeting_routes import router as meeting_router
from app.api.system_routes import router as system_router
from app.config.settings import get_settings


def create_app() -> FastAPI:
    """Create and configure the MeetingPilot ASGI application."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(system_router)
    application.include_router(meeting_router)
    return application


app = create_app()
