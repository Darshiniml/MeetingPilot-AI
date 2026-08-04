from __future__ import annotations

import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.provider_models import LocalCalendarEvent
from app.scheduler.schemas import MeetingDetails, CalendarPreview

logger = logging.getLogger(__name__)

class LocalCalendarProvider:
    """SQLAlchemy backed local offline calendar provider."""
    
    def __init__(self, db_session: Session | None = None) -> None:
        self._db = db_session
        self.version = "1.0.0"
        self.last_sync = datetime.now(timezone.utc).isoformat()
        self.error_info = None

    def _get_db(self) -> Session:
        if self._db is not None:
            return self._db
        return SessionLocal()

    def _close_db(self, session: Session) -> None:
        if self._db is None:
            session.close()

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "latency_ms": 5,
            "version": self.version,
            "capabilities": ["CRUD", "timezone_scheduling", "recurrence", "conflict_detection", "reminders", "ics_sync"],
            "last_sync": self.last_sync,
            "error_info": self.error_info
        }

    def _parse_event_times(self, date_str: str, time_str: str, duration_str: str) -> tuple[datetime, datetime]:
        try:
            dt_base = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            dt_base = datetime.now()

        try:
            hr, mn = map(int, time_str.split(":"))
        except Exception:
            hr, mn = 12, 0

        start_time = datetime(dt_base.year, dt_base.month, dt_base.day, hr, mn, tzinfo=timezone.utc)
        
        duration_minutes = 60
        try:
            if duration_str.endswith("h"):
                duration_minutes = int(float(duration_str[:-1]) * 60)
            elif duration_str.endswith("m"):
                duration_minutes = int(duration_str[:-1])
            else:
                duration_minutes = int(duration_str)
        except Exception:
            pass

        end_time = start_time + timedelta(minutes=duration_minutes)
        return start_time, end_time

    def check_availability(self, details: MeetingDetails) -> CalendarPreview:
        """Validate if the meeting slot conflicts with other local calendar entries."""
        start_time, end_time = self._parse_event_times(details.date, details.time, details.duration)
        conflicts = []
        
        session = self._get_db()
        try:
            events = session.query(LocalCalendarEvent).all()
            for ev in events:
                ev_start = datetime.fromisoformat(ev.start_time)
                ev_end = datetime.fromisoformat(ev.end_time)
                
                # Simple overlap check
                if (start_time < ev_end) and (end_time > ev_start):
                    conflicts.append(f"Conflict with '{ev.title}' ({ev_start.strftime('%H:%M')} - {ev_end.strftime('%H:%M')})")
        finally:
            self._close_db(session)

        return CalendarPreview(
            provider="local",
            available=len(conflicts) == 0,
            conflicts=conflicts,
            suggestions=[]
        )

    def create_event(self, details: MeetingDetails) -> dict[str, Any]:
        """Save a new local calendar event into the SQLite table."""
        start_time, end_time = self._parse_event_times(details.date, details.time, details.duration)
        event_id = f"evt-{uuid.uuid4()}"
        
        # Pull potential recurrence parameters (default to none if not in schema fields)
        is_recurring = getattr(details, "is_recurring", False)
        recurrence_rule = getattr(details, "recurrence_rule", None)
        reminder_minutes = getattr(details, "reminder_minutes", 15)

        event_row = LocalCalendarEvent(
            event_id=event_id,
            title=details.title,
            date=details.date,
            time=details.time,
            duration=details.duration,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            attendees_json=json.dumps(details.attendees),
            is_recurring=is_recurring,
            recurrence_rule=recurrence_rule,
            reminder_minutes_before=reminder_minutes
        )

        session = self._get_db()
        try:
            session.add(event_row)
            session.commit()
            logger.info("Local event created: %s (%s)", details.title, event_id)
            return self._row_to_dict(event_row)
        finally:
            self._close_db(session)

    def update_event(self, event_id: str, details: MeetingDetails) -> dict[str, Any]:
        """Update existing local calendar database event."""
        session = self._get_db()
        try:
            event_row = session.query(LocalCalendarEvent).filter_by(event_id=event_id).first()
            if not event_row:
                raise KeyError(f"Event ID {event_id} not found in database.")
                
            start_time, end_time = self._parse_event_times(details.date, details.time, details.duration)
            
            event_row.title = details.title
            event_row.date = details.date
            event_row.time = details.time
            event_row.duration = details.duration
            event_row.start_time = start_time.isoformat()
            event_row.end_time = end_time.isoformat()
            event_row.attendees_json = json.dumps(details.attendees)
            
            if hasattr(details, "is_recurring"):
                event_row.is_recurring = getattr(details, "is_recurring")
            if hasattr(details, "recurrence_rule"):
                event_row.recurrence_rule = getattr(details, "recurrence_rule")
            if hasattr(details, "reminder_minutes"):
                event_row.reminder_minutes_before = getattr(details, "reminder_minutes")
                
            session.commit()
            logger.info("Local event updated: %s (%s)", details.title, event_id)
            return self._row_to_dict(event_row)
        finally:
            self._close_db(session)

    def delete_event(self, event_id: str) -> None:
        session = self._get_db()
        try:
            event_row = session.query(LocalCalendarEvent).filter_by(event_id=event_id).first()
            if event_row:
                session.delete(event_row)
                session.commit()
                logger.info("Local event deleted: %s", event_id)
        finally:
            self._close_db(session)

    def list_events(self) -> list[dict[str, Any]]:
        session = self._get_db()
        try:
            rows = session.query(LocalCalendarEvent).all()
            return [self._row_to_dict(r) for r in rows]
        finally:
            self._close_db(session)

    def search_events(self, query: str) -> list[dict[str, Any]]:
        session = self._get_db()
        try:
            query_str = f"%{query}%"
            rows = session.query(LocalCalendarEvent).filter(
                (LocalCalendarEvent.title.like(query_str)) |
                (LocalCalendarEvent.attendees_json.like(query_str))
            ).all()
            return [self._row_to_dict(r) for r in rows]
        finally:
            self._close_db(session)

    def get_events_for_range(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Day/Week/Month range query support."""
        session = self._get_db()
        try:
            rows = session.query(LocalCalendarEvent).filter(
                (LocalCalendarEvent.date >= start_date) &
                (LocalCalendarEvent.date <= end_date)
            ).all()
            return [self._row_to_dict(r) for r in rows]
        finally:
            self._close_db(session)

    def export_ics(self) -> str:
        events = self.list_events()
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//MeetingPilot//LocalCalendar//EN"
        ]
        
        for ev in events:
            start_dt = datetime.fromisoformat(ev["start_time"]).strftime("%Y%m%dT%H%M%SZ")
            end_dt = datetime.fromisoformat(ev["end_time"]).strftime("%Y%m%dT%H%M%SZ")
            
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{ev['event_id']}",
                f"DTSTAMP:{start_dt}",
                f"DTSTART:{start_dt}",
                f"DTEND:{end_dt}",
                f"SUMMARY:{ev['title']}",
                f"DESCRIPTION:Duration {ev['duration']}. Attendees: {', '.join(ev['attendees'])}",
                "END:VEVENT"
            ])
            
        lines.append("END:VCALENDAR")
        return "\n".join(lines)

    def import_ics(self, ics_text: str) -> int:
        imported = 0
        current_event: dict[str, Any] = {}
        in_vevent = False

        session = self._get_db()
        try:
            for line in ics_text.splitlines():
                line = line.strip()
                if not line:
                    continue

                if line == "BEGIN:VEVENT":
                    current_event = {}
                    in_vevent = True
                elif line == "END:VEVENT" and in_vevent:
                    event_id = current_event.get("event_id") or f"evt-{uuid.uuid4()}"
                    title = current_event.get("title", "Imported Event")
                    start_iso = current_event.get("start_time") or datetime.now(timezone.utc).isoformat()
                    end_iso = current_event.get("end_time") or (datetime.fromisoformat(start_iso) + timedelta(hours=1)).isoformat()
                    
                    event_row = LocalCalendarEvent(
                        event_id=event_id,
                        title=title,
                        date=datetime.fromisoformat(start_iso).strftime("%Y-%m-%d"),
                        time=datetime.fromisoformat(start_iso).strftime("%H:%M"),
                        duration="1h",
                        start_time=start_iso,
                        end_time=end_iso,
                        attendees_json=json.dumps(current_event.get("attendees", [])),
                        is_recurring=False,
                        recurrence_rule=None,
                        reminder_minutes_before=15
                    )
                    session.merge(event_row)
                    imported += 1
                    in_vevent = False
                elif in_vevent:
                    if ":" in line:
                        key, val = line.split(":", 1)
                        key = key.upper()
                        
                        if key == "UID":
                            current_event["event_id"] = val
                        elif key == "SUMMARY":
                            current_event["title"] = val
                        elif key in ("DTSTART", "DTSTART;VALUE=DATE"):
                            try:
                                dt = datetime.strptime(val.replace("Z", ""), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                                current_event["start_time"] = dt.isoformat()
                            except Exception:
                                pass
                        elif key in ("DTEND", "DTEND;VALUE=DATE"):
                            try:
                                dt = datetime.strptime(val.replace("Z", ""), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                                current_event["end_time"] = dt.isoformat()
                            except Exception:
                                pass
            if imported > 0:
                session.commit()
        finally:
            self._close_db(session)
            
        return imported

    def _row_to_dict(self, row: LocalCalendarEvent) -> dict[str, Any]:
        try:
            atts = json.loads(row.attendees_json)
        except Exception:
            atts = []
            
        return {
            "event_id": row.event_id,
            "title": row.title,
            "date": row.date,
            "time": row.time,
            "duration": row.duration,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "attendees": atts,
            "calendar_link": f"http://local-calendar/events/{row.event_id}",
            "google_meet_link": f"http://local-calendar/meet/{row.event_id}",
            "is_recurring": row.is_recurring,
            "recurrence_rule": row.recurrence_rule,
            "reminder_minutes": row.reminder_minutes_before
        }
