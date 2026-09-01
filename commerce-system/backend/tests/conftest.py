"""
Test fixtures.

Uses an in-memory SQLite DB for speed. Note: SQLite does not enforce real
row-level locking the way Postgres does with SELECT ... FOR UPDATE — the
`.with_for_update()` calls in cart_service/inventory_service are no-ops
here. These tests validate business logic correctness, not concurrency;
true race-condition behavior should be verified against Postgres in CI
(see tests/test_concurrency.py once the inventory/order system lands).
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.models.core_platform_stubs import Product
from app.models.core_platform_stubs import User as CorePlatformUser


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seed_product(db_session):
    product = Product(
        sku="SKU-001",
        name="Test Widget",
        slug="test-widget",
        price=Decimal("100.00"),
        is_active=True,
        is_purchasable=True,
        total_stock=10,
        reserved_stock=0,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture()
def seed_user(db_session):
    user = CorePlatformUser(id=1, email="test@example.com", full_name="Test User", role="customer")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    def override_get_current_user():
        return CurrentUser(id=1, role="customer", email="test@example.com")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
