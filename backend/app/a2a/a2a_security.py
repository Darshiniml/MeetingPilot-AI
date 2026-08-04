from __future__ import annotations

import hmac
import hashlib
import time
import logging
from typing import Any
from app.a2a.a2a_models import AgentRequest, AgentResponse

logger = logging.getLogger(__name__)

SHARED_SECRET = b"meetingpilot_a2a_secure_shared_secret_key_123!"

# In-memory store for replay protection: (nonce, timestamp)
_seen_nonces: set[tuple[str, float]] = set()
NONCE_VALIDITY_SECONDS = 300.0  # 5 minutes

# Allowed agent names
ALLOWED_AGENTS: set[str] = {
    "supervisor", "meeting", "research", "scheduler", "email", "memory", "vision",
    "github", "slack", "notion", "jira", "salesforce", "teams", "google_drive", "servicenow",
    "external_agent_test"
}

def generate_hmac(payload: str, secret: bytes = SHARED_SECRET) -> str:
    """Generate HMAC-SHA256 signature for a string payload."""
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

def sign_request(request: AgentRequest, secret: bytes = SHARED_SECRET) -> str:
    """Compute signature for an AgentRequest."""
    payload = f"{request.request_id}:{request.trace_id}:{request.sender_name}:{request.receiver_name}:{request.message}:{request.timestamp}:{request.nonce}"
    return generate_hmac(payload, secret)

def verify_request_signature(request: AgentRequest, secret: bytes = SHARED_SECRET) -> bool:
    """Verify HMAC signature on an incoming request."""
    expected = sign_request(request, secret)
    return hmac.compare_digest(expected, request.signature)

def sign_response(response: AgentResponse, secret: bytes = SHARED_SECRET) -> str:
    """Compute signature for an AgentResponse."""
    payload = f"{response.request_id}:{response.trace_id}:{response.status}:{response.answer}:{response.timestamp}"
    return generate_hmac(payload, secret)

def verify_response_signature(response: AgentResponse, secret: bytes = SHARED_SECRET) -> bool:
    """Verify HMAC signature on a received response."""
    expected = sign_response(response, secret)
    return hmac.compare_digest(expected, response.signature)

def validate_request_security(request: AgentRequest, secret: bytes = SHARED_SECRET) -> tuple[bool, str]:
    """
    Perform full security validation of an incoming request:
    1. Signature check
    2. Timestamp validation (prevent stale/delayed replay)
    3. Nonce uniqueness (prevent duplicate replay)
    4. Allow-list check
    """
    # 1. Allow-list validation
    if request.sender_name not in ALLOWED_AGENTS:
        return False, f"Sender agent '{request.sender_name}' is not in the trusted allow-list."

    # 2. Signature verification
    if not verify_request_signature(request, secret):
        return False, "Invalid signature detected."

    # 3. Time skew verification
    now = time.time()
    if abs(now - request.timestamp) > NONCE_VALIDITY_SECONDS:
        return False, f"Request timestamp is outside the valid skew window (+/- {NONCE_VALIDITY_SECONDS}s)."

    # 4. Replay nonce check
    # Prune expired nonces first
    global _seen_nonces
    _seen_nonces = {item for item in _seen_nonces if now - item[1] <= NONCE_VALIDITY_SECONDS}

    nonce_key = (request.nonce, request.timestamp)
    if nonce_key in _seen_nonces:
        return False, "Replay attack detected: Nonce has already been processed."
    
    _seen_nonces.add(nonce_key)
    return True, "Security validation successful."
