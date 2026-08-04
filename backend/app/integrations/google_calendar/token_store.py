"""Token storage management with encryption."""

import base64
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet

from app.config.settings import get_settings
from app.models.google_calendar_token import GoogleCalendarToken

def _get_fernet() -> Fernet:
    settings = get_settings()
    # Deriving 32-byte key for Fernet from the configured encryption key
    key_bytes = settings.google_token_encryption_key.encode("utf-8")
    derived_key = hashlib.sha256(key_bytes).digest()
    return Fernet(base64.urlsafe_b64encode(derived_key))

def encrypt_token(token: str) -> str:
    """Encrypt a token string using Fernet AES encryption."""
    f = _get_fernet()
    return f.encrypt(token.encode("utf-8")).decode("utf-8")

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token string using Fernet AES decryption."""
    f = _get_fernet()
    return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")

class TokenStore:
    """Store, retrieve, and disconnect Google OAuth tokens."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save_token(
        self,
        user_id: int,
        google_email: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime,
        scopes: str | None = None
    ) -> GoogleCalendarToken:
        """Create or update Google OAuth tokens for a user, encrypting secrets."""
        token_record = self.get_token(user_id)
        
        encrypted_access = encrypt_token(access_token)
        encrypted_refresh = encrypt_token(refresh_token) if refresh_token else None

        if token_record:
            token_record.google_email = google_email
            token_record.access_token = encrypted_access
            if encrypted_refresh:
                token_record.refresh_token = encrypted_refresh
            token_record.expires_at = expires_at
            if scopes:
                token_record.scopes = scopes
            token_record.is_connected = True
            token_record.updated_at = datetime.utcnow()
        else:
            token_record = GoogleCalendarToken(
                user_id=user_id,
                google_email=google_email,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                expires_at=expires_at,
                scopes=scopes,
                is_connected=True
            )
            self._session.add(token_record)

        self._session.commit()
        return token_record

    def get_token(self, user_id: int) -> GoogleCalendarToken | None:
        """Query raw token record for a user."""
        return (
            self._session.query(GoogleCalendarToken)
            .filter(GoogleCalendarToken.user_id == user_id)
            .first()
        )

    def get_decrypted_tokens(self, user_id: int) -> dict | None:
        """Retrieve connection info with decrypted access and refresh tokens."""
        token_record = self.get_token(user_id)
        if not token_record or not token_record.is_connected:
            return None

        return {
            "google_email": token_record.google_email,
            "access_token": decrypt_token(token_record.access_token),
            "refresh_token": decrypt_token(token_record.refresh_token) if token_record.refresh_token else None,
            "expires_at": token_record.expires_at,
            "is_connected": token_record.is_connected
        }

    def disconnect(self, user_id: int) -> None:
        """Mark connection as disconnected and clean tokens."""
        token_record = self.get_token(user_id)
        if token_record:
            token_record.is_connected = False
            token_record.access_token = ""
            token_record.refresh_token = None
            self._session.commit()
