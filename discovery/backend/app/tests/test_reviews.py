import pytest
from sqlalchemy.exc import IntegrityError

from app.models.review import Review, ReviewStatus
from app.schemas.review import ReviewCreate


def test_review_create_schema_has_no_verified_purchase_field():
    """Section 14: client payload must not be able to set verified purchase."""
    fields = ReviewCreate.model_fields.keys()
    assert "verified_purchase" not in fields
    assert "order_id" not in fields


def test_review_defaults_to_pending(sample_data, db_session):
    review = Review(
        product_id=sample_data["p1"].id,
        user_id=sample_data["user"].id,
        rating=5,
        title="Great laptop",
        body="Really happy with the performance and build quality.",
    )
    db_session.add(review)
    db_session.commit()
    assert review.status == ReviewStatus.PENDING
    assert review.is_verified_purchase is False


def test_duplicate_review_same_user_product_rejected(sample_data, db_session):
    r1 = Review(product_id=sample_data["p1"].id, user_id=sample_data["user"].id,
                rating=4, title="Good", body="Solid overall performance for the price.")
    db_session.add(r1)
    db_session.commit()

    r2 = Review(product_id=sample_data["p1"].id, user_id=sample_data["user"].id,
                rating=2, title="Meh", body="Changed my mind after a week of use.")
    db_session.add(r2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_order_id_set_marks_verified(sample_data, db_session):
    review = Review(
        product_id=sample_data["p1"].id, user_id=sample_data["user"].id,
        order_id=999, rating=5, title="Verified", body="Bought it and it works great overall.",
    )
    db_session.add(review)
    db_session.commit()
    assert review.is_verified_purchase is True
