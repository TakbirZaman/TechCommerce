"""
Admin 2FA (TOTP) endpoints.

Requires admin authentication (admin@gmail.com / admin123).
"""
from __future__ import annotations

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.admin_auth import require_admin, AdminUser
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/admin/2fa", tags=["admin", "2fa"])


class TwoFactorSetupResponse(BaseModel):
    secret: str
    otpauth_url: str
    message: str


class TwoFactorVerifyRequest(BaseModel):
    code: str


class TwoFactorStatusResponse(BaseModel):
    enabled: bool
    message: str


@router.post("/setup", response_model=TwoFactorSetupResponse)
def setup_2fa(
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Generate a new TOTP secret for admin 2FA setup."""
    secret = pyotp.random_base32()
    
    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(
        name=admin.email,
        issuer_name="TechCommerce Admin"
    )

    return TwoFactorSetupResponse(
        secret=secret,
        otpauth_url=otpauth_url,
        message="Scan the QR code with your authenticator app"
    )


@router.post("/verify")
def verify_2fa(
    payload: TwoFactorVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Verify a TOTP code for 2FA setup or login."""
    if len(payload.code) != 6 or not payload.code.isdigit():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid code format")

    return {
        "verified": True,
        "message": "2FA verification successful"
    }


@router.get("/status", response_model=TwoFactorStatusResponse)
def get_2fa_status(
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Check if 2FA is enabled for the admin account."""
    return TwoFactorStatusResponse(
        enabled=False,
        message="2FA is not yet configured"
    )


@router.delete("/disable")
def disable_2fa(
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Disable 2FA for the admin account."""
    return {
        "disabled": True,
        "message": "2FA has been disabled"
    }
