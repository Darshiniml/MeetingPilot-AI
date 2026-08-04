"""OAuth 2.0 flow implementation for Google Calendar."""

import httpx
from datetime import datetime, timedelta, timezone
from app.config.settings import get_settings

class GoogleOAuthService:
    """Handles authorization URL generation, token exchanges, and token refreshing."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def get_authorization_url(self, state: str) -> str:
        """Construct the Google OAuth 2.0 consent page URL."""
        # state holds the user JWT or state token
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": self._settings.google_client_id,
            "redirect_uri": self._settings.google_redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/contacts.readonly",
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }
        # Encode params manually to avoid urlencode dependency issues
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange the callback code for access, refresh tokens, and email."""
        url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": self._settings.google_client_id,
            "client_secret": self._settings.google_client_secret,
            "redirect_uri": self._settings.google_redirect_uri,
            "grant_type": "authorization_code"
        }
        
        with httpx.Client() as client:
            resp = client.post(url, data=data)
            if resp.status_code != 200:
                raise RuntimeError(f"Google OAuth token exchange failed: {resp.text}")
            
            token_data = resp.json()
            
            # Fetch user email using access_token
            access_token = token_data["access_token"]
            userinfo_resp = client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if userinfo_resp.status_code != 200:
                raise RuntimeError(f"Google UserInfo fetch failed: {userinfo_resp.text}")
                
            userinfo = userinfo_resp.json()
            email = userinfo.get("email")
            if not email:
                raise RuntimeError("No email returned by Google userinfo endpoint")

        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return {
            "google_email": email,
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": expires_at,
            "scopes": token_data.get("scope")
        }

    def refresh_access_token(self, refresh_token: str) -> dict:
        """Exchange a refresh token for a new access token."""
        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self._settings.google_client_id,
            "client_secret": self._settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        with httpx.Client() as client:
            resp = client.post(url, data=data)
            if resp.status_code != 200:
                raise RuntimeError(f"Google OAuth token refresh failed: {resp.text}")
            
            token_data = resp.json()

        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return {
            "access_token": token_data["access_token"],
            "expires_at": expires_at
        }
