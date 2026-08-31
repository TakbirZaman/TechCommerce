"""
Admin discovery controls (Section 31): feature/unfeature, visibility,
review moderation is in reviews.py, price history inspection, category
metadata management (the filter schema from Section 6).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.cache import cache_delete, cache_delete_prefix, k_category, k_product_detail
from app.core.deps import CurrentUser, get_current_admin_user, get_db
from app.models.stubs import Category, Product

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/products/{product_id}/feature", status_code=status.HTTP_204_NO_CONTENT)
async def feature_product(product_id: int, db: Session = Depends(get_db), admin: CurrentUser = Depends(get_current_admin_user)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    product.is_featured = True
    db.commit()
    await cache_delete(k_product_detail(product_id))


@router.post("/products/{product_id}/unfeature", status_code=status.HTTP_204_NO_CONTENT)
async def unfeature_product(product_id: int, db: Session = Depends(get_db), admin: CurrentUser = Depends(get_current_admin_user)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    product.is_featured = False
    db.commit()
    await cache_delete(k_product_detail(product_id))


class VisibilityUpdate(BaseModel):
    is_visible: bool


@router.patch("/products/{product_id}/visibility", status_code=status.HTTP_204_NO_CONTENT)
async def set_product_visibility(
    product_id: int,
    payload: VisibilityUpdate,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    product.is_visible = payload.is_visible
    db.commit()
    # Category/brand pages list this product — evict the parent listing caches too.
    if product.category:
        await cache_delete(k_category(product.category.slug))
    await cache_delete(k_product_detail(product_id))


class CategoryMetadataUpdate(BaseModel):
    description: str | None = None
    filterable_spec_schema: dict | None = None


@router.patch("/categories/{slug}/metadata", status_code=status.HTTP_204_NO_CONTENT)
async def update_category_metadata(
    slug: str,
    payload: CategoryMetadataUpdate,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
):
    """
    Lets admins define which spec keys are filterable for a category
    (Section 6/31) without a code deploy.
    """
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")

    if payload.description is not None:
        category.description = payload.description
    if payload.filterable_spec_schema is not None:
        category.filterable_spec_schema = payload.filterable_spec_schema
    db.commit()
    await cache_delete_prefix(k_category(slug))
