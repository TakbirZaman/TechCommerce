"""initial commerce schema (+ core-platform stub tables)

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-01

NOTE: The users / brands / categories / products tables created here are
STUBS standing in for feature/core-platform (see
app/models/core_platform_stubs.py). When that branch lands, drop this
migration's stub-table creation and depend on core-platform's own
migrations instead — do not run both against the same database.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- core-platform stub tables ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="customer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "brands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_purchasable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("total_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- cart ---
    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True, index=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cart_id", sa.Integer(), sa.ForeignKey("carts.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), index=True, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
    )

    # --- order number counters (shared by ORD-* and INV-*) ---
    op.create_table(
        "order_number_counters",
        sa.Column("year", sa.String(4), primary_key=True),
        sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
    )

    # --- orders ---
    payment_method_enum = sa.Enum("BKASH", "NAGAD", "SSLCOMMERZ", name="payment_method_enum", native_enum=False)
    order_payment_status_enum = sa.Enum(
        "UNPAID", "INITIATED", "PENDING", "PAID", "FAILED", "REFUNDED",
        name="order_payment_status_enum", native_enum=False,
    )
    order_status_enum = sa.Enum(
        "PENDING", "PAYMENT_PENDING", "PAID", "PROCESSING", "SHIPPED",
        "DELIVERED", "CANCELLED", "REFUND_REQUESTED", "REFUNDED",
        name="order_status_enum", native_enum=False,
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_number", sa.String(32), unique=True, index=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("delivery_charge", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method", payment_method_enum, nullable=False),
        sa.Column("payment_status", order_payment_status_enum, nullable=False, server_default="UNPAID"),
        sa.Column("order_status", order_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("shipping_full_name", sa.String(255), nullable=False),
        sa.Column("shipping_phone", sa.String(32), nullable=False),
        sa.Column("shipping_address", sa.Text(), nullable=False),
        sa.Column("shipping_city", sa.String(120), nullable=False),
        sa.Column("shipping_area", sa.String(120), nullable=False),
        sa.Column("shipping_postal_code", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), index=True, nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("product_sku", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
    )

    # --- payments ---
    payment_gateway_enum = sa.Enum("BKASH", "NAGAD", "SSLCOMMERZ", name="paymentgateway", native_enum=False)
    payment_status_enum = sa.Enum(
        "INITIATED", "PENDING", "SUCCESS", "FAILED", "CANCELLED", "REFUNDED",
        name="paymentstatus", native_enum=False,
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), index=True, nullable=False),
        sa.Column("gateway", payment_gateway_enum, nullable=False),
        sa.Column("merchant_reference", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("transaction_id", sa.String(128), index=True, nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="BDT"),
        sa.Column("status", payment_status_enum, nullable=False, server_default="INITIATED"),
        sa.Column("gateway_response_reference", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "processed_callbacks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dedupe_key", sa.String(128), unique=True, index=True, nullable=False),
        sa.Column("gateway", payment_gateway_enum, nullable=False),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("result_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- invoices ---
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), unique=True, index=True, nullable=False),
        sa.Column("invoice_number", sa.String(32), unique=True, index=True, nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("storage_bucket", sa.String(128), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False, server_default="application/pdf"),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("processed_callbacks")
    op.drop_table("payments")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("order_number_counters")
    op.drop_table("cart_items")
    op.drop_table("carts")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("brands")
    op.drop_table("users")
