"""
Shared model definitions for the discovery module.

These models map to the same PostgreSQL tables used by core-platform and
commerce. Column sets are the MINIMUM the discovery module assumes exists
on the real models. If the real models already have equivalents, map to
those instead of adding duplicates.

When the real core-platform models are available, delete this file and
replace imports with:
    from app.models.product import Product
    from app.models.brand import Brand
    from app.models.category import Category
    from app.models.user import User
    from app.models.order import Order, OrderItem
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
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    products = relationship("Product", back_populates="brand")


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(140), unique=True, nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    description = Column(Text)
    filterable_spec_schema = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    parent = relationship("Category", remote_side=[id])
    products = relationship("Product", back_populates="category")


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
    reserved_stock = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    is_purchasable = Column(Boolean, default=True)
    popularity_score = Column(Float, default=0.0)
    specifications = Column(JSON, default=dict)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    brand = relationship("Brand", back_populates="products")
    category = relationship("Category", back_populates="products")

    @property
    def available_stock(self) -> int:
        return max(self.stock_quantity - self.reserved_stock, 0)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(32), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    role = Column(String(32), default="customer")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_number = Column(String(32), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(40), nullable=False)
    subtotal = Column(Float, nullable=False)
    discount = Column(Float, default=0.0)
    delivery_charge = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class Wishlist(Base):
    __tablename__ = "wishlists"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    product = relationship("Product")

    __table_args__ = (
        {"schema": None},
    )


class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    discount_percent = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    min_order_amount = Column(Float, default=0.0)
    max_uses = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DeliveryZone(Base):
    __tablename__ = "delivery_zones"
    id = Column(Integer, primary_key=True)
    city = Column(String(120), nullable=False, index=True)
    area = Column(String(120), nullable=True)
    charge = Column(Float, nullable=False)
    estimated_days = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
