from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PriceHistoryPoint(BaseModel):
    price: float
    recorded_at: datetime
    change_reason: str | None = None


class PriceHistoryResponse(BaseModel):
    product_id: int
    current_price: float
    previous_price: float | None
    lowest_price: float | None
    highest_price: float | None
    history: list[PriceHistoryPoint]
