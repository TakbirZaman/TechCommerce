"""
Core data contracts for the intelligence system.

These schemas are the boundary between layers:
- UserRequirement: what the requirement-extraction layer must produce
  (whether from a form, a follow-up flow, or an LLM — see ml/inference/llm_validation.py
  in a later stage).
- Product: the minimal shape the recommender needs from the product-catalog DB.
  This is NOT the full product schema owned by the core platform — it's a read
  projection. The intelligence system never writes to or redefines the product schema.
- ScoredProduct / RecommendationResponse: what the API returns.

Validation lives here so that no invalid structure (e.g. from a malformed LLM
extraction) can reach the filtering/ranking pipeline.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class Category(str, Enum):
    LAPTOP = "laptop"
    SMARTPHONE = "smartphone"
    MONITOR = "monitor"


class UseCase(str, Enum):
    PROGRAMMING = "programming"
    MACHINE_LEARNING = "machine_learning"
    GAMING = "gaming"
    VIDEO_EDITING = "video_editing"
    UNIVERSITY = "university"
    BUSINESS = "business"
    GENERAL = "general"
    PHOTOGRAPHY = "photography"


class Priorities(BaseModel):
    """
    Weights in [0, 1] indicating how much the user cares about each dimension.
    All fields optional — missing priorities are filled in later from
    use-case defaults (ml/features/weights.py), never left as an implicit 0.
    """

    performance: float | None = Field(default=None, ge=0, le=1)
    cpu: float | None = Field(default=None, ge=0, le=1)
    gpu: float | None = Field(default=None, ge=0, le=1)
    ram: float | None = Field(default=None, ge=0, le=1)
    storage: float | None = Field(default=None, ge=0, le=1)
    battery: float | None = Field(default=None, ge=0, le=1)
    weight: float | None = Field(default=None, ge=0, le=1)
    display: float | None = Field(default=None, ge=0, le=1)
    camera: float | None = Field(default=None, ge=0, le=1)
    price: float | None = Field(default=None, ge=0, le=1)

    model_config = {"extra": "forbid"}


class RequiredSpecs(BaseModel):
    """
    Hard constraints. A product violating any of these is filtered out
    entirely — it is never ranked, regardless of how well it scores otherwise.
    """

    min_ram_gb: float | None = Field(default=None, gt=0)
    min_storage_gb: float | None = Field(default=None, gt=0)
    min_battery_mah: float | None = Field(default=None, gt=0)
    max_weight_kg: float | None = Field(default=None, gt=0)
    required_brand: str | None = None
    in_stock_only: bool = True

    model_config = {"extra": "forbid"}


class UserRequirement(BaseModel):
    category: Category
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, gt=0)
    use_cases: list[UseCase] = Field(default_factory=list)
    priorities: Priorities = Field(default_factory=Priorities)
    required_specs: RequiredSpecs = Field(default_factory=RequiredSpecs)
    preferred_brands: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _validate_budget_range(self) -> "UserRequirement":
        if (
            self.budget_min is not None
            and self.budget_max is not None
            and self.budget_min > self.budget_max
        ):
            raise ValueError("budget_min cannot exceed budget_max")
        return self


class Product(BaseModel):
    """
    Read projection of a product, as consumed by the recommender.
    Raw specification fields (raw_specs) preserve whatever the catalog
    stored (e.g. "16GB", "16384MB") — normalization happens in
    ml/preprocessing/normalization.py, never by inventing values here.
    """

    product_id: str
    name: str
    brand: str
    category: Category
    price: float = Field(gt=0)
    in_stock: bool = True
    rating: float | None = Field(default=None, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)
    raw_specs: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}

    @field_validator("price")
    @classmethod
    def _price_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price must be positive")
        return v


class ScoredProduct(BaseModel):
    product_id: str
    score: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    component_scores: dict[str, float] = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    requirement: UserRequirement
    recommendations: list[ScoredProduct]
    candidates_considered: int
    candidates_after_filtering: int
    engine: str = "rule_based_v1"
