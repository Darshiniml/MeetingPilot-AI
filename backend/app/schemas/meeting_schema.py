"""HTTP response schemas for meeting endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class MeetingStatusResponse(BaseModel):
    """Public representation of whether a meeting is currently active."""

    model_config = ConfigDict(frozen=True)

    running: bool = Field(
        ..., description="Whether the local MeetingPilot session is running."
    )


class MeetingActionResponse(MeetingStatusResponse):
    """Response returned after starting or stopping a meeting."""

    message: str = Field(..., description="Human-readable result of the requested action.")
