"""
Price history endpoints (Sections 18-19).

Writing a price-history row happens as a side effect of the ADMIN product
price-update endpoint, not here. This module exposes:
  - the read-only history for the frontend chart
  - the write hook the admin product-edit flow should call

STUB NOTE: the actual "update product price" endpoint lives in
feature/commerce's admin product router. Integration point: call
`record_price_change()` from there inside the same DB transaction
whenever `Product.price` changes, instead of duplicating admin product
CRUD here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.cache import cache_delete, k_product_detail
from app.core.deps import CurrentUser, get_current_admin_user, get_db
from app.models.price_history import PriceHistory
from app.models.stubs import Product
from app.schemas.price_history import PriceHistoryPoint, PriceHistoryResponse

router = APIRouter(tags=["price-history"])


def record_price_change(db: Session, product: Product, new_price: float, admin_id: int, reason: str = "admin_update") -> None:
    """
    Call this from the admin product-update flow whenever price changes.
    Intentionally has no HTTP-facing "customer edits price history" path —
    only ever invoked from trusted admin write paths (Section 18).
    """
    if new_price == product.price:
        return
    db.add(
        PriceHistory(
            product_id=product.id,
            price=new_price,
            change_reason=reason,
            changed_by_admin_id=admin_id,
        )
    )
    product.price = new_price
    db.add(product)


@router.get("/products/{product_id}/price-history", response_model=PriceHistoryResponse)
async def get_price_history(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    history = (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.recorded_at.asc())
        .all()
    )

    prices = [h.price for h in history] or [product.price]
    previous_price = history[-2].price if len(history) >= 2 else None

    return PriceHistoryResponse(
        product_id=product_id,
        current_price=product.price,
        previous_price=previous_price,
        lowest_price=min(prices),
        highest_price=max(prices),
        history=[
            PriceHistoryPoint(price=h.price, recorded_at=h.recorded_at, change_reason=h.change_reason)
            for h in history
        ],
    )


@router.post("/admin/products/{product_id}/price", status_code=status.HTTP_204_NO_CONTENT)
async def admin_update_price(
    product_id: int,
    new_price: float,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
):
    """
    Thin illustrative endpoint. In the real integration this logic is
    invoked from within feature/commerce's existing product-update
    endpoint rather than a separate one, to avoid two sources of truth
    for "what changed a product's price."
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    record_price_change(db, product, new_price, admin.id)
    db.commit()
    await cache_delete(k_product_detail(product_id))
