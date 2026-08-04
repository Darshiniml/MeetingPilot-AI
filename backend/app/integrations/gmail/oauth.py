"""OAuth helper utilities for Gmail."""

from app.integrations.google_calendar.token_store import TokenStore
from sqlalchemy.orm import Session

def is_gmail_connected(session: Session, user_id: int) -> bool:
    """Check if the user has connected Google Calendar AND authorized Gmail Send scope."""
    token_store = TokenStore(session)
    token_record = token_store.get_token(user_id)
    if not token_record or not token_record.is_connected:
        return False
        
    scopes = token_record.scopes or ""
    return "gmail.send" in scopes
