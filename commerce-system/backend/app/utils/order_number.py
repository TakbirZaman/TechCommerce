"""
Order number generation (Section 8).

Format: ORD-{YEAR}-{6-digit sequence}, e.g. ORD-2026-000001.

Uses a per-year row in `order_number_counters`, incremented under
SELECT ... FOR UPDATE so concurrent order creation can't produce
duplicate numbers. This is portable across Postgres (real row lock) and
SQLite (used in tests; lock is a no-op but single-process tests are still
correct). Deliberately not derived from Order.id, so customer-facing
numbers don't leak total row counts and can restart cleanly each year.

Must be called within the same transaction as the Order insert so the
lock is held for the duration of order creation.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order_number_counter import OrderNumberCounter


def generate_order_number(db: Session, year: int) -> str:
    year_str = str(year)

    counter = db.execute(
        select(OrderNumberCounter).where(OrderNumberCounter.year == year_str).with_for_update()
    ).scalar_one_or_none()

    if counter is None:
        counter = OrderNumberCounter(year=year_str, last_value=0)
        db.add(counter)
        db.flush()

    counter.last_value += 1
    db.flush()

    return f"ORD-{year_str}-{counter.last_value:06d}"
