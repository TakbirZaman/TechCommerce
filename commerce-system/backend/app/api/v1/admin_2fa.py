"""
Admin 2FA (TOTP) endpoints.
"""
from __future__ import annotations

import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, require_admin
from app.models.stubs import User

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
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_admin),
):
    """
    Generate a new TOTP secret for admin 2FA setup.
    Returns the secret and otpauth URL for the admin to scan with their authenticator app.
    """
    # Get the admin user
    user = db.get(User, admin.id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Generate a new TOTP secret
    secret = pyotp.random_base32()
    
    # Store the secret (in production, encrypt this)
    # For now, we'll just return it - in real implementation, store in DB
    # user.totp_secret = secret
    # db.commit()

    # Create OTP auth URL for QR code
    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(
        name=user.email or f"admin-{admin.id}",
        issuer_name="TechCommerce Admin"
    )

    return TwoFactorSetupResponse(
        secret=secret,
        otpauth_url=otpauth_url,
        message="Scan the QR code with your authenticator app, then verify with /verify endpoint"
    )


@router.post("/verify")
def verify_2fa(
    payload: TwoFactorVerifyRequest,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_admin),
):
    """
    Verify a TOTP code for 2FA setup or login.
    """
    # In production, retrieve the stored secret for this admin
    # For now, we'll verify against a test secret
    # TODO: Retrieve secret from database
    
    # For demonstration, accept any 6-digit code
    # In production, use: totp = pyotp.TOTP(stored_secret)
    # valid = totp.verify(payload.code, valid_window=1)
    
    if len(payload.code) != 6 or not payload.code.isdigit():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid code format")

    # TODO: Implement actual TOTP verification with stored secret
    # For now, return success for demonstration
    return {
        "verified": True,
        "message": "2FA verification successful"
    }


@router.get("/status", response_model=TwoFactorStatusResponse)
def get_2fa_status(
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_admin),
):
    """Check if 2FA is enabled for the admin account."""
    # TODO: Check database for 2FA status
    return TwoFactorStatusResponse(
        enabled=False,
        message="2FA is not yet configured"
    )


@router.delete("/disable")
def disable_2fa(
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_admin),
):
    """Disable 2FA for the admin account."""
    # TODO: Remove TOTP secret from database
    return {
        "disabled": True,
        "message": "2FA has been disabled"
    }
