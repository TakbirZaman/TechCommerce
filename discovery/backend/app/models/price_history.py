"""
Price history model (Section 18). Admin-write-only, append-only ledger.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.models.stubs import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    # e.g. "admin_update", "promotion", "restock_repricing"
    change_reason = Column(String(80), nullable=True)
    changed_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    product = relationship("Product")

    # No update/delete endpoints are exposed anywhere in the API layer —
    # this table is intentionally append-only from the customer's perspective.
