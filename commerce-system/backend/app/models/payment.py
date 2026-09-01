"""
Payment model (Branch 2, Section 12).

One Order can have multiple Payment rows over time (e.g. a failed bKash
attempt followed by a successful retry) — Payment is NOT 1:1 with Order.
gateway_transaction_id is unique-indexed to support idempotent callback
handling (Section 16): a duplicate callback for the same transaction_id
is detected by this constraint before any side effect runs.
"""
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class PaymentGateway(str, enum.Enum):
    BKASH = "BKASH"
    NAGAD = "NAGAD"
    SSLCOMMERZ = "SSLCOMMERZ"


class PaymentStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)

    gateway: Mapped[PaymentGateway] = mapped_column(Enum(PaymentGateway, native_enum=False))

    # Our own reference handed to the gateway when initiating (e.g. bKash
    # merchantInvoiceNumber / Nagad orderId / SSLCommerz tran_id).
    merchant_reference: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # The gateway's own transaction/payment identifier, populated once known
    # (bKash paymentID, Nagad paymentRefId, SSLCommerz val_id/bank_tran_id).
    # Unique + nullable: unique across non-null values only, enforced at the
    # service layer since not all DBs partial-index NULLs the same way.
    transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="BDT")

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False), default=PaymentStatus.INITIATED
    )

    # Raw gateway response stored for audit/reconciliation (never surfaced to frontend as-is).
    gateway_response_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped["Order"] = relationship(back_populates="payments")  # noqa: F821


class ProcessedCallback(Base, TimestampMixin):
    """
    Idempotency ledger for payment callbacks (Section 16-17).

    Every inbound gateway callback/webhook/IPN is hashed to a dedupe_key
    (gateway + transaction reference + raw payload hash) BEFORE any order/
    inventory/invoice side effect runs. If the key already exists, the
    callback is a replay and is answered from the stored result without
    reprocessing.
    """

    __tablename__ = "processed_callbacks"

    id: Mapped[int] = mapped_column(primary_key=True)
    dedupe_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    gateway: Mapped[PaymentGateway] = mapped_column(Enum(PaymentGateway, native_enum=False))
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True)
    result_status: Mapped[str] = mapped_column(String(32))
