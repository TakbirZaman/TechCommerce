"""
DB-layer tests for core/services/ai_search.search_products().

Uses a standalone temp-file SQLite engine built with
Base.metadata.create_all — the real ./techcommerce.db is never touched
(no DATABASE_URL override is needed because the FastAPI app is never
imported here).
"""
import os
import tempfile

_TEST_DIR = tempfile.mkdtemp(prefix="tc_ai_search_db_tests_")
_DB_PATH = os.path.join(_TEST_DIR, "test_ai_search.db")

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from core.database import Base  # noqa: E402
import core.models.catalog  # noqa: F401,E402  (registers table metadata)
import core.models.commerce  # noqa: F401,E402  (FK targets: users, orders, ...)
import core.models.pc_builder  # noqa: F401,E402
import core.models.specification  # noqa: F401,E402
import core.models.user  # noqa: F401,E402  (FK target: users)
from core.models.catalog import Brand, Category  # noqa: E402
from core.models.specification import Product, ProductSpecification  # noqa: E402
from core.services.ai_search import search_products  # noqa: E402

engine = create_engine(
    f"sqlite:///{_DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)
Base.metadata.create_all(bind=engine)
SessionFactory = sessionmaker(bind=engine, autoflush=False, future=True)


# ---------------------------------------------------------------------------
# Seed: 2 categories, 4 brands, 8 products (numeric + text-only specs)
# ---------------------------------------------------------------------------

def _add_product(db, name, slug, sku, brand, category, price, popularity,
                 specs):
    p = Product(
        name=name, slug=slug, sku=sku,
        brand_id=brand.id, category_id=category.id,
        price=price, popularity_score=popularity, is_active=True,
        stock_quantity=5,
    )
    db.add(p)
    db.flush()
    for key, value, numeric in specs:
        db.add(ProductSpecification(
            product_id=p.id, spec_key=key, value=value, numeric_value=numeric,
        ))
    return p


@pytest.fixture(scope="module")
def db():
    session = SessionFactory()
    laptop = Category(name="Laptops", slug="laptop", is_active=True)
    monitor = Category(name="Monitors", slug="monitor", is_active=True)
    asus = Brand(name="ASUS", slug="asus", is_active=True)
    lenovo = Brand(name="Lenovo", slug="lenovo", is_active=True)
    lg = Brand(name="LG", slug="lg", is_active=True)
    cooler = Brand(name="Cooler Master", slug="cooler-master", is_active=True)
    session.add_all([laptop, monitor, asus, lenovo, lg, cooler])
    session.flush()

    _add_product(session, "ASUS TUF Gaming A15", "asus-tuf-a15", "SKU-1",
                 asus, laptop, 120000, 90,
                 [("ram_gb", "16GB DDR5", 16.0),
                  ("storage_gb", "512GB SSD", 512.0),
                  ("gpu", "NVIDIA RTX 4070", None),
                  ("refresh_hz", "144Hz", 144.0)])
    _add_product(session, "ASUS Vivobook 15", "asus-vivobook-15", "SKU-2",
                 asus, laptop, 65000, 60,
                 [("ram_gb", "8GB DDR4", 8.0),
                  ("storage_gb", "512GB SSD", 512.0)])
    _add_product(session, "Lenovo IdeaPad Gaming 3", "lenovo-ideapad-g3", "SKU-3",
                 lenovo, laptop, 95000, 70,
                 # text-only RAM (numeric_value NULL) -> exercises the
                 # LIKE text fallback + parse_spec_number path
                 [("ram", "16GB DDR5", None),
                  ("storage_gb", "512GB SSD", 512.0)])
    _add_product(session, "Lenovo ThinkPad E14", "lenovo-thinkpad-e14", "SKU-4",
                 lenovo, laptop, 55000, 40,
                 [("ram_gb", "8GB DDR4", 8.0)])
    _add_product(session, "LG UltraGear 27", "lg-ultragear-27", "SKU-5",
                 lg, monitor, 48000, 80,
                 # text-only refresh rate (numeric_value NULL, "144Hz")
                 [("refresh_rate_hz", "144Hz", None),
                  ("display_size", "27", 27.0),
                  ("panel_type", "IPS", None)])
    _add_product(session, "LG 24MP60G", "lg-24mp60g", "SKU-6",
                 lg, monitor, 22000, 50,
                 [("refresh_hz", "75Hz", 75.0),
                  ("display_size", "24", 24.0)])
    _add_product(session, "Cooler Master GA2501", "cooler-master-ga2501", "SKU-7",
                 cooler, monitor, 33000, 30,
                 [("refresh_rate_hz", "144Hz", None),
                  ("display_size", "25", 25.0)])
    _add_product(session, "ASUS ROG Strix Scar 18", "asus-rog-scar-18", "SKU-8",
                 asus, laptop, 250000, 85,
                 [("ram_gb", "32GB DDR5", 32.0),
                  ("gpu", "NVIDIA RTX 4090", None)])
    session.commit()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Hard filtering
# ---------------------------------------------------------------------------

class TestHardFilters:
    def test_category_brand_budget(self, db):
        results = search_products(db, "asus laptop under 100000", limit=20)
        assert results, "expected non-empty results"
        for r in results:
            p = r["product"]
            assert p.category.slug == "laptop"
            assert p.brand.slug == "asus"
            assert p.price <= 100000
        names = {r["product"].name for r in results}
        assert "ASUS Vivobook 15" in names          # 65k, fits
        assert "ASUS TUF Gaming A15" not in names   # 120k, over budget
        assert "ASUS ROG Strix Scar 18" not in names

    def test_brand_slug_with_hyphen_matches(self, db):
        # parsed brand token 'cooler master' vs DB slug 'cooler-master'
        results = search_products(db, "cooler master monitor", limit=20)
        assert results
        assert all(r["product"].brand.slug == "cooler-master" for r in results)


# ---------------------------------------------------------------------------
# Spec matching
# ---------------------------------------------------------------------------

class TestSpecMatching:
    def test_numeric_spec_via_numeric_value(self, db):
        results = search_products(db, "16gb ram laptop", limit=20)
        names = {r["product"].name for r in results}
        assert "ASUS TUF Gaming A15" in names            # ram_gb numeric 16
        assert "Lenovo IdeaPad Gaming 3" in names        # ram "16GB DDR5" text
        assert "Lenovo ThinkPad E14" not in names        # 8GB
        assert all(r["product"].category.slug == "laptop" for r in results)

    def test_text_fallback_numeric_value_null(self, db):
        # "144Hz" stored as text with numeric_value IS NULL under the
        # real scraped key refresh_rate_hz
        results = search_products(db, "144hz monitor", limit=20)
        names = {r["product"].name for r in results}
        assert "LG UltraGear 27" in names
        assert "Cooler Master GA2501" in names
        assert "LG 24MP60G" not in names                 # 75Hz
        assert all(r["product"].category.slug == "monitor" for r in results)

    def test_numeric_8_does_not_match_80(self, db):
        # the LIKE text fallback must not let "8" match "80GB..."-style values
        results = search_products(db, "8gb ram laptop", limit=20)
        for r in results:
            specs = {s.spec_key: s for s in r["product"].specifications}
            values = [str(s.value).lower() for s in specs.values()]
            assert not any(v.startswith("80") for v in values)


# ---------------------------------------------------------------------------
# Garbage queries + relaxation
# ---------------------------------------------------------------------------

class TestGarbageAndRelaxation:
    def test_garbage_query_returns_zero_results(self, db):
        results = search_products(db, "xyzzy qqq", limit=12)
        assert results == []

    def test_overfiltered_query_relaxes_with_notes(self, db):
        # budget 1k is impossible -> filters get relaxed, notes recorded
        from core.services.ai_search import interpret
        interpretation = interpret(db, "lg monitor under 1000")
        results = search_products(db, interpretation, limit=20)
        interp_notes = interpretation["notes"]

        relaxed_notes = [n for n in interp_notes if "relaxed" in n]
        assert relaxed_notes, f"expected relaxation notes, got {interp_notes}"
        assert any("'brands'" in n for n in relaxed_notes)
        assert any("'budget_max'" in n for n in relaxed_notes)
        assert results
        # category survives relaxation
        assert all(r["product"].category.slug == "monitor" for r in results)

    def test_fully_relaxed_overfiltered_query_never_bare_searches(self, db):
        # 'apple' brand exists in vocab but has no seeded products and there
        # are no phones: every tier relaxes and the result must be 0 rows
        # (NOT popular products from a filter-free query)
        from core.services.ai_search import interpret
        interpretation = interpret(db, "apple phone under 1000")
        results = search_products(db, interpretation, limit=20)
        assert results == []
        relaxed = [n for n in interpretation["notes"] if "relaxed" in n]
        assert any("'brands'" in n for n in relaxed)
        assert any("'budget_max'" in n for n in relaxed)
        # category tier has no filter here (no 'phone' category in the seed
        # DB) so it is skipped, never relaxed -- and no bare query ran.
