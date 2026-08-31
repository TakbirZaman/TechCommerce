"""
Shared FastAPI dependencies.

STUB NOTE: get_db, get_current_user, get_current_admin_user, and
get_rate_limiter below MUST be replaced with the real implementations from
feature/core-platform's auth module. They are stubbed here only so this
module is self-contained and its contracts (return types) are explicit.
"""
from __future__ import annotations

from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.stubs import SessionLocal, configure_engine

if SessionLocal.kw.get("bind") is None:
    configure_engine()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CurrentUser:
    """Mirrors the shape expected from core-platform's auth dependency."""

    def __init__(self, id: int, is_admin: bool = False):
        self.id = id
        self.is_admin = is_admin


def get_current_user_optional() -> Optional[CurrentUser]:
    """
    STUB: real implementation reads/validates the auth token and returns
    None for anonymous requests (search/browse must work unauthenticated).
    """
    return None


def get_current_user_required() -> CurrentUser:
    """STUB: replace with core-platform's required-auth dependency."""
    user = get_current_user_optional()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return user


def get_current_admin_user(user: CurrentUser = Depends(get_current_user_required)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    return user
