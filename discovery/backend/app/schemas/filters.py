from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel


class FilterOption(BaseModel):
    value: Any
    label: str
    count: int  # number of matching results if this option were applied


class FilterDefinition(BaseModel):
    key: str  # e.g. "ram_gb", "brand_id", "price"
    label: str  # e.g. "RAM"
    type: Literal["enum", "range", "boolean"]
    unit: Optional[str] = None
    options: list[FilterOption] = []
    min: Optional[float] = None
    max: Optional[float] = None


class CategoryFiltersResponse(BaseModel):
    category_slug: str
    filters: list[FilterDefinition]
