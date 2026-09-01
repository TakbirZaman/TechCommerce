"""
GET /api/v1/products/{id}/related (Section 20).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db
from app.models.stubs import Product
from app.schemas.product import ProductListItem
from app.services.related_products import get_related_products_strategy

router = APIRouter(tags=["related"])


@router.get("/products/{product_id}/related", response_model=list[ProductListItem])
def get_related(product_id: int, limit: int = 8, db: Session = Depends(get_db)):
    product = (
        db.query(Product)
        .options(joinedload(Product.brand), joinedload(Product.category))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    strategy = get_related_products_strategy()
    related = strategy.get_related(db, product, limit=limit)
    return [ProductListItem.model_validate(p) for p in related]
