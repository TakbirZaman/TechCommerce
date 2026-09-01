from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ReviewCreate(BaseModel):
    """
    Client-submitted payload. Deliberately has NO verified_purchase or
    order_id field — the backend derives that itself (Section 14).
    """

    rating: int = Field(ge=1, le=5)
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=5000)
    pros: Optional[str] = Field(default=None, max_length=1000)
    cons: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("title", "body")
    @classmethod
    def no_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class ReviewOut(BaseModel):
    id: int
    product_id: int
    user_id: int
    rating: int
    title: str
    body: str
    pros: Optional[str]
    cons: Optional[str]
    status: str
    is_verified_purchase: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewModerationAction(BaseModel):
    action: str = Field(pattern="^(approve|reject|hide|restore)$")
    reason: Optional[str] = None


class RatingAggregate(BaseModel):
    product_id: int
    average_rating: float
    review_count: int
    distribution: dict[int, int]  # {5: 120, 4: 40, 3: 10, 2: 3, 1: 1}
