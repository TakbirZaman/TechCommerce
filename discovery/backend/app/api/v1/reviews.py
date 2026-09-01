"""
Review endpoints (Sections 13-17).

Reviews are public - anyone can read them.
Only authenticated users can create reviews (optional - can be removed for simplicity).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.rate_limiter import check_review_rate_limit, get_rate_limit_remaining
from app.models.review import Review, ReviewModerationLog, ReviewStatus
from app.models.stubs import Product
from app.schemas.review import RatingAggregate, ReviewCreate, ReviewModerationAction, ReviewOut
from app.services.rating_aggregation import get_rating_aggregate, invalidate_rating_aggregate
from app.services.verified_purchase import find_qualifying_order_id

router = APIRouter(tags=["reviews"])


class SimpleReviewCreate(BaseModel):
    """Simple review creation - no auth required."""
    rating: int
    title: str
    body: str
    pros: str | None = None
    cons: str | None = None
    # Optional user info for display
    reviewer_name: str = "Anonymous"


@router.post("/products/{product_id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    product_id: int,
    payload: SimpleReviewCreate,
    db: Session = Depends(get_db),
):
    # Rate limiting check (simple IP-based or in-memory)
    # For now, skip rate limiting for simplicity

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    review = Review(
        product_id=product_id,
        user_id=0,  # Guest user
        order_id=None,  # No verified purchase required
        rating=payload.rating,
        title=payload.title,
        body=payload.body,
        pros=payload.pros,
        cons=payload.cons,
        status=ReviewStatus.APPROVED,  # Auto-approve for simplicity
    )
    db.add(review)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Error submitting review")

    db.refresh(review)
    out = ReviewOut.model_validate(review)
    out.is_verified_purchase = False
    return out


@router.get("/products/{product_id}/reviews", response_model=list[ReviewOut])
def list_reviews(product_id: int, db: Session = Depends(get_db)):
    reviews = (
        db.query(Review)
        .filter(Review.product_id == product_id, Review.status == ReviewStatus.APPROVED)
        .order_by(Review.created_at.desc())
        .all()
    )
    out = []
    for r in reviews:
        item = ReviewOut.model_validate(r)
        item.is_verified_purchase = r.is_verified_purchase
        out.append(item)
    return out


@router.get("/products/{product_id}/rating", response_model=RatingAggregate)
async def get_rating(product_id: int, db: Session = Depends(get_db)):
    return await get_rating_aggregate(db, product_id)


@router.post("/admin/reviews/{review_id}/moderate", response_model=ReviewOut)
async def moderate_review(
    review_id: int,
    action: ReviewModerationAction,
    db: Session = Depends(get_db),
):
    """Admin: approve / reject / hide / restore (Section 15)."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")

    transitions = {
        "approve": ReviewStatus.APPROVED,
        "reject": ReviewStatus.REJECTED,
        "hide": ReviewStatus.HIDDEN,
        "restore": ReviewStatus.APPROVED,
    }
    review.status = transitions[action.action]
    db.add(ReviewModerationLog(review_id=review.id, admin_user_id=0, action=action.action, reason=action.reason))
    db.commit()
    db.refresh(review)

    await invalidate_rating_aggregate(review.product_id)

    out = ReviewOut.model_validate(review)
    out.is_verified_purchase = review.is_verified_purchase
    return out
