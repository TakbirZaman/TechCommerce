"""
JWT Token Utilities

Simple token generation for API authentication.
"""
from datetime import UTC, datetime, timedelta
from typing import Optional

import hashlib
import hmac
import json
import base64
import logging
import os


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "techcommerce-secret-key-change-in-production")
if SECRET_KEY == "techcommerce-secret-key-change-in-production":
    logging.getLogger(__name__).warning(
        "JWT_SECRET_KEY is not set — using the well-known default. "
        "Anyone with repo access can forge admin tokens. Set JWT_SECRET_KEY in production!"
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a simple JWT-like token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire.timestamp(), "iat": datetime.now(UTC).timestamp()})
    
    # Simple token format: base64(header).base64(payload).signature
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode()
    payload = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode()
    
    message = f"{header}.{payload}"
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    
    return f"{message}.{signature}"


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        header, payload, signature = parts
        
        # Verify signature
        message = f"{header}.{payload}"
        expected_signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        # Decode payload
        data = json.loads(base64.urlsafe_b64decode(payload + "=="))
        
        # Check expiration
        if datetime.now(UTC).timestamp() > data.get("exp", 0):
            return None
        
        return data
        
    except Exception:
        return None


def decode_token_user_id(token: str) -> Optional[int]:
    """Extract user_id from token."""
    data = verify_token(token)
    if data is None:
        return None
    return data.get("user_id")
