"""
Auth integration with core-platform.

IMPORTANT: Commerce does NOT issue tokens or own user credentials.
core-platform (feature/core-platform) is the source of truth for
authentication. This module only VERIFIES the JWT that core-platform
issued and extracts the identity/role claims needed for authorization
decisions inside the commerce service.

Replace `ALGORITHM`/claim names below to match whatever core-platform
actually emits once that branch exists. Until then this is a reasonable
stand-in: sub=user_id, role=<string>, exp=<unix ts>.
"""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class CurrentUser:
    id: int
    role: str
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


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    payload = _decode_token(credentials.credentials)

    user_id = payload.get("sub")
    role = payload.get("role", "customer")
    email = payload.get("email")

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    return CurrentUser(id=int(user_id), role=role, email=email)


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
