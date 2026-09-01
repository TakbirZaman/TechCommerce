"""
Shared FastAPI dependencies for the discovery module.

Auth: No authentication required for browsing/search.
Admin endpoints are protected separately.
"""
from __future__ import annotations

from typing import Generator, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.stubs import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_optional() -> Optional[dict]:
    """
    Returns None - all browsing/search is public.
    No authentication required for users.
    """
    return None


def get_current_user_required() -> Optional[dict]:
    """
    Returns None - all endpoints are public.
    """
    return None


def get_current_admin_user() -> Optional[dict]:
    """
    Admin auth is handled separately in admin endpoints.
    This dependency is kept for compatibility but does nothing.
    """
    return None
