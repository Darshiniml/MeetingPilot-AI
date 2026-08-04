from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from threading import RLock
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class MeetingPlatformProfile(BaseModel):
    """Metadata configurations outlining how to detect specific meeting applications."""
    platform_name: str
    process_names: list[str]
    window_patterns: list[str]
    url_patterns: list[str]
    weights: dict[str, float] = Field(default_factory=lambda: {
        "window": 0.3,
        "browser": 0.4,
        "process": 0.2,
        "microphone": 0.1
    })

class MeetingSession(BaseModel):
    """Execution telemetry log tracking a single active or historic meeting session."""
    meeting_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: str
    window_handle: int | None = None
    application: str
    title: str
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    status: str = "DETECTED"  # DETECTED, WAITING_CONFIRMATION, MONITORING, ENDED, LOST
    confidence: float
    signals_used: list[str] = Field(default_factory=list)

class MeetingPlatformRegistry:
    """Dynamic repository managing supported meeting software profiles."""
    
    def __init__(self) -> None:
        self._profiles: dict[str, MeetingPlatformProfile] = {}
        self._lock = RLock()
        self._register_default_profiles()

    def register_profile(self, profile: MeetingPlatformProfile) -> None:
        with self._lock:
            self._profiles[profile.platform_name.lower()] = profile
        logger.info("Registered meeting platform detection profile: %s", profile.platform_name)

    def get_profiles(self) -> list[MeetingPlatformProfile]:
        with self._lock:
            return list(self._profiles.values())

    def _register_default_profiles(self) -> None:
        # 1. Google Meet
        self.register_profile(MeetingPlatformProfile(
            platform_name="Google Meet",
            process_names=["chrome.exe", "msedge.exe", "firefox.exe", "browser.exe"],
            window_patterns=["meet - ", "google meet", "meet.google.com"],
            url_patterns=["meet.google.com"]
        ))
        # 2. Microsoft Teams
        self.register_profile(MeetingPlatformProfile(
            platform_name="Microsoft Teams",
            process_names=["teams.exe", "ms-teams.exe", "chrome.exe", "msedge.exe"],
            window_patterns=["teams", "microsoft teams", "teams.microsoft.com"],
            url_patterns=["teams.microsoft.com", "teams.live.com"]
        ))
        # 3. Zoom
        self.register_profile(MeetingPlatformProfile(
            platform_name="Zoom",
            process_names=["zoom.exe", "zoom.us", "chrome.exe"],
            window_patterns=["zoom meeting", "zoom", "zoom.us"],
            url_patterns=["zoom.us"]
        ))
        # 4. Discord
        self.register_profile(MeetingPlatformProfile(
            platform_name="Discord",
            process_names=["discord.exe", "chrome.exe"],
            window_patterns=["discord", "voice channel"],
            url_patterns=["discord.com"]
        ))
        # 5. Slack Huddles
        self.register_profile(MeetingPlatformProfile(
            platform_name="Slack Huddles",
            process_names=["slack.exe"],
            window_patterns=["slack", "huddle"],
            url_patterns=["slack.com"]
        ))
        # 6. Webex
        self.register_profile(MeetingPlatformProfile(
            platform_name="Webex",
            process_names=["webex.exe", "ciscowebexstart.exe", "chrome.exe"],
            window_patterns=["webex", "cisco webex"],
            url_patterns=["webex.com", "web.webex.com"]
        ))
        # 7. Skype
        self.register_profile(MeetingPlatformProfile(
            platform_name="Skype",
            process_names=["skype.exe"],
            window_patterns=["skype"],
            url_patterns=["skype.com"]
        ))

class MeetingRegistry:
    """Thread-safe storage caching detected and monitored meeting sessions."""
    
    def __init__(self) -> None:
        self._sessions: dict[str, MeetingSession] = {}
        self._lock = RLock()

    def add_session(self, session: MeetingSession) -> None:
        with self._lock:
            self._sessions[session.meeting_id] = session

    def get_session(self, meeting_id: str) -> MeetingSession | None:
        with self._lock:
            return self._sessions.get(meeting_id)

    def get_active_session(self) -> MeetingSession | None:
        """Finds any session that is currently DETECTED, WAITING_CONFIRMATION, or MONITORING."""
        with self._lock:
            for session in self._sessions.values():
                if session.status in ("DETECTED", "WAITING_CONFIRMATION", "MONITORING"):
                    return session
            return None

    def update_session_status(self, meeting_id: str, new_status: str) -> None:
        with self._lock:
            session = self._sessions.get(meeting_id)
            if session:
                session.status = new_status
                if new_status in ("ENDED", "LOST"):
                    session.end_time = datetime.now(timezone.utc)
                logger.info("Updated meeting session '%s' status to %s", meeting_id, new_status)

    def get_all_sessions(self) -> list[MeetingSession]:
        with self._lock:
            return list(self._sessions.values())
