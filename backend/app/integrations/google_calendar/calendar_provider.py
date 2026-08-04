"""Google Calendar provider implementation."""

import re
import httpx
from datetime import datetime, timedelta, time, timezone
from sqlalchemy.orm import Session

from app.scheduler.schemas import MeetingDetails, CalendarPreview
from app.integrations.google_calendar.token_store import TokenStore
from app.integrations.google_calendar.oauth import GoogleOAuthService

def parse_meeting_time(
    date_str: str,
    time_str: str,
    duration_str: str,
    timezone_str: str = "UTC",
    now: datetime | None = None
) -> tuple[datetime, datetime]:
    """Parse relative NLP date/time strings into timezone-aware datetimes."""
    if now is None:
        now = datetime.now(timezone.utc)

    # 1. Parse date
    date_str_clean = date_str.lower().strip()
    target_date = now.date()

    if "today" in date_str_clean:
        target_date = now.date()
    elif "tomorrow" in date_str_clean:
        target_date = now.date() + timedelta(days=1)
    elif "next" in date_str_clean:
        # e.g., "next tuesday"
        weekdays = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        found_day = None
        for day, idx in weekdays.items():
            if day in date_str_clean:
                found_day = idx
                break
        if found_day is not None:
            days_ahead = found_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = now.date() + timedelta(days=days_ahead)
    else:
        # Match YYYY-MM-DD
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str_clean)
        if match:
            try:
                target_date = datetime.strptime(match.group(0), "%Y-%m-%d").date()
            except ValueError:
                pass

    # 2. Parse time
    time_str_clean = time_str.lower().strip()
    target_time = time(12, 0) # Default to noon

    # Match H:MM AM/PM or H AM/PM
    match_ampm = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", time_str_clean)
    if match_ampm:
        hour = int(match_ampm.group(1))
        minute = int(match_ampm.group(2)) if match_ampm.group(2) else 0
        ampm = match_ampm.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        target_time = time(hour, minute)
    else:
        # Match HH:MM (24h)
        match_24h = re.search(r"(\d{1,2}):(\d{2})", time_str_clean)
        if match_24h:
            hour = int(match_24h.group(1))
            minute = int(match_24h.group(2))
            target_time = time(hour, minute)

    # 3. Parse duration
    duration_str_clean = duration_str.lower().strip()
    delta = timedelta(hours=1) # Default to 1h
    match_dur = re.search(r"(\d+)\s*(h|m)", duration_str_clean)
    if match_dur:
        amount = int(match_dur.group(1))
        unit = match_dur.group(2)
        if unit == "h":
            delta = timedelta(hours=amount)
        elif unit == "m":
            delta = timedelta(minutes=amount)

    start_dt = datetime.combine(target_date, target_time).replace(tzinfo=timezone.utc)
    end_dt = start_dt + delta
    return start_dt, end_dt

