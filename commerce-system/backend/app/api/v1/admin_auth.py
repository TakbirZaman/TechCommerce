"""
Admin Authentication endpoints.

Simple login for admin only.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.admin_auth import (
    create_admin_session,
    invalidate_admin_session,
    verify_admin_credentials,
)
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/admin/auth", tags=["admin", "auth"])


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    token: str
    message: str


class AdminLogoutRequest(BaseModel):
    token: str


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(
    payload: AdminLoginRequest,
):
    """
    Admin login endpoint.
    Credentials: admin@gmail.com / admin123
    """
    if not verify_admin_credentials(payload.email, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_admin_session()
    return AdminLoginResponse(
        token=token,
        message="Login successful"
    )


@router.post("/logout")
def admin_logout(
    payload: AdminLogoutRequest,
):
    """Admin logout endpoint."""
    invalidate_admin_session(payload.token)
    return {"message": "Logged out successfully"}


@router.get("/me")
def admin_me():
    """
    Check if current session is valid.
    In production, this would validate the token.
    """
    return {"message": "Admin endpoint - use token in Authorization header"}
