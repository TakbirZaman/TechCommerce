import pytest

from app.core.exceptions import InsufficientStockError
from app.services import inventory_service


def test_reserve_stock_increases_reserved(db_session, seed_product):
    inventory_service.reserve_stock(db_session, seed_product.id, 4)
    db_session.refresh(seed_product)
    assert seed_product.reserved_stock == 4
    assert seed_product.available_stock == 6


def test_reserve_stock_exceeding_available_raises(db_session, seed_product):
    with pytest.raises(InsufficientStockError):
        inventory_service.reserve_stock(db_session, seed_product.id, 11)


def test_release_stock_decreases_reserved(db_session, seed_product):
    inventory_service.reserve_stock(db_session, seed_product.id, 5)
    inventory_service.release_stock(db_session, seed_product.id, 5)
    db_session.refresh(seed_product)
    assert seed_product.reserved_stock == 0
    assert seed_product.available_stock == 10


def test_release_stock_never_goes_negative(db_session, seed_product):
    inventory_service.release_stock(db_session, seed_product.id, 5)
    db_session.refresh(seed_product)
    assert seed_product.reserved_stock == 0


def test_finalize_stock_reduces_total_and_reserved(db_session, seed_product):
    inventory_service.reserve_stock(db_session, seed_product.id, 3)
    inventory_service.finalize_stock(db_session, seed_product.id, 3)
    db_session.refresh(seed_product)
    assert seed_product.total_stock == 7
    assert seed_product.reserved_stock == 0
    assert seed_product.available_stock == 7  # unchanged by finalize itself


def test_reserve_then_release_then_reserve_again(db_session, seed_product):
    inventory_service.reserve_stock(db_session, seed_product.id, 10)
    db_session.refresh(seed_product)
    assert seed_product.available_stock == 0

    inventory_service.release_stock(db_session, seed_product.id, 10)
    db_session.refresh(seed_product)
    assert seed_product.available_stock == 10

    inventory_service.reserve_stock(db_session, seed_product.id, 6)
    db_session.refresh(seed_product)
    assert seed_product.available_stock == 4
