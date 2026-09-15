"""
Authentication Service

Handles: Register, Login, Refresh Token, Logout, Forgot Password
Requires bcrypt — fails fast if not installed (no SHA256 fallback).
"""
from datetime import UTC, datetime, timedelta
from typing import Optional

import hashlib
import secrets
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.user import User, RefreshToken, UserRole

try:
    import bcrypt  # type: ignore
except ImportError as _e:
    raise RuntimeError(
        "bcrypt is required for password hashing. Install it via `pip install bcrypt` "
        "(or `pip install -r requirements.txt`). SHA256 fallback has been removed for security."
    ) from _e


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password — only bcrypt hashes are accepted."""
    if not password_hash:
        return False
    # Legacy SHA256 hashes (pre-fix) are no longer considered valid.
    # If you have old SHA256 hashes in DB, force a password reset.
    if not password_hash.startswith("$2"):
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def _hash_token(token: str) -> str:
    """Hash reset tokens with SHA256 (fast, not a password)."""
    return hashlib.sha256(token.encode()).hexdigest()


def _verify_token(token: str, token_hash: str) -> bool:
    return _hash_token(token) == token_hash


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str,
    phone: str | None = None,
    role: UserRole = UserRole.CUSTOMER,
) -> User:
    """Create a new user.

    Bootstrap: if no admin exists yet, the first user OR any user registering
    as admin@gmail.com is promoted to ADMIN so the deployed instance can
    recover from an empty DB without manual SQL.
    """
    existing = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if existing:
        raise ValueError("Email already registered")
    
    # Bootstrap admin if none exists — only canonical admin email auto-promotes
    has_admin = db.execute(select(User).where(User.role == UserRole.ADMIN)).scalar_one_or_none()
    effective_role = role
    if has_admin is None and email.lower() == "admin@gmail.com":
        effective_role = UserRole.ADMIN
    
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        phone=phone,
        role=effective_role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password."""
    user = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    
    user.last_login = datetime.now(UTC)
    db.commit()
    
    return user


def create_refresh_token(db: Session, user: User) -> str:
    """Create a refresh token for the user."""
    token = secrets.token_urlsafe(64)
    expires_at = datetime.now(UTC) + timedelta(days=30)
    
    refresh_token = RefreshToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
    )
    db.add(refresh_token)
    db.commit()
    return token


def validate_refresh_token(db: Session, token: str) -> Optional[User]:
    """Validate refresh token and return user."""
    refresh_token = db.execute(
        select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.now(UTC),
        )
    ).scalar_one_or_none()
    
    if refresh_token is None:
        return None
    
    return db.get(User, refresh_token.user_id)


def revoke_refresh_token(db: Session, token: str) -> bool:
    """Revoke a refresh token (logout)."""
    refresh_token = db.execute(
        select(RefreshToken).where(RefreshToken.token == token)
    ).scalar_one_or_none()
    
    if refresh_token is None:
        return False
    
    refresh_token.is_revoked = True
    db.commit()
    return True


def revoke_all_user_tokens(db: Session, user_id: int) -> int:
    """Revoke all refresh tokens for a user (logout from all devices)."""
    from sqlalchemy import update
    
    result = db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
        .values(is_revoked=True)
    )
    db.commit()
    return result.rowcount


def generate_password_reset_token(db: Session, email: str) -> Optional[str]:
    """Generate a password reset token."""
    user = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if user is None:
        return None
    
    token = secrets.token_urlsafe(32)
    user.reset_token = _hash_token(token)
    user.reset_token_expires = datetime.now(UTC) + timedelta(hours=1)
    db.commit()

    return token


def reset_password(db: Session, token: str, new_password: str) -> bool:
    """Reset password using token."""
    users = db.execute(
        select(User).where(
            User.reset_token.isnot(None),
            User.reset_token_expires > datetime.now(UTC),
        )
    ).scalars().all()
    
    for user in users:
        if _verify_token(token, user.reset_token):
            user.password_hash = hash_password(new_password)
            user.reset_token = None
            user.reset_token_expires = None
            db.commit()
            return True
    
    return False
