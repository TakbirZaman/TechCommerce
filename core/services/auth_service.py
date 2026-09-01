"""
Authentication Service

Handles: Register, Login, Refresh Token, Logout, Forgot Password
"""
from datetime import UTC, datetime, timedelta
from typing import Optional

import hashlib
import secrets
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.user import User, RefreshToken, UserRole


# Password hashing (simple SHA256 for demo - use bcrypt in production)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str,
    phone: str | None = None,
    role: UserRole = UserRole.CUSTOMER,
) -> User:
    """Create a new user."""
    # Check if email exists
    existing = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if existing:
        raise ValueError("Email already registered")
    
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        phone=phone,
        role=role,
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
    
    # Update last login
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
    user.reset_token = hash_password(token)  # Store hash
    user.reset_token_expires = datetime.now(UTC) + timedelta(hours=1)
    db.commit()
    
    return token  # Return raw token to send via email


def reset_password(db: Session, token: str, new_password: str) -> bool:
    """Reset password using token."""
    # We need to check all users with non-expired reset tokens
    users = db.execute(
        select(User).where(
            User.reset_token.isnot(None),
            User.reset_token_expires > datetime.now(UTC),
        )
    ).scalars().all()
    
    for user in users:
        if verify_password(token, user.reset_token):
            user.password_hash = hash_password(new_password)
            user.reset_token = None
            user.reset_token_expires = None
            db.commit()
            return True
    
    return False