class GoogleCalendarProvider:
    """Production Google Calendar integration provider."""

    def __init__(self, session: Session, user_id: int) -> None:
        self._session = session
        self._user_id = user_id
        self._token_store = TokenStore(session)
        self._oauth = GoogleOAuthService()

    def _get_access_token(self) -> str:
        """Fetch the token and auto-refresh if close to expiry."""
        decrypted = self._token_store.get_decrypted_tokens(self._user_id)
        if not decrypted:
            raise RuntimeError("Google Account is not connected.")

        expires_at = decrypted["expires_at"]
        # Add timezone awareness if not present
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if now + timedelta(minutes=1) >= expires_at:
            # Token expired or expiring soon, refresh it
            refresh_token = decrypted["refresh_token"]
            if not refresh_token:
                raise RuntimeError("Refresh token missing. Re-authorization required.")
            
            refreshed = self._oauth.refresh_access_token(refresh_token)
            self._token_store.save_token(
                user_id=self._user_id,
                google_email=decrypted["google_email"],
                access_token=refreshed["access_token"],
                refresh_token=refresh_token,
                expires_at=refreshed["expires_at"]
            )
            return refreshed["access_token"]

        return decrypted["access_token"]

    def check_availability(self, details: MeetingDetails) -> CalendarPreview:
        """Check user availability and suggest 3 alternative slots if busy."""
        token = self._get_access_token()
        start_dt, end_dt = parse_meeting_time(details.date, details.time, details.duration, details.timezone)

        # We query freebusy for a 24-hour range to suggest alternatives easily in one call
        query_start = start_dt - timedelta(hours=4)
        query_end = start_dt + timedelta(hours=20)

        url = "https://www.googleapis.com/calendar/v3/freeBusy"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "timeMin": query_start.isoformat(),
            "timeMax": query_end.isoformat(),
            "items": [{"id": "primary"}]
        }

        with httpx.Client() as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Google FreeBusy check failed: {resp.text}")

            busy_data = resp.json().get("calendars", {}).get("primary", {}).get("busy", [])

        # Parse busy intervals
        busy_intervals = []
        for interval in busy_data:
            b_start = datetime.fromisoformat(interval["start"].replace("Z", "+00:00"))
            b_end = datetime.fromisoformat(interval["end"].replace("Z", "+00:00"))
            busy_intervals.append((b_start, b_end))

        # Check if requested slot overlaps with any busy interval
        conflicts = []
        is_available = True
        for b_start, b_end in busy_intervals:
            if max(start_dt, b_start) < min(end_dt, b_end):
                is_available = False
                conflicts.append(f"Busy from {b_start.strftime('%H:%M')} to {b_end.strftime('%H:%M')}")

        alternatives = []
        if not is_available:
            # Generate suggested alternative slots
            # Move in 30-min increments from start_dt
            candidate = start_dt
            duration = end_dt - start_dt
            
            while len(alternatives) < 3 and candidate < query_end:
                candidate += timedelta(minutes=30)
                candidate_end = candidate + duration
                
                # Check conflict for candidate
                conflict_found = False
                for b_start, b_end in busy_intervals:
                    if max(candidate, b_start) < min(candidate_end, b_end):
                        conflict_found = True
                        break
                
                # Ensure typical business hours (9 AM to 6 PM)
                if not conflict_found and 9 <= candidate.hour < 18:
                    alternatives.append(
                        f"{candidate.strftime('%Y-%m-%d')} at {candidate.strftime('%I:%M %p')}"
                    )

        return CalendarPreview(
            provider="google",
            available=is_available,
            conflicts=conflicts if not is_available else [],
            suggestions=alternatives
        )

    def create_event(self, details: MeetingDetails) -> dict:
        """Create a Google Calendar event and return details."""
        token = self._get_access_token()
        start_dt, end_dt = parse_meeting_time(details.date, details.time, details.duration, details.timezone)

        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        payload = {
            "summary": details.title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
            "attendees": [{"email": email} for email in details.attendees],
            "conferenceData": {
                "createRequest": {
                    "requestId": f"mp-{int(datetime.utcnow().timestamp())}",
                    "conferenceSolutionKey": {"type": "hangoutsMeeting"}
                }
            }
        }

        with httpx.Client() as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Google Calendar event creation failed: {resp.text}")

            event = resp.json()

        # Extract meet link
        meet_link = ""
        entry_points = event.get("conferenceData", {}).get("entryPoints", [])
        for ep in entry_points:
            if ep.get("entryPointType") == "video":
                meet_link = ep.get("uri", "")
                break

        return {
            "event_id": event["id"],
            "calendar_link": event.get("htmlLink", ""),
            "meeting_start": start_dt,
            "meeting_end": end_dt,
            "google_meet_link": meet_link
        }

    def update_event(self, event_id: str, details: MeetingDetails) -> dict:
        """Update an existing Google Calendar event."""
        token = self._get_access_token()
        start_dt, end_dt = parse_meeting_time(details.date, details.time, details.duration, details.timezone)

        url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        payload = {
            "summary": details.title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
            "attendees": [{"email": email} for email in details.attendees]
        }

        with httpx.Client() as client:
            resp = client.put(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Google Calendar event update failed: {resp.text}")
            event = resp.json()

        return {
            "event_id": event["id"],
            "calendar_link": event.get("htmlLink", ""),
            "meeting_start": start_dt,
            "meeting_end": end_dt
        }

    def delete_event(self, event_id: str) -> None:
        """Delete an existing Google Calendar event."""
        token = self._get_access_token()
        url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
        headers = {"Authorization": f"Bearer {token}"}

        with httpx.Client() as client:
            resp = client.delete(url, headers=headers)
            if resp.status_code not in (200, 204):
                raise RuntimeError(f"Google Calendar event deletion failed: {resp.text}")

    def list_events(self) -> list[dict]:
        """List upcoming Google Calendar events."""
        token = self._get_access_token()
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"maxResults": 10, "orderBy": "startTime", "singleEvents": "true"}

        with httpx.Client() as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Google Calendar events list failed: {resp.text}")
            
            items = resp.json().get("items", [])
            
        events = []
        for item in items:
            events.append({
                "event_id": item["id"],
                "summary": item.get("summary", ""),
                "start": item.get("start", {}).get("dateTime") or item.get("start", {}).get("date"),
                "end": item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
            })
        return events
