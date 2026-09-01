"""
POST /api/v1/compare (Sections 9-11).

POST (not GET) because product_ids can exceed a comfortable query-string
length and because this is a computed view, not a resource fetch by id.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db
from app.models.stubs import Product
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison import build_comparison

router = APIRouter(prefix="/compare", tags=["comparison"])


@router.post("", response_model=ComparisonResponse)
def compare_products(payload: ComparisonRequest, db: Session = Depends(get_db)):
    products = (
        db.query(Product)
        .options(joinedload(Product.brand), joinedload(Product.category))
        .filter(Product.id.in_(payload.product_ids), Product.is_visible.is_(True))
        .all()
    )

    found_ids = {p.id for p in products}
    missing = set(payload.product_ids) - found_ids
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product(s) not found: {sorted(missing)}")

    # Preserve the order the client requested for stable column ordering.
    order_index = {pid: i for i, pid in enumerate(payload.product_ids)}
    products.sort(key=lambda p: order_index[p.id])

    return build_comparison(products)
