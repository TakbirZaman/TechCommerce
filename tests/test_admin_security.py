"""
Admin security tests.

Verifies:
- Router-level admin auth enforcement (401/403/200)
- Login-issued token round-trip works with admin verification
- Expired / unknown-user / inactive-admin tokens are rejected
- AuditLog rows are written for mutating endpoints
- GET /api/v1/admin/analytics shape, zeros on empty DB, and correct math with data

IMPORTANT: DATABASE_URL is pointed at a temp file BEFORE importing main,
so the real ./techcommerce.db is never touched.
"""
import os
import tempfile

_TEST_DIR = tempfile.mkdtemp(prefix="tc_admin_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TEST_DIR, 'test_admin.db')}"

from datetime import timedelta  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from core.database import Base, SessionLocal, engine  # noqa: E402
from core.models.commerce import (  # noqa: E402
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from core.models.catalog import Brand, Category  # noqa: E402
from core.models.specification import Product  # noqa: E402
from core.models.user import AuditLog, User, UserRole  # noqa: E402
from core.services.auth_service import hash_password  # noqa: E402
from core.services.token_service import create_access_token  # noqa: E402
from main import app  # noqa: E402

ADMIN_EMAIL = "admin@test.example.com"
ADMIN_PASSWORD = "admin-pass-123"
CUSTOMER_EMAIL = "customer@test.example.com"
CUSTOMER_PASSWORD = "cust-pass-123"


def _make_user(db, email, password, role, is_active=True):
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=f"{role.value} user",
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, email, password):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


import pytest  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _make_user(db, ADMIN_EMAIL, ADMIN_PASSWORD, UserRole.ADMIN)
        _make_user(db, CUSTOMER_EMAIL, CUSTOMER_PASSWORD, UserRole.CUSTOMER)
    finally:
        db.close()
    c = TestClient(app)
    yield c
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


def test_admin_endpoint_401_without_token(client):
    resp = client.get("/api/v1/admin/dashboard")
    assert resp.status_code == 401


def test_admin_endpoint_401_with_garbage_token(client):
    resp = client.get("/api/v1/admin/dashboard", headers={"Authorization": "Bearer not.a.real.jwt"})
    assert resp.status_code == 401


def test_admin_endpoint_401_with_malformed_header(client):
    resp = client.get("/api/v1/admin/dashboard", headers={"Authorization": "Basic abc123"})
    assert resp.status_code == 401


def test_customer_token_gets_403(client):
    token = _login(client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
    resp = client.get("/api/v1/admin/dashboard", headers=_auth(token))
    assert resp.status_code == 403
    assert "Admin" in resp.json()["detail"]


def test_admin_login_token_round_trip_200(client):
    """Token issued by /api/v1/auth/login must pass admin verification (frontend path)."""
    token = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    resp = client.get("/api/v1/admin/dashboard", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    assert "total_products" in resp.json()


def test_directly_issued_token_round_trip_200(client):
    """Token created via token_service.create_access_token (same code path as login)."""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).one()
        token = create_access_token({"user_id": admin.id, "role": admin.role})
    finally:
        db.close()
    resp = client.get("/api/v1/admin/dashboard", headers=_auth(token))
    assert resp.status_code == 200


def test_expired_token_401(client):
    token = create_access_token({"user_id": 1}, expires_delta=timedelta(seconds=-60))
    resp = client.get("/api/v1/admin/dashboard", headers=_auth(token))
    assert resp.status_code == 401


def test_token_for_unknown_user_401(client):
    token = create_access_token({"user_id": 999999})
    resp = client.get("/api/v1/admin/dashboard", headers=_auth(token))
    assert resp.status_code == 401


def test_inactive_admin_403(client):
    db = SessionLocal()
    try:
        inactive = _make_user(db, "inactive@test.example.com", "x-pass-123", UserRole.ADMIN, is_active=False)
        token = create_access_token({"user_id": inactive.id, "role": inactive.role})
    finally:
        db.close()
    resp = client.get("/api/v1/admin/dashboard", headers=_auth(token))
    assert resp.status_code == 403


def test_tampered_token_signature_401(client):
    token = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    header, payload, sig = token.split(".")
    tampered = f"{header}.{payload}{'A' if not payload.endswith('A') else 'B'}.{sig}"
    resp = client.get("/api/v1/admin/dashboard", headers=_auth(tampered))
    assert resp.status_code == 401


def test_superuser_also_allowed(client):
    db = SessionLocal()
    try:
        super_admin = _make_user(db, "super@test.example.com", "super-pass-123", UserRole.SUPER_ADMIN)
        token = create_access_token({"user_id": super_admin.id, "role": super_admin.role})
    finally:
        db.close()
    resp = client.get("/api/v1/admin/dashboard", headers=_auth(token))
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


def test_audit_log_written_for_brand_create(client):
    token = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    resp = client.post(
        "/api/v1/admin/brands",
        json={"name": "AuditBrand", "slug": "audit-brand"},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    brand_id = resp.json()["id"]

    db = SessionLocal()
    try:
        row = db.query(AuditLog).filter(AuditLog.resource == "brand", AuditLog.resource_id == brand_id).one()
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).one()
        assert row.action == "create"
        assert row.user_id == admin.id
        assert "AuditBrand" in (row.details or "")
    finally:
        db.close()


def test_audit_log_written_for_order_status_update(client):
    # Seed brand/category/product + a paid order directly
    db = SessionLocal()
    try:
        brand = Brand(name="B", slug="b")
        category = Category(name="C", slug="c")
        db.add_all([brand, category])
        db.flush()
        product = Product(
            name="Widget", slug="widget", sku="SKU-1",
            brand_id=brand.id, category_id=category.id, price=100.0,
        )
        db.add(product)
        db.flush()
        order = Order(
            order_number="ORD-TEST-1",
            guest_email="g@example.com", guest_name="Guest", guest_phone="0123",
            subtotal=200, discount=0, delivery_charge=0, total_amount=200,
            payment_method=PaymentMethod.BKASH,
            payment_status=PaymentStatus.PAID,
            order_status=OrderStatus.PAID,
            shipping_address="addr", shipping_city="Dhaka", shipping_area="Gulshan",
        )
        db.add(order)
        db.flush()
        db.add(OrderItem(
            order_id=order.id, product_id=product.id,
            product_name="Widget", product_sku="SKU-1",
            quantity=2, unit_price=100, subtotal=200,
        ))
        db.commit()
        order_id = order.id
    finally:
        db.close()

    token = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    resp = client.put(
        f"/api/v1/admin/orders/{order_id}/status",
        json={"order_status": "processing"},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text

    db = SessionLocal()
    try:
        row = db.query(AuditLog).filter(AuditLog.resource == "order_status").one()
        assert row.action == "update"
        assert row.resource_id == order_id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


def test_analytics_empty_tables_zeroed(client):
    token = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    resp = client.get("/api/v1/admin/analytics", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert set(body) == {"totals", "revenue_by_day", "orders_by_status", "top_products", "low_stock", "recent_orders"}
    totals = body["totals"]
    assert set(totals) == {
        "products", "active_products", "users", "orders",
        "revenue_total", "pending_orders", "low_stock_count",
    }
    # Only the 2 fixture users exist (admin + customer), no products/orders
    assert totals["products"] == 0
    assert totals["active_products"] == 0
    assert totals["users"] == 2
    assert totals["orders"] == 0
    assert totals["revenue_total"] == 0
    assert totals["pending_orders"] == 0
    assert totals["low_stock_count"] == 0

    assert len(body["revenue_by_day"]) == 30
    today = body["revenue_by_day"][-1]["date"]
    assert len(today.split("-")) == 3  # "YYYY-MM-DD"
    for entry in body["revenue_by_day"]:
        assert set(entry) == {"date", "revenue", "orders"}
        assert entry["revenue"] == 0 and entry["orders"] == 0

    assert body["orders_by_status"] == []
    assert body["top_products"] == []
    assert body["low_stock"] == []
    assert body["recent_orders"] == []


def test_analytics_unauthorized(client):
    resp = client.get("/api/v1/admin/analytics")
    assert resp.status_code == 401


def test_analytics_with_data(client):
    db = SessionLocal()
    try:
        brand = Brand(name="B2", slug="b2")
        category = Category(name="C2", slug="c2")
        db.add_all([brand, category])
        db.flush()
        p1 = Product(
            name="Laptop Pro", slug="laptop-pro", sku="LP-1",
            brand_id=brand.id, category_id=category.id, price=1000.0,
            stock_quantity=3,
        )
        p2 = Product(
            name="Mouse", slug="mouse", sku="MS-1",
            brand_id=brand.id, category_id=category.id, price=20.0,
            stock_quantity=50,
        )
        db.add_all([p1, p2])
        db.flush()
        order = Order(
            order_number="ORD-AN-1",
            guest_email="g2@example.com", guest_name="Alice", guest_phone="0123",
            subtotal=2000, discount=0, delivery_charge=0, total_amount=2000,
            payment_method=PaymentMethod.BKASH,
            payment_status=PaymentStatus.PAID,
            order_status=OrderStatus.DELIVERED,
            shipping_address="addr", shipping_city="Dhaka", shipping_area="Banani",
        )
        db.add(order)
        db.flush()
        db.add(OrderItem(
            order_id=order.id, product_id=p1.id,
            product_name="Laptop Pro", product_sku="LP-1",
            quantity=2, unit_price=1000, subtotal=2000,
        ))
        db.commit()
    finally:
        db.close()

    token = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    resp = client.get("/api/v1/admin/analytics", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    t = body["totals"]
    assert t["products"] == 2
    assert t["active_products"] == 2
    assert t["orders"] == 1
    assert t["revenue_total"] == 2000.0
    assert t["pending_orders"] == 0
    assert t["low_stock_count"] == 1  # only Laptop Pro has stock <= 10

    # The paid order lands in today's bucket
    today_entry = body["revenue_by_day"][-1]
    assert today_entry["revenue"] == 2000.0
    assert today_entry["orders"] == 1

    assert body["orders_by_status"] == [{"status": "delivered", "count": 1}]

    assert body["top_products"] == [
        {"product_id": body["top_products"][0]["product_id"], "name": "Laptop Pro", "units_sold": 2, "revenue": 2000.0}
    ]

    assert len(body["low_stock"]) == 1
    assert body["low_stock"][0]["name"] == "Laptop Pro"
    assert body["low_stock"][0]["sku"] == "LP-1"
    assert body["low_stock"][0]["stock_quantity"] == 3

    assert len(body["recent_orders"]) == 1
    ro = body["recent_orders"][0]
    assert ro["order_number"] == "ORD-AN-1"
    assert ro["customer"] == "Alice"
    assert ro["total_amount"] == 2000.0
    assert ro["payment_status"] == "paid"
    assert ro["order_status"] == "delivered"
    assert ro["created_at"] is not None
