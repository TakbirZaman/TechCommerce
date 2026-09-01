"""
Review endpoints (Sections 13-17).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_admin_user, get_current_user_required, get_db
from app.core.rate_limiter import check_review_rate_limit, get_rate_limit_remaining
from app.models.review import Review, ReviewModerationLog, ReviewStatus
from app.models.stubs import Product
from app.schemas.review import RatingAggregate, ReviewCreate, ReviewModerationAction, ReviewOut
from app.services.rating_aggregation import get_rating_aggregate, invalidate_rating_aggregate
from app.services.verified_purchase import find_qualifying_order_id

router = APIRouter(tags=["reviews"])


@router.post("/products/{product_id}/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    product_id: int,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_required),
):
    # Rate limiting check (Section 17)
    if check_review_rate_limit(user.id):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Review rate limit exceeded. Maximum {5} reviews per hour."
        )

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    # Verified purchase is derived here, server-side ONLY. The client never
    # supplies this (Section 14) — ReviewCreate schema has no such field.
    order_id = find_qualifying_order_id(db, user.id, product_id)

    review = Review(
        product_id=product_id,
        user_id=user.id,
        order_id=order_id,
        rating=payload.rating,
        title=payload.title,
        body=payload.body,
        pros=payload.pros,
        cons=payload.cons,
        status=ReviewStatus.PENDING,
    )
    db.add(review)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Unique constraint (product_id, user_id) — duplicate-review guard (Section 17).
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already reviewed this product.")

    db.refresh(review)
    out = ReviewOut.model_validate(review)
    out.is_verified_purchase = review.is_verified_purchase
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


@router.get("/products/{product_id}/reviews/rate-limit")
def get_review_rate_limit(
    product_id: int,
    user: CurrentUser = Depends(get_current_user_required),
):
    """Check remaining reviews allowed for current user."""
    remaining = get_rate_limit_remaining(user.id)
    return {
        "remaining": remaining,
        "limit": 5,
        "window_seconds": 3600,
    }


@router.post("/admin/reviews/{review_id}/moderate", response_model=ReviewOut)
async def moderate_review(
    review_id: int,
    action: ReviewModerationAction,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
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
    db.add(ReviewModerationLog(review_id=review.id, admin_user_id=admin.id, action=action.action, reason=action.reason))
    db.commit()
    db.refresh(review)

    # Aggregate rating must reflect moderation immediately.
    await invalidate_rating_aggregate(review.product_id)

    out = ReviewOut.model_validate(review)
    out.is_verified_purchase = review.is_verified_purchase
    return out
