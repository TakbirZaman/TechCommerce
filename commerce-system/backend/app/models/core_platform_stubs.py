"""
STUB MODELS — REPLACE WHEN feature/core-platform LANDS.

feature/core-platform does not exist yet in this codebase. The commerce
system needs to reference Users, Products, Categories, and Brands (foreign
keys, price/stock lookups, etc.), so this file defines the MINIMUM shape
those tables must have for commerce to function correctly.

Rules for whoever integrates the real core-platform branch:
  1. Delete this file.
  2. Point every `from app.models.core_platform_stubs import X` in the
     commerce codebase to the real core-platform model instead.
  3. Confirm column names/types line up (especially Product.price,
     Product.is_active, and the inventory columns below) or update the
     commerce services that read them.

Do NOT extend business logic in this file — it exists only so commerce
has something concrete to compile/test against.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """Minimal shape of core-platform's User table."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="customer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))


class Product(Base):
    """
    Minimal shape of core-platform's Product table, including the
    inventory foundation fields commerce relies on for reservation logic
    (see app/services/inventory_service.py).
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)

    # Authoritative price. Commerce must NEVER trust a client-supplied price
    # and must always re-read this column at cart/checkout/order time.
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_purchasable: Mapped[bool] = mapped_column(Boolean, default=True)

    # --- Inventory foundation (owned by core-platform per spec, section 10) ---
    total_stock: Mapped[int] = mapped_column(default=0)
    reserved_stock: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def available_stock(self) -> int:
        return max(self.total_stock - self.reserved_stock, 0)

    brand: Mapped["Brand"] = relationship(viewonly=True)
    category: Mapped["Category"] = relationship(viewonly=True)
