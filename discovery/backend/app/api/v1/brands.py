"""
GET /api/v1/brands/{slug} (Section 21).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.cache import cache_get_json, cache_set_json, k_brand
from app.core.config import settings
from app.core.deps import get_db
from app.models.stubs import Brand, Category, Product
from app.schemas.product import BrandBrief, ProductListItem

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("/{slug}")
async def get_brand_page(slug: str, db: Session = Depends(get_db)):
    cache_key = k_brand(slug)
    cached_value = await cache_get_json(cache_key)
    if cached_value is not None:
        return cached_value

    brand = db.query(Brand).filter(Brand.slug == slug).first()
    if not brand:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")

    products_q = (
        db.query(Product)
        .options(joinedload(Product.brand), joinedload(Product.category))
        .filter(Product.brand_id == brand.id, Product.is_visible.is_(True))
    )

    categories = (
        db.query(Category)
        .join(Product, Product.category_id == Category.id)
        .filter(Product.brand_id == brand.id)
        .distinct()
        .all()
    )

    popular_products = products_q.order_by(Product.popularity_score.desc()).limit(8).all()
    all_products = products_q.order_by(Product.name.asc()).limit(60).all()

    payload = {
        "brand": BrandBrief.model_validate(brand).model_dump(),
        "description": brand.description,
        "categories": [{"name": c.name, "slug": c.slug} for c in categories],
        "popular_products": [ProductListItem.model_validate(p).model_dump() for p in popular_products],
        "products": [ProductListItem.model_validate(p).model_dump() for p in all_products],
    }
    await cache_set_json(cache_key, payload, settings.CACHE_TTL_BRAND)
    return payload
