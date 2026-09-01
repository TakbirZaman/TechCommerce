"""
Central application configuration.

All secrets/config are pulled from environment variables (see .env.example).
Nothing here should ever hardcode gateway credentials.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Auth - tokens are ISSUED by core-platform; commerce only verifies them.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # Storage
    STORAGE_PROVIDER: str = "s3"
    STORAGE_BUCKET: str
    STORAGE_REGION: str = "ap-southeast-1"
    STORAGE_ENDPOINT_URL: str | None = None
    STORAGE_ACCESS_KEY_ID: str | None = None
    STORAGE_SECRET_ACCESS_KEY: str | None = None
    STORAGE_PUBLIC_BASE_URL: str | None = None

    # bKash
    BKASH_BASE_URL: str = ""
    BKASH_APP_KEY: str = ""
    BKASH_APP_SECRET: str = ""
    BKASH_USERNAME: str = ""
    BKASH_PASSWORD: str = ""
    BKASH_CALLBACK_URL: str = ""

    # Nagad
    NAGAD_BASE_URL: str = ""
    NAGAD_MERCHANT_ID: str = ""
    NAGAD_MERCHANT_NUMBER: str = ""
    NAGAD_PUBLIC_KEY: str = ""
    NAGAD_PRIVATE_KEY: str = ""
    NAGAD_CALLBACK_URL: str = ""

    # SSLCommerz
    SSLCOMMERZ_STORE_ID: str = ""
    SSLCOMMERZ_STORE_PASSWORD: str = ""
    SSLCOMMERZ_IS_SANDBOX: bool = True
    SSLCOMMERZ_SUCCESS_URL: str = ""
    SSLCOMMERZ_FAIL_URL: str = ""
    SSLCOMMERZ_CANCEL_URL: str = ""
    SSLCOMMERZ_IPN_URL: str = ""

    FRONTEND_BASE_URL: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
