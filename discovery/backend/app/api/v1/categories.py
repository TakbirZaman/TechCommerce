"""
GET /api/v1/categories/{slug} (Section 22).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.cache import cache_get_json, cache_set_json, k_category
from app.core.config import settings
from app.core.deps import get_db
from app.models.stubs import Brand, Category, Product
from app.schemas.product import CategoryBrief, ProductListItem

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/{slug}")
async def get_category_page(slug: str, db: Session = Depends(get_db)):
    cache_key = k_category(slug)
    cached_value = await cache_get_json(cache_key)
    if cached_value is not None:
        return cached_value

    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")

    subcategories = db.query(Category).filter(Category.parent_id == category.id).all()

    popular_brands = (
        db.query(Brand.name, Brand.slug, func.count(Product.id).label("cnt"))
        .join(Product, Product.brand_id == Brand.id)
        .filter(Product.category_id == category.id, Product.is_visible.is_(True))
        .group_by(Brand.name, Brand.slug)
        .order_by(func.count(Product.id).desc())
        .limit(10)
        .all()
    )

    products = (
        db.query(Product)
        .options(joinedload(Product.brand), joinedload(Product.category))
        .filter(Product.category_id == category.id, Product.is_visible.is_(True))
        .order_by(Product.popularity_score.desc())
        .limit(40)
        .all()
    )

    payload = {
        "category": CategoryBrief.model_validate(category).model_dump(),
        "description": category.description,
        "subcategories": [{"name": c.name, "slug": c.slug} for c in subcategories],
        "popular_brands": [{"name": n, "slug": s, "product_count": c} for n, s, c in popular_brands],
        "products": [ProductListItem.model_validate(p).model_dump() for p in products],
    }
    await cache_set_json(cache_key, payload, settings.CACHE_TTL_CATEGORY)
    return payload
