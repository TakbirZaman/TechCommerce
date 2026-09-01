"""
Auth API Routes

Endpoints:
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- POST /api/v1/auth/forgot-password
- POST /api/v1/auth/reset-password
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.database import get_db
from core.services.auth_service import (
    authenticate_user,
    create_refresh_token,
    create_user,
    generate_password_reset_token,
    revoke_refresh_token,
    reset_password,
    validate_refresh_token,
)
from core.services.token_service import create_access_token, decode_token_user_id

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# Request/Response schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Extract current user from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]
    user_id = decode_token_user_id(token)
    if user_id is None:
        return None
    
    return db.get("User", user_id)


def require_auth(request: Request, db: Session = Depends(get_db)):
    """Require authentication."""
    user = get_current_user(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        user = create_user(
            db=db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            phone=payload.phone,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    
    access_token = create_access_token({"user_id": user.id, "role": user.role})
    refresh_token = create_refresh_token(db, user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    access_token = create_access_token({"user_id": user.id, "role": user.role})
    refresh_token = create_refresh_token(db, user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    user = validate_refresh_token(db, payload.refresh_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    # Revoke old refresh token
    revoke_refresh_token(db, payload.refresh_token)
    
    # Create new tokens
    access_token = create_access_token({"user_id": user.id, "role": user.role})
    refresh_token = create_refresh_token(db, user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    )


@router.post("/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Logout by revoking refresh token."""
    revoke_refresh_token(db, payload.refresh_token)
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request password reset email."""
    token = generate_password_reset_token(db, payload.email)
    
    # In production, send email with token
    # For now, return token (REMOVE IN PRODUCTION)
    if token:
        return {"message": "Password reset email sent", "debug_token": token}
    else:
        # Don't reveal if email exists
        return {"message": "Password reset email sent"}


@router.post("/reset-password")
def reset_password_endpoint(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using token."""
    success = reset_password(db, payload.token, payload.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return {"message": "Password reset successful"}


@router.get("/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    """Get current user info."""
    user = get_current_user(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
