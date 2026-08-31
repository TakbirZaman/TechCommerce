"""
Review domain models — owned by the discovery module (Sections 13-17).
"""
from __future__ import annotations

import enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.models.stubs import Base


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    HIDDEN = "hidden"


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
        # One review per user per product — prevents duplicate-review spam (Section 17).
        UniqueConstraint("product_id", "user_id", name="uq_review_product_user"),
    )

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Nullable: only set when the backend independently verifies a qualifying
    # purchase (Section 14). Never trust a client-supplied flag for this.
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    rating = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    pros = Column(Text, nullable=True)
    cons = Column(Text, nullable=True)

    status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product")
    user = relationship("User")
    order = relationship("Order")

    @property
    def is_verified_purchase(self) -> bool:
        return self.order_id is not None


class ReviewModerationLog(Base):
    """Audit trail for Section 15 — who moderated what, and when."""

    __tablename__ = "review_moderation_logs"
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(20), nullable=False)  # approve|reject|hide|restore
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
