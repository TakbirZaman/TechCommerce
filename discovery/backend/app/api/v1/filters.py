"""
GET /api/v1/categories/{slug}/filters (Section 6).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.stubs import Category, Product
from app.schemas.filters import CategoryFiltersResponse
from app.services.filter_engine import build_common_filters, build_spec_filters

router = APIRouter(prefix="/categories", tags=["filters"])


@router.get("/{slug}/filters", response_model=CategoryFiltersResponse)
def get_category_filters(slug: str, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")

    base_query = db.query(Product).filter(Product.category_id == category.id, Product.is_visible.is_(True))

    filters = build_common_filters(db, base_query) + build_spec_filters(db, category, base_query)
    return CategoryFiltersResponse(category_slug=slug, filters=filters)
