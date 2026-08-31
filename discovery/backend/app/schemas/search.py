from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.schemas.product import ProductListItem


class SearchResponse(BaseModel):
    query: str
    total: int
    page: int
    page_size: int
    results: list[ProductListItem]
    applied_filters: dict = {}
    ranking_strategy: str  # exposed for debuggability / future A-B testing


class AutocompleteSuggestion(BaseModel):
    label: str
    type: str  # "product" | "brand" | "category"
    slug: Optional[str] = None


class AutocompleteResponse(BaseModel):
    query: str
    suggestions: list[AutocompleteSuggestion]
