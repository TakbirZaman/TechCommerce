from app.api.v1.price_history import record_price_change
from app.models.price_history import PriceHistory


def test_price_change_recorded(sample_data, db_session):
    product = sample_data["p1"]
    original_price = product.price

    record_price_change(db_session, product, new_price=1650.0, admin_id=1, reason="promotion")
    db_session.commit()

    assert product.price == 1650.0
    history = db_session.query(PriceHistory).filter(PriceHistory.product_id == product.id).all()
    assert len(history) == 1
    assert history[0].price == 1650.0
    assert history[0].change_reason == "promotion"
    assert original_price != product.price


def test_no_op_when_price_unchanged(sample_data, db_session):
    product = sample_data["p1"]
    record_price_change(db_session, product, new_price=product.price, admin_id=1)
    db_session.commit()
    history = db_session.query(PriceHistory).filter(PriceHistory.product_id == product.id).all()
    assert len(history) == 0


def test_lowest_highest_price_from_history(sample_data, db_session):
    product = sample_data["p1"]
    for price in [1700.0, 1500.0, 1900.0]:
        record_price_change(db_session, product, new_price=price, admin_id=1)
        db_session.commit()

    history = db_session.query(PriceHistory).filter(PriceHistory.product_id == product.id).all()
    prices = [h.price for h in history]
    assert min(prices) == 1500.0
    assert max(prices) == 1900.0
