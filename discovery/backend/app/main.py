"""
Discovery module FastAPI app.

Can run standalone for local development/testing, or mount routers
on the core-platform's existing FastAPI app instance.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    admin_discovery,
    autocomplete,
    brands,
    categories,
    comparison,
    filters,
    price_history,
    related,
    reviews,
    search,
)
from app.api.v1 import wishlist as wishlist_router
from app.api.v1 import homepage as homepage_router
from app.core.config import settings
from app.models.base import Base, engine

# Create all tables (for development only - use Alembic in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Discovery Module", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

# Mount all routers
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(autocomplete.router, prefix=API_PREFIX)
app.include_router(filters.router, prefix=API_PREFIX)
app.include_router(comparison.router, prefix=API_PREFIX)
app.include_router(reviews.router, prefix=API_PREFIX)
app.include_router(price_history.router, prefix=API_PREFIX)
app.include_router(related.router, prefix=API_PREFIX)
app.include_router(brands.router, prefix=API_PREFIX)
app.include_router(categories.router, prefix=API_PREFIX)
app.include_router(admin_discovery.router, prefix=API_PREFIX)
app.include_router(wishlist_router.router, prefix=API_PREFIX)
app.include_router(homepage_router.router, prefix=API_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok"}


def mount_on_main_app(main_app: FastAPI):
    """
    Mount discovery routers on an existing FastAPI app (core-platform).
    Use this when integrating into the monorepo.
    """
    main_app.include_router(search.router, prefix=API_PREFIX, tags=["discovery"])
    main_app.include_router(autocomplete.router, prefix=API_PREFIX, tags=["discovery"])
    main_app.include_router(filters.router, prefix=API_PREFIX, tags=["discovery"])
    main_app.include_router(comparison.router, prefix=API_PREFIX, tags=["discovery"])
    main_app.include_router(reviews.router, prefix=API_PREFIX, tags=["discovery"])
    main_app.include_router(price_history.router, prefix=API_PREFIX, tags=["discovery"])
    main_app.include_router(related.router, prefix=API_PREFIX, tags=["discovery"])
    main_app.include_router(brands.router, prefix=API_PREFIX, tags=["discovery"])
    main_app.include_router(categories.router, prefix=API_PREFIX, tags=["discovery"])
    main_app.include_router(admin_discovery.router, prefix=API_PREFIX, tags=["discovery"])
    main_app.include_router(wishlist_router.router, prefix=API_PREFIX, tags=["discovery"])
    main_app.include_router(homepage_router.router, prefix=API_PREFIX, tags=["discovery"])
