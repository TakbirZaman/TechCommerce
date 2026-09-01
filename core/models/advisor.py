"""
AI Advisor Models

Tracks user interactions for recommendation engine.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class UserEvent(Base):
    """
    Tracks user interactions for ML/recommendation.
    
    Events: view, search, compare, wishlist, cart, purchase
    """
    __tablename__ = "user_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Types: view, search, compare, wishlist_add, wishlist_remove, cart_add, cart_remove, purchase
    
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    
    # Search/query data
    query: Mapped[str | None] = mapped_column(String(500), nullable=True)
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Result data
    result_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Metadata
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIRecommendation(Base):
    """Stores AI recommendations for tracking and improvement."""
    __tablename__ = "ai_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    
    # User query
    query: Mapped[str] = mapped_column(String(1000), nullable=False)
    extracted_requirements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Results
    recommended_product_ids: Mapped[dict] = mapped_column(JSON, nullable=False)
    scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Feedback (optional)
    clicked_product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purchased_product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
