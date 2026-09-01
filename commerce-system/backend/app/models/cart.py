"""
Cart models (Branch 2, Section 4-5).

Design notes:
- One active Cart per user (created lazily on first add-to-cart).
- CartItem does NOT store price. Price is always re-fetched from
  Product.price at read/checkout time so it can never go stale/manipulated.
  (We *do* snapshot price onto OrderItem later, at order creation — see
  app/models/order.py — but never on the cart itself.)
- unique(user_id, product_id) prevents duplicate rows for the same product;
  adding an already-present product increments quantity instead.
"""
from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Cart(Base, TimestampMixin):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan", lazy="selectin"
    )


class CartItem(Base, TimestampMixin):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)

    cart: Mapped["Cart"] = relationship(back_populates="items")
