"""
GET /api/v1/search/autocomplete (Section 5).

Server-side: cached by prefix, capped result count. Debouncing itself is a
frontend concern (see frontend/hooks/useDebounce.ts) — this endpoint just
needs to be cheap enough to call frequently and cache well.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.core.cache import cached, k_autocomplete
from app.core.config import settings
from app.core.deps import get_db
from app.models.stubs import Brand, Category, Product
from app.schemas.search import AutocompleteResponse, AutocompleteSuggestion

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(
    q: str = Query(..., min_length=2, max_length=60),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    async def load() -> list[dict]:
        prefix = f"{q}%"
        suggestions: list[dict] = []

        brands = db.query(Brand.name, Brand.slug).filter(Brand.name.ilike(prefix)).limit(limit).all()
        suggestions += [{"label": name, "type": "brand", "slug": slug} for name, slug in brands]

        categories = (
            db.query(Category.name, Category.slug).filter(Category.name.ilike(prefix)).limit(limit).all()
        )
        suggestions += [{"label": name, "type": "category", "slug": slug} for name, slug in categories]

        products = (
            db.query(distinct(Product.name), Product.slug)
            .filter(Product.name.ilike(prefix), Product.is_visible.is_(True))
            .limit(limit)
            .all()
        )
        suggestions += [{"label": name, "type": "product", "slug": slug} for name, slug in products]

        return suggestions[:limit]

    raw = await cached(k_autocomplete(q), settings.CACHE_TTL_AUTOCOMPLETE, load)
    return AutocompleteResponse(query=q, suggestions=[AutocompleteSuggestion(**s) for s in raw])
