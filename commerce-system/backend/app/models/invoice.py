"""
Invoice model (Section 20-21).

The PDF binary is NEVER stored in Postgres. This row stores the object
storage key + metadata; app/services/storage_service.py handles the actual
S3/R2 read/write, and customers download via a short-lived signed URL
minted on request rather than a public object key.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    storage_key: Mapped[str] = mapped_column(String(512))
    storage_bucket: Mapped[str] = mapped_column(String(128))
    content_type: Mapped[str] = mapped_column(String(64), default="application/pdf")
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
