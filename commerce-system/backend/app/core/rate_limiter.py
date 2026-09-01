"""
Rate limiting utilities for the commerce module.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """
    Simple in-memory rate limiter for development.
    Replace with Redis-backed implementation in production.
    """

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if a request should be rate-limited.
        
        Args:
            key: Unique identifier for the rate limit bucket
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
            
        Returns:
            True if rate limited, False if request allowed
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            # Clean up old entries
            self._requests[key] = [t for t in self._requests[key] if t > window_start]

            # Check if rate limited
            if len(self._requests[key]) >= max_requests:
                return True

            # Record this request
            self._requests[key].append(now)
            return False

    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests allowed in current window."""
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            recent_requests = [t for t in self._requests[key] if t > window_start]
            return max(0, max_requests - len(recent_requests))


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_payment_callback_rate_limit(gateway: str, ip_address: str) -> bool:
    """
    Check rate limit for payment callback endpoints.
    
    Args:
        gateway: Payment gateway name (bkash, nagad, sslcommerz)
        ip_address: Client IP address
        
    Returns:
        True if rate limited, False if allowed
    """
    key = f"payment_callback:{gateway}:{ip_address}"
    return rate_limiter.is_rate_limited(
        key=key,
        max_requests=100,  # 100 requests per window
        window_seconds=60,  # 1 minute window
    )


def check_login_rate_limit(email: str, ip_address: str) -> bool:
    """
    Check rate limit for login attempts.
    
    Args:
        email: User's email
        ip_address: Client IP address
        
    Returns:
        True if rate limited, False if allowed
    """
    key = f"login:{email}:{ip_address}"
    return rate_limiter.is_rate_limited(
        key=key,
        max_requests=5,  # 5 attempts per window
        window_seconds=900,  # 15 minute window
    )


def get_payment_callback_rate_limit_remaining(gateway: str, ip_address: str) -> int:
    """Get remaining callback requests allowed."""
    key = f"payment_callback:{gateway}:{ip_address}"
    return rate_limiter.get_remaining(key, 100, 60)


def get_login_rate_limit_remaining(email: str, ip_address: str) -> int:
    """Get remaining login attempts allowed."""
    key = f"login:{email}:{ip_address}"
    return rate_limiter.get_remaining(key, 5, 900)
