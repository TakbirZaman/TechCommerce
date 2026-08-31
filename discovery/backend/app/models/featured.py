"""
Admin discovery controls state (Section 31) beyond what's already on Product
(is_featured, is_visible live on Product itself — see models/stubs.py).
This file exists for future admin-only discovery metadata (e.g. homepage
section curation overrides) without overloading the core Product model.
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, func

from app.models.stubs import Base


class HomepageSectionOverride(Base):
    """
    Lets admins pin/exclude specific products in a homepage section
    (Section 23) without hard-coding product IDs into frontend code.
    """

    __tablename__ = "homepage_section_overrides"

    id = Column(Integer, primary_key=True)
    section_key = Column(String(60), nullable=False, index=True)  # e.g. "trending", "deals"
    product_id = Column(Integer, nullable=False)
    action = Column(String(10), nullable=False)  # "pin" | "exclude"
    position = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
