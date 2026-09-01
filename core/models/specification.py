"""
Specification Engine Models

This is the foundation for:
- Comparison Engine
- PC Builder  
- AI Product Advisor

Instead of hardcoding specs into products, we use a flexible template system:

1. SpecificationTemplate - Defines what specs a category has
2. SpecificationOption - Predefined values for enum specs (e.g., CPU models)
3. ProductSpecification - Actual spec values for each product
"""
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class SpecType(str):
    """Specification data types."""
    TEXT = "text"          # Free text (e.g., "Intel Core i7-13700H")
    NUMBER = "number"      # Numeric value (e.g., 16 for RAM)
    ENUM = "enum"          # Predefined options (e.g., "RTX 4060")
    BOOLEAN = "boolean"    # Yes/No (e.g., "Touchscreen")
    RANGE = "range"        # Min-Max (e.g., "8-16 hours battery")


class SpecificationTemplate(Base):
    """
    Defines what specifications a category has.
    
    Example for Laptops:
    - cpu: enum (predefined CPU options)
    - ram_gb: number (8, 16, 32, 64)
    - storage_type: enum (SSD, HDD)
    - storage_gb: number
    - gpu: enum (predefined GPU options)
    - screen_size: number (inches)
    - battery_wh: number
    - weight_kg: float
    """
    __tablename__ = "specification_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), unique=True, nullable=False)
    
    # JSON structure defining all specs for this category
    # Format: {
    #   "spec_key": {
    #     "name": "Display Name",
    #     "type": "enum|number|text|boolean|range",
    #     "unit": "GB" or null,
    #     "required": true/false,
    #     "filterable": true/false,
    #     "comparable": true/false,
    #     "options_key": "cpu_options" (for enum type)
    #   }
    # }
    template: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category: Mapped["Category"] = relationship("Category", back_populates="specification_template")
    options: Mapped[list["SpecificationOption"]] = relationship(back_populates="template", cascade="all, delete-orphan")


class SpecificationOption(Base):
    """
    Predefined values for enum-type specifications.
    
    Example for CPU:
    - AMD Ryzen 5 7600X
    - AMD Ryzen 7 7800X3D
    - Intel Core i5-13600K
    - Intel Core i7-13700H
    """
    __tablename__ = "specification_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("specification_templates.id"), index=True)
    spec_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # e.g., "cpu", "gpu"
    value: Mapped[str] = mapped_column(String(200), nullable=False)  # e.g., "AMD Ryzen 7 7800X3D"
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)  # For UI
    sort_order: Mapped[int] = mapped_column(Integer, default=0)  # For ordering in dropdowns
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Additional data for the option (TDP, benchmarks, etc.)
    extra_data: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    template: Mapped["SpecificationTemplate"] = relationship(back_populates="options")


class Product(Base):
    """
    Product model with proper specification support.
    """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(280), unique=True, nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    
    # Pricing
    price: Mapped[float] = mapped_column(Float, nullable=False)
    compare_at_price: Mapped[float | None] = mapped_column(Float, nullable=True)  # Original price for discounts
    
    # Inventory
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    reserved_stock: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # SEO
    meta_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Popularity (for sorting/ranking)
    popularity_score: Mapped[float] = mapped_column(Float, default=0.0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    brand: Mapped["Brand"] = relationship(back_populates="products")
    category: Mapped["Category"] = relationship(back_populates="products")
    images: Mapped[list["ProductImage"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    specifications: Mapped[list["ProductSpecification"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    reviews: Mapped[list["ProductReview"]] = relationship(back_populates="product", cascade="all, delete-orphan")

    @property
    def available_stock(self) -> int:
        return max(self.stock_quantity - self.reserved_stock, 0)

    @property
    def is_in_stock(self) -> bool:
        return self.available_stock > 0

    def get_spec_value(self, spec_key: str) -> Any:
        """Get a specific specification value."""
        for spec in self.specifications:
            if spec.spec_key == spec_key:
                return spec.value
        return None

    def get_all_specs(self) -> dict[str, Any]:
        """Get all specifications as a dictionary."""
        return {spec.spec_key: spec.value for spec in self.specifications}


class ProductImage(Base):
    """Product images with ordering."""
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="images")


class ProductSpecification(Base):
    """
    Actual specification values for a product.
    
    This links a product to its specification values.
    Values are stored as strings and converted based on spec type.
    """
    __tablename__ = "product_specifications"
    __table_args__ = {"schema": None}

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    spec_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Value stored as string - type conversion happens in application layer
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # For numeric specs, store numeric value for filtering/sorting
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="specifications")


class ProductReview(Base):
    """Product reviews and ratings."""
    __tablename__ = "product_reviews"
    __table_args__ = {"schema": None}

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    reviewer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="reviews")
