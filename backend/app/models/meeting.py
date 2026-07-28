"""Meeting domain model.

This model represents internal application state. It intentionally has no
FastAPI or request/response concerns so it can later be persisted with
SQLAlchemy or mapped into event streams without changing the API contract.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class MeetingState:
    """The current state of a single active meeting session."""

    running: bool = False
