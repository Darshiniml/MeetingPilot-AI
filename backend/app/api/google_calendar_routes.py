"""Google Calendar integration routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import jwt

from app.database.session import get_db
from app.core.dependencies import get_current_user, CurrentUser, DatabaseSession
from app.core.security import decode_token
from app.integrations.google_calendar.schemas import GoogleAuthUrlResponse, GoogleStatusResponse
from app.integrations.google_calendar.oauth import GoogleOAuthService
from app.integrations.google_calendar.token_store import TokenStore

router = APIRouter(prefix="/integrations/google", tags=["google-calendar"])

@router.get("/auth-url", response_model=GoogleAuthUrlResponse)
def get_auth_url(
    user: CurrentUser,
    token: str = Query(..., description="The user's active JWT access token to authenticate the callback.")
) -> GoogleAuthUrlResponse:
    """Generate the Google OAuth 2.0 authorization URL."""
    oauth_service = GoogleOAuthService()
    url = oauth_service.get_authorization_url(state=token)
    return GoogleAuthUrlResponse(url=url)

@router.get("/callback", response_class=HTMLResponse)
def oauth_callback(
    code: str,
    state: str,
    session: Session = Depends(get_db)
) -> HTMLResponse:
    """OAuth redirect callback from Google. Authenticates the user via the state JWT."""
    try:
        # Decode and verify the JWT stored in the state parameter
        payload = decode_token(state)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        return HTMLResponse("<h3>Authentication expired. Please link account again.</h3>", status_code=401)
    except Exception:
        return HTMLResponse("<h3>Invalid authentication state.</h3>", status_code=401)

    oauth_service = GoogleOAuthService()
    token_store = TokenStore(session)

    try:
        tokens = oauth_service.exchange_code_for_tokens(code)
        token_store.save_token(
            user_id=user_id,
            google_email=tokens["google_email"],
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_at=tokens["expires_at"],
            scopes=tokens.get("scopes")
        )
    except Exception as e:
        return HTMLResponse(f"<h3>Google Calendar integration failed: {str(e)}</h3>", status_code=500)

    # Return a success HTML page that auto-closes the window
    return HTMLResponse("""
    <html>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h2>Google Calendar Connected Successfully!</h2>
            <p>You can close this window now.</p>
            <script>
                setTimeout(function() { window.close(); }, 3000);
            </script>
        </body>
    </html>
    """)

@router.get("/status", response_model=GoogleStatusResponse)
def get_status(user: CurrentUser, session: DatabaseSession) -> GoogleStatusResponse:
    """Get the current Google Calendar connection status for the user."""
    token_store = TokenStore(session)
    token_record = token_store.get_token(user.id)
    if token_record and token_record.is_connected:
        return GoogleStatusResponse(
            is_connected=True,
            google_email=token_record.google_email
        )
    return GoogleStatusResponse(is_connected=False)

@router.post("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(user: CurrentUser, session: DatabaseSession) -> None:
    """Disconnect Google Calendar by removing saved tokens."""
    token_store = TokenStore(session)
    token_store.disconnect(user.id)
