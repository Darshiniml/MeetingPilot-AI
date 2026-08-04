"""Gmail provider implementation conforming to provider-agnostic EmailProvider interface."""

import base64
import time
import httpx
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from typing import Any, Protocol
from sqlalchemy.orm import Session

from app.models.email_log import EmailLog
from app.integrations.google_calendar.token_store import TokenStore
from app.integrations.google_calendar.oauth import GoogleOAuthService

class EmailProvider(Protocol):
    def send_email(self, to_email: str, subject: str, body: str, meeting_id: int | None = None, thread_id: str | None = None) -> dict[str, Any]:
        ...

    def send_html_email(self, to_email: str, subject: str, html_body: str, meeting_id: int | None = None, thread_id: str | None = None) -> dict[str, Any]:
        ...

    def reply_email(self, to_email: str, subject: str, html_body: str, thread_id: str, meeting_id: int | None = None) -> dict[str, Any]:
        ...

    def draft_email(self, to_email: str, subject: str, html_body: str, meeting_id: int | None = None) -> dict[str, Any]:
        ...

    def list_sent_messages(self) -> list[dict[str, Any]]:
        ...

class GmailProvider:
    """Gmail sending provider with transient error retry and db logging."""

    def __init__(self, session: Session, user_id: int) -> None:
        self._session = session
        self._user_id = user_id
        self._token_store = TokenStore(session)
        self._oauth = GoogleOAuthService()

    def _get_access_token(self) -> str:
        """Retrieve connection info, check scopes and refresh token automatically."""
        decrypted = self._token_store.get_decrypted_tokens(self._user_id)
        if not decrypted:
            raise RuntimeError("Gmail Account is not connected.")

        # Check for Gmail scopes presence
        token_record = self._token_store.get_token(self._user_id)
        scopes = token_record.scopes or ""
        if "gmail.send" not in scopes:
            raise RuntimeError("Gmail permissions ('gmail.send' scope) not authorized.")

        expires_at = decrypted["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if now + timedelta(minutes=1) >= expires_at:
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

    def _get_sender_email(self) -> str:
        decrypted = self._token_store.get_decrypted_tokens(self._user_id)
        return decrypted["google_email"] if decrypted else "me"

    def _send_raw_message(self, raw_b64: str, thread_id: str | None = None) -> dict[str, Any]:
        """HTTP call to Gmail send API with transient retry logic."""
        token = self._get_access_token()
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"raw": raw_b64}
        if thread_id:
            payload["threadId"] = thread_id

        max_retries = 3
        delay = 1.0

        for attempt in range(max_retries):
            try:
                with httpx.Client() as client:
                    resp = client.post(url, headers=headers, json=payload)
                    # Transient error categories: 429 rate limit or 5xx server issues
                    if resp.status_code in (429, 500, 502, 503, 504):
                        resp.raise_for_status()
                    elif resp.status_code != 200:
                        raise RuntimeError(f"Gmail API error: {resp.text}")
                    
                    data = resp.json()
                    return {
                        "message_id": data["id"],
                        "thread_id": data["threadId"]
                    }
            except (httpx.HTTPError, httpx.RequestError) as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Gmail Send request failed after {max_retries} attempts: {str(e)}") from e
                time.sleep(delay)
                delay *= 2

    def _log_email(
        self,
        meeting_id: int | None,
        recipient: str,
        subject: str,
        body: str,
        status: str,
        error_msg: str | None = None
    ) -> None:
        log_entry = EmailLog(
            meeting_id=meeting_id,
            recipient=recipient,
            subject=subject,
            body=body,
            status=status,
            provider="gmail",
            error_message=error_msg
        )
        self._session.add(log_entry)
        self._session.commit()

    def send_email(self, to_email: str, subject: str, body: str, meeting_id: int | None = None, thread_id: str | None = None) -> dict[str, Any]:
        """Send a plain text email and log results."""
        return self.send_html_email(to_email, subject, f"<p>{body}</p>", meeting_id, thread_id)

    def send_html_email(self, to_email: str, subject: str, html_body: str, meeting_id: int | None = None, thread_id: str | None = None) -> dict[str, Any]:
        """Construct raw RFC 822 email message and send via Gmail API."""
        sender = self._get_sender_email()
        message = MIMEMultipart()
        message["to"] = to_email
        message["from"] = sender
        message["subject"] = subject

        if thread_id:
            # Threading headers
            message["In-Reply-To"] = thread_id
            message["References"] = thread_id

        msg_html = MIMEText(html_body, "html")
        message.attach(msg_html)
        
        raw_b64 = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        try:
            result = self._send_raw_message(raw_b64, thread_id)
            self._log_email(meeting_id, to_email, subject, html_body, "SENT")
            return result
        except Exception as e:
            self._log_email(meeting_id, to_email, subject, html_body, "FAILED", str(e))
            raise

    def reply_email(self, to_email: str, subject: str, html_body: str, thread_id: str, meeting_id: int | None = None) -> dict[str, Any]:
        """Reply to an existing thread."""
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        return self.send_html_email(to_email, subject, html_body, meeting_id, thread_id)

    def draft_email(self, to_email: str, subject: str, html_body: str, meeting_id: int | None = None) -> dict[str, Any]:
        """Create a draft message in Gmail."""
        token = self._get_access_token()
        sender = self._get_sender_email()
        message = MIMEMultipart()
        message["to"] = to_email
        message["from"] = sender
        message["subject"] = subject
        msg_html = MIMEText(html_body, "html")
        message.attach(msg_html)
        raw_b64 = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"message": {"raw": raw_b64}}

        with httpx.Client() as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail Draft creation failed: {resp.text}")
            data = resp.json()
            return {"draft_id": data["id"], "message_id": data["message"]["id"]}

    def list_sent_messages(self) -> list[dict[str, Any]]:
        """List sent messages for the connected user."""
        token = self._get_access_token()
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": "from:me", "maxResults": 10}

        with httpx.Client() as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Gmail list messages failed: {resp.text}")
            messages = resp.json().get("messages", [])
            return [{"message_id": msg["id"], "thread_id": msg["threadId"]} for msg in messages]
