"""
Shared FastAPI dependencies for the discovery module.

Auth: Validates JWT tokens issued by core-platform. Discovery does NOT
issue tokens - it only verifies them and extracts identity/role claims.

Database: Provides SQLAlchemy sessions for PostgreSQL access.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.stubs import SessionLocal

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@dataclass(frozen=True)
class CurrentUser:
    """Mirrors the shape expected from core-platform's auth dependency."""
    id: int
    role: str = "customer"
    email: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role in {"admin", "superadmin"}


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[CurrentUser]:
    """
    Returns the current user if a valid token is provided, None otherwise.
    Used for endpoints that work both authenticated and匿名 (e.g., search, browse).
    """
    if credentials is None:
        return None

    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")
    role = payload.get("role", "customer")
    email = payload.get("email")

    if user_id is None:
        return None

    return CurrentUser(id=int(user_id), role=role, email=email)


def get_current_user_required(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> CurrentUser:
    """Required authentication - returns 401 if no valid token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")
    role = payload.get("role", "customer")
    email = payload.get("email")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return CurrentUser(id=int(user_id), role=role, email=email)


def get_current_admin_user(user: CurrentUser = Depends(get_current_user_required)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    return user
