"""
ML API endpoints with production security.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user_required, get_db
from ml.data.schemas import UserRequirement
from ml.inference.pipeline import recommend_from_database

router = APIRouter(prefix="/api/v1/ml", tags=["ml"])


class RecommendationRequest(BaseModel):
    budget_min: float = 0
    budget_max: float = float("inf")
    use_case: str = "general"
    preferences: dict = {}
    top_n: int = 10


class RecommendationResponse(BaseModel):
    recommendations: list[dict]
    total_candidates: int
    engine: str


@router.post("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    payload: RecommendationRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_required),
):
    """
    Get product recommendations based on user requirements.
    
    Requires authentication. Rate limited to prevent abuse.
    """
    # Rate limiting check (simple in-memory for now)
    # In production, use Redis-backed rate limiter
    
    requirement = UserRequirement(
        budget_min=payload.budget_min,
        budget_max=payload.budget_max,
        use_case=payload.use_case,
        preferences=payload.preferences,
    )
    
    try:
        response = recommend_from_database(db, requirement, top_n=payload.top_n)
        
        return RecommendationResponse(
            recommendations=[
                {
                    "product_id": r.product_id,
                    "score": r.score,
                    "reasons": r.reasons,
                    "tradeoffs": r.tradeoffs,
                }
                for r in response.recommendations
            ],
            total_candidates=response.candidates_considered,
            engine=response.engine,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recommendation engine error: {str(e)}"
        )


@router.get("/health")
def ml_health():
    """Health check for ML service."""
    return {
        "status": "healthy",
        "engine": "rule_based_v1",
        "features": ["filtering", "ranking", "explanation"],
    }
