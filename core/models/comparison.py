"""
Comparison Engine Models

Allows users to compare products side-by-side.
Only works within the same category (laptop vs laptop, phone vs phone).
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Comparison(Base):
    """A comparison session - stores which products are being compared."""
    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["ComparisonItem"]] = relationship(back_populates="comparison", cascade="all, delete-orphan")


class ComparisonItem(Base):
    """Individual product in a comparison."""
    __tablename__ = "comparison_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    comparison_id: Mapped[int] = mapped_column(ForeignKey("comparisons.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    comparison: Mapped["Comparison"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship("Product")


# Maximum products that can be compared at once
MAX_COMPARISON_ITEMS = 4
