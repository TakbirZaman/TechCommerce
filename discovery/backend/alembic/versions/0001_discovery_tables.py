"""
Discovery module tables: reviews, review_moderation_logs, price_history,
homepage_section_overrides. Adjust FK targets if the real user/order/product
tables live in different schemas.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_discovery"
down_revision = None  # STUB: set to the current head of core-platform/commerce migrations
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("pros", sa.Text, nullable=True),
        sa.Column("cons", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
        sa.UniqueConstraint("product_id", "user_id", name="uq_review_product_user"),
    )
    op.create_index("ix_reviews_status", "reviews", ["status"])

    op.create_table(
        "review_moderation_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("review_id", sa.Integer, sa.ForeignKey("reviews.id"), nullable=False, index=True),
        sa.Column("admin_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False, index=True),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("change_reason", sa.String(80), nullable=True),
        sa.Column("changed_by_admin_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    op.create_table(
        "homepage_section_overrides",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("section_key", sa.String(60), nullable=False, index=True),
        sa.Column("product_id", sa.Integer, nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("position", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # STUB: also add, on the EXISTING categories table (core-platform), a
    # nullable JSON column for filter schema if it doesn't already have one:
    # op.add_column("categories", sa.Column("filterable_spec_schema", sa.JSON, server_default="{}"))

    # Full-text search support (Section 3) — GIN index for ranking (Section 4).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_fts ON products "
        "USING GIN (to_tsvector('english', coalesce(name, '') || ' ' || coalesce(description, '')))"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_products_fts")
    op.drop_table("homepage_section_overrides")
    op.drop_table("price_history")
    op.drop_table("review_moderation_logs")
    op.drop_index("ix_reviews_status", table_name="reviews")
    op.drop_table("reviews")
