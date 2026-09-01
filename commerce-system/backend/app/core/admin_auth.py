"""
Simple Admin Authentication.

Admin: admin@gmail.com / admin123
No complex JWT - simple session-based auth for admin only.
Users browse and checkout as guests - no login required.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)

# Admin credentials (in production, use environment variables and hash passwords)
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()

# Simple session store (in production, use Redis)
_sessions: dict[str, dict] = {}


@dataclass(frozen=True)
class AdminUser:
    """Admin user - the only authenticated role."""
    id: int = 1
    email: str = ADMIN_EMAIL
    role: str = "admin"

    @property
    def is_admin(self) -> bool:
        return True


def verify_admin_credentials(email: str, password: str) -> bool:
    """Verify admin login credentials."""
    return email.lower() == ADMIN_EMAIL and hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH


def create_admin_session() -> str:
    """Create a new admin session and return the token."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "user_id": 1,
        "email": ADMIN_EMAIL,
        "role": "admin",
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24),
    }
    return token


def validate_admin_session(token: str) -> AdminUser | None:
    """Validate an admin session token."""
    session = _sessions.get(token)
    if session is None:
        return None
    
    if datetime.now() > session["expires_at"]:
        del _sessions[token]
        return None
    
    return AdminUser(id=session["user_id"], email=session["email"], role=session["role"])


def invalidate_admin_session(token: str) -> None:
    """Invalidate (logout) an admin session."""
    _sessions.pop(token, None)


def get_current_admin_user(
    request: Request,
    credentials=None,
) -> AdminUser | None:
    """
    Get current admin user from session token.
    Returns None if not authenticated.
    """
    # Check Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return validate_admin_session(token)
    
    # Check cookie
    token = request.cookies.get("admin_session")
    if token:
        return validate_admin_session(token)
    
    return None


def require_admin(
    request: Request,
    credentials=None,
) -> AdminUser:
    """
    Require admin authentication.
    Raises 401 if not authenticated as admin.
    """
    admin = get_current_admin_user(request, credentials)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin
