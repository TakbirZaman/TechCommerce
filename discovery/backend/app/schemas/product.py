"""
Product DTOs — deliberately split (Section 26) so list endpoints never
pay for/ship full specification blobs and detail endpoints don't get
truncated.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class BrandBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    logo_url: Optional[str] = None


class CategoryBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str


class ProductListItem(BaseModel):
    """Minimal shape for search results, category grids, related-product rails."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    sku: str
    price: float
    status: str
    brand: BrandBrief
    category: CategoryBrief
    thumbnail_url: Optional[str] = None
    average_rating: Optional[float] = None
    review_count: int = 0
    # Only the handful of specs relevant for card display (e.g. RAM/storage
    # chips), not the full specifications blob.
    highlight_specs: dict[str, Any] = {}


class ProductDetail(BaseModel):
    """Full shape for the product detail page (Section 12)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    sku: str
    description: Optional[str] = None
    price: float
    status: str
    stock_quantity: int
    brand: BrandBrief
    category: CategoryBrief
    specifications: dict[str, Any] = {}
    average_rating: Optional[float] = None
    review_count: int = 0
    rating_distribution: dict[int, int] = {}
    created_at: datetime
    updated_at: datetime
