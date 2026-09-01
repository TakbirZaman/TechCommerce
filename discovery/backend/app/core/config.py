"""
Configuration for the Discovery module.

No authentication required - all endpoints are public.
"""
from pydantic_settings import BaseSettings


class DiscoverySettings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/discovery"
    REDIS_URL: str = "redis://localhost:6379/0"

    CACHE_TTL_CATEGORY: int = 60 * 30
    CACHE_TTL_BRAND: int = 60 * 30
    CACHE_TTL_PRODUCT_DETAIL: int = 60 * 10
    CACHE_TTL_AUTOCOMPLETE: int = 60 * 5
    CACHE_TTL_RATING_AGG: int = 60 * 15

    SEARCH_DEFAULT_PAGE_SIZE: int = 24
    SEARCH_MAX_PAGE_SIZE: int = 100

    REVIEW_RATE_LIMIT_PER_HOUR: int = 5

    class Config:
        env_prefix = "DISCOVERY_"


settings = DiscoverySettings()
