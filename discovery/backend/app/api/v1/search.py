"""
GET /api/v1/search (Section 3-4).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.deps import get_db
from app.models.stubs import Brand, Category, Product
from app.schemas.product import ProductListItem
from app.schemas.search import SearchResponse
from app.services.filter_engine import apply_filters_to_query
from app.services.ranking import RankingContext, get_ranking_strategy

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search_products(
    q: str = Query(..., min_length=1, description="Free text: name, brand, category, SKU, spec, description"),
    brand: Optional[list[str]] = Query(None),
    status: Optional[list[str]] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    sort: str = Query("relevance", pattern="^(relevance|price_asc|price_desc|newest|popularity|rating|discount)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.SEARCH_DEFAULT_PAGE_SIZE, ge=1, le=settings.SEARCH_MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    base_query = (
        db.query(Product)
        .options(joinedload(Product.brand), joinedload(Product.category))
        .join(Brand, Product.brand_id == Brand.id)
        .join(Category, Product.category_id == Category.id)
        .filter(Product.is_visible.is_(True))
        .filter(
            or_(
                Product.name.ilike(f"%{q}%"),
                Product.sku.ilike(f"%{q}%"),
                Product.description.ilike(f"%{q}%"),
                Brand.name.ilike(f"%{q}%"),
                Category.name.ilike(f"%{q}%"),
                # Matches against specification values, e.g. "16GB", "RTX 5070".
                Product.specifications.cast(str).ilike(f"%{q}%"),
            )
        )
    )

    filters = {
        "brand": brand,
        "status": status,
        "min_price": min_price,
        "max_price": max_price,
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    base_query = apply_filters_to_query(base_query, filters)

    strategy = get_ranking_strategy()
    ctx = RankingContext(query=q, query_tokens=q.lower().split())
    score = strategy.score_expression(ctx)

    sort_map = {
        "relevance": score.desc(),
        "price_asc": Product.price.asc(),
        "price_desc": Product.price.desc(),
        "newest": Product.created_at.desc(),
        "popularity": Product.popularity_score.desc(),
        "rating": Product.popularity_score.desc(),  # STUB: replace with joined rating_agg avg
        "discount": Product.price.asc(),  # STUB: requires a "compare_at_price" column from commerce
    }

    total = base_query.count()
    results = (
        base_query.order_by(sort_map[sort])
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return SearchResponse(
        query=q,
        total=total,
        page=page,
        page_size=page_size,
        results=[ProductListItem.model_validate(p) for p in results],
        applied_filters=filters,
        ranking_strategy=strategy.name if sort == "relevance" else f"sort:{sort}",
    )
