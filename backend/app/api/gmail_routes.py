"""Gmail routes for sending emails and checking connection status."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import CurrentUser, DatabaseSession, get_gmail_provider
from app.integrations.gmail.gmail_provider import GmailProvider
from app.integrations.gmail.schemas import GmailSendRequest, GoogleStatusResponse
from app.integrations.gmail.oauth import is_gmail_connected

router = APIRouter(tags=["gmail"])

@router.get("/integrations/google/gmail/status", response_model=GoogleStatusResponse)
def get_gmail_status(user: CurrentUser, session: DatabaseSession) -> GoogleStatusResponse:
    """Check if the user has connected Google Calendar AND authorized Gmail Send scope."""
    connected = is_gmail_connected(session, user.id)
    if connected:
        from app.integrations.google_calendar.token_store import TokenStore
        token_store = TokenStore(session)
        token_record = token_store.get_token(user.id)
        return GoogleStatusResponse(
            is_connected=True,
            google_email=token_record.google_email
        )
    return GoogleStatusResponse(is_connected=False)

@router.post("/gmail/send", status_code=status.HTTP_200_OK)
def send_email_endpoint(
    request: GmailSendRequest,
    user: CurrentUser,
    gmail_provider: GmailProvider = Depends(get_gmail_provider)
) -> dict:
    """Directly send a plain text email via Gmail."""
    try:
        return gmail_provider.send_email(
            to_email=request.to_email,
            subject=request.subject,
            body=request.body
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
