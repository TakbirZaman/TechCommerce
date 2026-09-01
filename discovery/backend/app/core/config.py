"""
Configuration for the Discovery module.

In the real monorepo, this imports shared settings from core-platform.
JWT_SECRET_KEY and JWT_ALGORITHM are required for token validation.
"""
from pydantic_settings import BaseSettings


class DiscoverySettings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/discovery"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth - tokens are ISSUED by core-platform; discovery only verifies them.
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"

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

    def validate_required_settings(self) -> list[str]:
        """
        Validate required settings and return list of missing/invalid ones.
        """
        warnings = []
        
        if self.JWT_SECRET_KEY == "change-me-in-production":
            warnings.append("JWT_SECRET_KEY is using default value - change in production")
        
        return warnings


settings = DiscoverySettings()
