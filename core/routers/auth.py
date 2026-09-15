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

from core.database import get_db, SessionLocal
from core.models.user import User, UserRole
from core.services.auth_service import (
    authenticate_user,
    create_refresh_token,
    create_user,
    generate_password_reset_token,
    hash_password,
    revoke_refresh_token,
    reset_password,
    validate_refresh_token,
)
from core.services.token_service import create_access_token, decode_token_user_id
from core.middleware.rate_limit import check_rate_limit

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

# Rate limiting is enforced via middleware (see core/middleware/rate_limit.py)
# for /auth/login, /auth/register, /auth/forgot-password endpoints.


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
    
    return db.get(User, user_id)


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
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request)
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
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request)
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
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request)
    """Request password reset email — never leaks token; always same message."""
    token = generate_password_reset_token(db, payload.email)
    # In production, send email via background task if token is not None.
    # The token is NOT returned to the caller for security.
    # We intentionally return the same message regardless of whether the email exists.
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password_endpoint(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request)
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


# ---------------------------------------------------------------------------
# Bootstrap / emergency endpoints — safe because they only act when no admin
# exists. Allows recovering a fresh Render Postgres that missed the startup seed.
# ---------------------------------------------------------------------------
class BootstrapAdminRequest(BaseModel):
    email: EmailStr | None = None
    password: str | None = None


@router.post("/bootstrap-admin")
def bootstrap_admin(request: Request, db: Session = Depends(get_db)):
    """Create or promote admin@gmail.com to ADMIN.

    Works only when no ADMIN exists yet — after that it is a no-op and
    returns 409. This lets a deployed empty DB recover without SSH/SQL.
    """
    check_rate_limit(request)
    existing_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    if existing_admin:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin already exists")

    target_email = "admin@gmail.com"
    target_password = "admin123"

    # Try to parse optional JSON body if provided (optional promotion of custom email)
    try:
        import json as _json
        body = _json.loads(request.headers.get("X-Bootstrap-Body", "") or "{}")
    except Exception:
        body = {}
    # Also try to read JSON body without failing if empty — FastAPI already consumed? So just use defaults.

    user = db.query(User).filter(User.email == target_email).first()
    if user:
        user.role = UserRole.ADMIN
        user.password_hash = hash_password(target_password)
        user.is_active = True
        db.commit()
        db.refresh(user)
        return {"message": f"Promoted {user.email} to admin", "user": {"id": user.id, "email": user.email, "role": user.role}}

    # Create fresh admin
    user = User(
        email=target_email,
        password_hash=hash_password(target_password),
        full_name="Admin",
        phone="01700000000",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": f"Created admin {user.email}", "user": {"id": user.id, "email": user.email, "role": user.role}}


@router.post("/seed")
def seed_database(request: Request, db: Session = Depends(get_db)):
    """Idempotent seed — creates brands/categories/products if missing.

    Only allowed when catalog is empty OR when no admin exists. Otherwise
    requires an authenticated admin (protects against abuse on prod).
    """
    # Check if seeding is needed: empty catalog
    from core.models.catalog import Brand, Category

    brand_count = db.query(Brand).count()
    cat_count = db.query(Category).count()
    has_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()

    # If DB already seeded and admin exists, require admin auth
    if brand_count > 0 and cat_count > 0 and has_admin:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Seeding already done — admin auth required")
        from core.services.token_service import verify_token
        payload = verify_token(auth_header[7:])
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user = db.get(User, payload.get("user_id"))
        if not user or not user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    check_rate_limit(request)
    try:
        from scripts.seed import seed as _seed
        _seed()
        return {"message": "Database seeded successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Seed failed: {e}")
