"""
Thin Redis caching layer, used selectively (Section 27).

Design goals:
- Explicit, opt-in caching per read path (never blanket-cache everything).
- Simple invalidation hooks that admin write-paths call directly, rather
  than relying on TTL alone for correctness-sensitive data.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Optional

import redis.asyncio as redis

from app.core.config import settings

_redis: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def cache_get_json(key: str) -> Optional[Any]:
    raw = await get_redis().get(key)
    return json.loads(raw) if raw is not None else None


async def cache_set_json(key: str, value: Any, ttl: int) -> None:
    await get_redis().set(key, json.dumps(value, default=str), ex=ttl)


async def cache_delete(*keys: str) -> None:
    if keys:
        await get_redis().delete(*keys)


async def cache_delete_prefix(prefix: str) -> None:
    """Used for invalidation after admin product/category/brand edits."""
    client = get_redis()
    async for key in client.scan_iter(match=f"{prefix}*"):
        await client.delete(key)


async def cached(key: str, ttl: int, loader: Callable[[], Any]) -> Any:
    """Read-through cache helper: try cache, else call loader() and populate."""
    hit = await cache_get_json(key)
    if hit is not None:
        return hit
    value = await loader()
    await cache_set_json(key, value, ttl)
    return value


def k_category(slug: str) -> str:
    return f"discovery:category:{slug}"


def k_brand(slug: str) -> str:
    return f"discovery:brand:{slug}"


def k_product_detail(product_id: int) -> str:
    return f"discovery:product:{product_id}"


def k_autocomplete(prefix: str) -> str:
    return f"discovery:autocomplete:{prefix.lower()}"


def k_rating_agg(product_id: int) -> str:
    return f"discovery:rating_agg:{product_id}"
