from sqlalchemy.orm import Session
from datetime import datetime
from app.scheduler.meeting_parser import MeetingParser
from app.scheduler.email_draft_service import EmailDraftService
from app.scheduler.calendar_service import CalendarProvider
from app.integrations.gmail.gmail_provider import EmailProvider
from app.scheduler.schemas import SchedulerPlanResponse, MeetingDetails

class SchedulerService:
    def __init__(
        self,
        session: Session,
        parser: MeetingParser,
        email_service: EmailDraftService,
        calendar_provider: CalendarProvider,
        email_provider: EmailProvider
    ) -> None:
        self._session = session
        self._parser = parser
        self._email_service = email_service
        self._calendar = calendar_provider
        self._email_provider = email_provider

    def create_meeting_event(self, user_id: int, details: MeetingDetails, meeting_id: int | None = None) -> dict:
        """Create a calendar event, send invitation emails, and link to Meeting record."""
        event = self._calendar.create_event(details)
        
        from app.models.meeting import Meeting, MeetingStatus
        
        if meeting_id:
            meeting = self._session.get(Meeting, meeting_id)
            if not meeting:
                raise ValueError("Meeting not found.")
        else:
            meeting = Meeting(
                title=details.title,
                status=MeetingStatus.CREATED,
                user_id=user_id
            )
            self._session.add(meeting)
            
        meeting.google_event_id = event["event_id"]
        meeting.google_meet_link = event.get("google_meet_link")
        meeting.calendar_url = event["calendar_link"]
        
        # Send emails automatically if attendees list is present
        if details.attendees:
            draft_text = self._email_service.generate_draft(details)
            meet_link = event.get("google_meet_link") or event["calendar_link"]
            
            if "[Insert Meeting Link Here]" in draft_text:
                draft_text = draft_text.replace("[Insert Meeting Link Here]", meet_link)
            elif "http" not in draft_text:
                draft_text += f"\nJoin Meeting: {meet_link}"

            from app.integrations.gmail.email_templates import load_template
            html_body = load_template("invitation", details, meet_link, draft_text)
            
            subject = f"Invitation: {details.title}"
            for email in details.attendees:
                try:
                    result = self._email_provider.send_html_email(
                        to_email=email,
                        subject=subject,
                        html_body=html_body,
                        meeting_id=meeting.id,
                        thread_id=meeting.gmail_thread_id
                    )
                    if not meeting.gmail_message_id:
                        meeting.gmail_message_id = result.get("message_id")
                        meeting.gmail_thread_id = result.get("thread_id")
                        meeting.invitation_sent_at = datetime.utcnow()
                        meeting.invitation_status = "SENT"
                        meeting.last_email_at = datetime.utcnow()
                except Exception:
                    meeting.invitation_status = "FAILED"
                    pass

        self._session.commit()
        return event

    def send_meeting_invitations(self, user_id: int, meeting_id: int, attendees: list[str]) -> dict:
        """Manually trigger sending invitations for an existing meeting."""
        from app.models.meeting import Meeting
        meeting = self._session.get(Meeting, meeting_id)
        if not meeting or meeting.user_id != user_id:
            raise ValueError("Meeting not found.")
            
        if not meeting.google_event_id:
            raise ValueError("Meeting has no Google Calendar event.")
            
        details = MeetingDetails(
            title=meeting.title,
            date=meeting.started_at.strftime("%Y-%m-%d") if meeting.started_at else datetime.utcnow().strftime("%Y-%m-%d"),
            time=meeting.started_at.strftime("%H:%M") if meeting.started_at else "12:00",
            duration="1h",
            timezone="UTC",
            attendees=attendees
        )
        
        draft_text = self._email_service.generate_draft(details)
        meet_link = meeting.google_meet_link or meeting.calendar_url or ""
        
        if "[Insert Meeting Link Here]" in draft_text:
            draft_text = draft_text.replace("[Insert Meeting Link Here]", meet_link)
        elif meet_link and "http" not in draft_text:
            draft_text += f"\nJoin Meeting: {meet_link}"

        from app.integrations.gmail.email_templates import load_template
        html_body = load_template("invitation", details, meet_link, draft_text)
        
        subject = f"Invitation: {details.title}"
        last_result = {}
        for email in attendees:
            try:
                result = self._email_provider.send_html_email(
                    to_email=email,
                    subject=subject,
                    html_body=html_body,
                    meeting_id=meeting.id,
                    thread_id=meeting.gmail_thread_id
                )
                last_result = result
                if not meeting.gmail_message_id:
                    meeting.gmail_message_id = result.get("message_id")
                    meeting.gmail_thread_id = result.get("thread_id")
                    meeting.invitation_sent_at = datetime.utcnow()
                    meeting.invitation_status = "SENT"
                    meeting.last_email_at = datetime.utcnow()
            except Exception as e:
                meeting.invitation_status = "FAILED"
                raise RuntimeError(f"Failed to send to {email}: {str(e)}") from e
                
        self._session.commit()
        return last_result

    def plan_meeting(self, request_text: str, user_id: int | None = None) -> SchedulerPlanResponse:
        details = self._parser.parse(request_text)
        
        attendee_resolutions = []
        resolved_emails = []
        
        if user_id is not None:
            from app.contacts.contact_repository import ContactRepository
            from app.contacts.contact_matcher import ContactMatcher
            
            repo = ContactRepository(self._session, user_id)
            contacts = repo.list_contacts(limit=1000)
            matcher = ContactMatcher(repo)
            
            for attendee in details.attendees:
                res = matcher.resolve_attendee(attendee, contacts, context_text=request_text)
                attendee_resolutions.append(res)
                if res["resolved_email"]:
                    resolved_emails.append(res["resolved_email"])
                else:
                    resolved_emails.append(attendee)
        else:
            resolved_emails = details.attendees
            for attendee in details.attendees:
                attendee_resolutions.append({
                    "input_name": attendee,
                    "resolved_email": attendee,
                    "status": "RESOLVED",
                    "confidence_score": 1.0,
                    "source": "INPUT",
                    "candidates": []
                })
                
        # Update details attendees list with resolved emails
        details.attendees = resolved_emails

        preview = self._calendar.check_availability(details)
        draft = self._email_service.generate_draft(details)

        return SchedulerPlanResponse(
            title=details.title,
            date=details.date,
            time=details.time,
            duration=details.duration,
            attendees=resolved_emails,
            email_draft=draft,
            calendar_preview=preview,
            attendee_resolutions=attendee_resolutions
        )
