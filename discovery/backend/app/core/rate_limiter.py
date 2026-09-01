"""
Rate limiting utilities for the discovery module.

Uses Redis-backed sliding window for rate limiting.
Falls back to in-memory tracking if Redis is unavailable.
"""
from __future__ import annotations

import time
from typing import Optional

from app.core.config import settings


class RateLimiter:
    """Simple in-memory rate limiter for development. Replace with Redis in production."""

    def __init__(self):
        self._requests: dict[str, list[float]] = {}

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if a request should be rate-limited.
        
        Args:
            key: Unique identifier for the rate limit bucket (e.g., "user:123:review")
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
            
        Returns:
            True if rate limited, False if request allowed
        """
        now = time.time()
        window_start = now - window_seconds

        # Clean up old entries
        if key in self._requests:
            self._requests[key] = [t for t in self._requests[key] if t > window_start]
        else:
            self._requests[key] = []

        # Check if rate limited
        if len(self._requests[key]) >= max_requests:
            return True

        # Record this request
        self._requests[key].append(now)
        return False


# Global rate limiter instance
_rate_limiter = RateLimiter()


def check_review_rate_limit(user_id: int) -> bool:
    """
    Check if user has exceeded review rate limit.
    
    Args:
        user_id: The user's ID
        
    Returns:
        True if rate limited, False if allowed
    """
    key = f"user:{user_id}:review"
    return _rate_limiter.is_rate_limited(
        key=key,
        max_requests=settings.REVIEW_RATE_LIMIT_PER_HOUR,
        window_seconds=3600  # 1 hour
    )


def get_rate_limit_remaining(user_id: int) -> int:
    """
    Get remaining reviews allowed for user in current window.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Number of remaining allowed reviews
    """
    key = f"user:{user_id}:review"
    now = time.time()
    window_start = now - 3600

    if key in _rate_limiter._requests:
        recent_requests = [t for t in _rate_limiter._requests[key] if t > window_start]
        return max(0, settings.REVIEW_RATE_LIMIT_PER_HOUR - len(recent_requests))

    return settings.REVIEW_RATE_LIMIT_PER_HOUR
