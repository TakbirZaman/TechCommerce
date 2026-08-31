"""
Shared pytest fixtures. Uses SQLite in-memory for speed; note the
`filter_engine`'s JSON-path filtering and ranking's `to_tsvector`/`ts_rank`
calls are Postgres-specific and are skipped/mocked in SQLite-based tests
(marked accordingly). Run the full suite against Postgres in CI.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.stubs import Base, Brand, Category, Product, ProductStatus, User


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def sample_data(db_session):
    laptops = Category(name="Laptops", slug="laptops", filterable_spec_schema={
        "cpu": {"label": "CPU", "type": "enum"},
        "ram_gb": {"label": "RAM", "type": "enum", "unit": "GB"},
    })
    phones = Category(name="Phones", slug="phones")
    db_session.add_all([laptops, phones])
    db_session.flush()

    asus = Brand(name="ASUS", slug="asus")
    samsung = Brand(name="Samsung", slug="samsung")
    db_session.add_all([asus, samsung])
    db_session.flush()

    p1 = Product(
        name="ASUS ROG Zephyrus G14", slug="asus-rog-zephyrus-g14", sku="SKU-001",
        brand_id=asus.id, category_id=laptops.id, price=1800.0,
        status=ProductStatus.AVAILABLE, stock_quantity=5,
        specifications={"cpu": "Ryzen 9", "ram_gb": 16, "gpu": "RTX 5070"},
        popularity_score=50,
    )
    p2 = Product(
        name="ASUS TUF Gaming A15", slug="asus-tuf-gaming-a15", sku="SKU-002",
        brand_id=asus.id, category_id=laptops.id, price=1200.0,
        status=ProductStatus.AVAILABLE, stock_quantity=0,
        specifications={"cpu": "Ryzen 7", "ram_gb": 16, "gpu": "RTX 4060"},
        popularity_score=20,
    )
    p3 = Product(
        name="Samsung Galaxy S25", slug="samsung-galaxy-s25", sku="SKU-003",
        brand_id=samsung.id, category_id=phones.id, price=999.0,
        status=ProductStatus.AVAILABLE, stock_quantity=10,
        specifications={"ram_gb": 12, "storage_gb": 256},
        popularity_score=90,
    )
    db_session.add_all([p1, p2, p3])

    user = User(email="tester@example.com")
    db_session.add(user)
    db_session.commit()

    return {"laptops": laptops, "phones": phones, "asus": asus, "samsung": samsung,
            "p1": p1, "p2": p2, "p3": p3, "user": user}
