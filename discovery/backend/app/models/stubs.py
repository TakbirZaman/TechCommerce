"""
STUBS for models owned by feature/core-platform and feature/commerce.

IMPORTANT: Do not deploy these. In the real integration, delete this file
and replace every `from app.models.stubs import X` in the discovery module
with the real import, e.g.:

    from app.models.product import Product
    from app.models.brand import Brand
    from app.models.category import Category
    from app.models.user import User
    from app.commerce.models.order import Order, OrderItem

These stub definitions exist only so the discovery module's own models
(Review, PriceHistory, FeaturedProduct) can declare FKs and so this
scaffold is runnable/testable standalone. Column sets are the MINIMUM the
discovery module assumes exists on the real models — if the real models
already have equivalents (e.g. `status`, `is_active`), map to those instead
of adding duplicates.
"""
from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from app.core.config import settings

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def configure_engine(database_url: str | None = None):
    """
    Lazily creates/binds the engine. Kept lazy (rather than at import time)
    so this module can be imported for unit tests against SQLite without
    requiring the Postgres driver/connection to be available.
    """
    engine = create_engine(database_url or settings.DATABASE_URL, future=True)
    SessionLocal.configure(bind=engine)
    return engine


class ProductStatus(str, enum.Enum):
    COMING_SOON = "coming_soon"
    PRE_ORDER = "pre_order"
    AVAILABLE = "available"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(140), unique=True, nullable=False, index=True)
    logo_url = Column(String(500))
    description = Column(Text)


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(140), unique=True, nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    description = Column(Text)
    # Defines which spec keys are filterable for this category (Section 6).
    # e.g. {"cpu": {"type": "enum"}, "ram_gb": {"type": "numeric", "unit": "GB"}}
    filterable_spec_schema = Column(JSON, default=dict)

    parent = relationship("Category", remote_side=[id])


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(280), unique=True, nullable=False, index=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    price = Column(Float, nullable=False)
    status = Column(Enum(ProductStatus), default=ProductStatus.AVAILABLE, nullable=False)
    stock_quantity = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=True)
    popularity_score = Column(Float, default=0.0)  # e.g. views/purchases decayed over time
    # Structured specs, e.g. {"ram_gb": 16, "cpu": "Intel Core i7-13700H", "gpu": "RTX 5070"}
    specifications = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    brand = relationship("Brand")
    category = relationship("Category")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    is_admin = Column(Boolean, default=False)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(40), nullable=False)  # e.g. "delivered", "completed"


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
