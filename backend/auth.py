"""Simple single-user JWT authentication for the admin panel."""

import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import hashlib
import hmac
import json
import base64

# ---------------------------------------------------------------------------
# Config – override via environment variables
# ---------------------------------------------------------------------------

_INSECURE_DEFAULTS = {"admin", "change-me-in-production", "change-me", ""}

ADMIN_PASSWORD = os.environ.get("POKERLOG_ADMIN_PASSWORD", "admin")
JWT_SECRET = os.environ.get("POKERLOG_JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("POKERLOG_JWT_EXPIRE_HOURS", "24"))

# Block startup if running with default secrets outside local dev
if os.environ.get("FLY_APP_NAME"):  # set automatically on Fly.io
    if ADMIN_PASSWORD in _INSECURE_DEFAULTS:
        raise RuntimeError("POKERLOG_ADMIN_PASSWORD is not set — run the setup-secrets workflow")
    if JWT_SECRET in _INSECURE_DEFAULTS:
        raise RuntimeError("POKERLOG_JWT_SECRET is not set — run the setup-secrets workflow")

_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Minimal JWT helpers (no external dependency)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _create_token(payload: dict, secret: str) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    h = _b64url_encode(json.dumps(header).encode())
    p = _b64url_encode(json.dumps(payload, default=str).encode())
    sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def _verify_token(token: str, secret: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("bad token")
        h, p, s = parts
        expected_sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
        actual_sig = _b64url_decode(s)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("bad signature")
        payload = json.loads(_b64url_decode(p))
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise ValueError("token expired")
        return payload
    except Exception as exc:
        raise ValueError(f"Invalid token: {exc}") from exc


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def verify_password(password: str) -> bool:
    return password == ADMIN_PASSWORD


def create_access_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": "admin", "exp": expire.timestamp()}
    return _create_token(payload, JWT_SECRET)


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """FastAPI dependency – raises 401 if not authenticated."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = _verify_token(credentials.credentials, JWT_SECRET)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload.get("sub", "admin")

