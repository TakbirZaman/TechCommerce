from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OrderNumberCounter(Base):
    """One row per year; incremented atomically under a row lock."""

    __tablename__ = "order_number_counters"

    year: Mapped[str] = mapped_column(String(4), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)
