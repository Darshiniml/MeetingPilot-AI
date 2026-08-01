"""Typed values used by the local vision foundation."""

from dataclasses import dataclass
from datetime import datetime

import numpy as np


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """A rectangle in desktop pixel coordinates."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class CaptureFrame:
    """One full-desktop BGR frame and its capture timestamp."""

    image: np.ndarray
    timestamp: datetime
    origin_x: int
    origin_y: int


@dataclass(frozen=True, slots=True)
class MeetingWindow:
    """Detected meeting application bounds and platform label."""

    bounding_box: BoundingBox
    platform_name: str


@dataclass(frozen=True, slots=True)
class Participant:
    """A contour-detected meeting tile; names remain intentionally unknown."""

    id: str
    display_name: str
    bounding_box: BoundingBox
    is_active_speaker: bool
    last_seen: datetime
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class VisionResult:
    """The result of one capture, window crop, and participant-tile pass."""

    frame: CaptureFrame
    meeting_window: MeetingWindow | None
    participants: tuple[Participant, ...]
