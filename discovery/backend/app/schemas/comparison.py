from __future__ import annotations

from pydantic import BaseModel

from app.schemas.product import BrandBrief, CategoryBrief


class ComparisonRequest(BaseModel):
    product_ids: list[int]


class ComparisonRow(BaseModel):
    spec_key: str
    spec_label: str
    values: list[str]  # one per product, aligned by index
    differs: bool


class ComparisonProductColumn(BaseModel):
    id: int
    name: str
    slug: str
    price: float
    status: str
    brand: BrandBrief
    thumbnail_url: str | None = None


class ComparisonResponse(BaseModel):
    category: CategoryBrief
    products: list[ComparisonProductColumn]
    rows: list[ComparisonRow]
