"""System-level HTTP endpoints."""

from fastapi import APIRouter


router = APIRouter(tags=["system"])


@router.get("/")
def root() -> dict[str, str]:
    """Provide a simple service identity endpoint."""
    return {"message": "🚀 MeetingPilot AI Backend is Running!"}


@router.get("/health")
def health() -> dict[str, str]:
    """Report process health for local checks and deployment probes."""
    return {"status": "healthy"}
