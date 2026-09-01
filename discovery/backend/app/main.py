"""
Discovery module FastAPI app.

STUB NOTE: In the real monorepo, `include_router` calls below should be
added to core-platform's existing FastAPI `app` instance instead of
standing up a second app — this file is runnable standalone for local
development/testing only.
"""
from fastapi import FastAPI

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

app = FastAPI(title="Discovery Module", version="1.0.0")

API_PREFIX = "/api/v1"

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


@app.get("/health")
def health():
    return {"status": "ok"}
