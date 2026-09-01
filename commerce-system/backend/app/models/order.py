"""
Order models (Branch 2, Sections 7-9).

- OrderItem stores unit_price as a SNAPSHOT at purchase time. Historical
  orders must never be recalculated from the current Product.price.
- Order.status transitions are NOT enforced here (that would allow bypassing
  the state machine by editing the model directly) — they're enforced in
  app/services/order_state_machine.py, which is the ONLY code path allowed
  to change Order.status.
- ShippingInfo columns are an immutable snapshot taken at checkout, not a
  live reference to the user's profile address (Section 24).
"""
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUND_REQUESTED = "REFUND_REQUESTED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, enum.Enum):
    BKASH = "BKASH"
    NAGAD = "NAGAD"
    SSLCOMMERZ = "SSLCOMMERZ"


class PaymentStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # --- Money (all server-calculated, never trusted from client) ---
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    delivery_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, native_enum=False))
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False), default=PaymentStatus.UNPAID
    )
    order_status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False), default=OrderStatus.PENDING
    )

    # --- Immutable shipping snapshot (Section 24) ---
    shipping_full_name: Mapped[str] = mapped_column(String(255))
    shipping_phone: Mapped[str] = mapped_column(String(32))
    shipping_address: Mapped[str] = mapped_column(Text)
    shipping_city: Mapped[str] = mapped_column(String(120))
    shipping_area: Mapped[str] = mapped_column(String(120))
    shipping_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821  (defined in app.models.payment)
        back_populates="order", lazy="selectin"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)

    # SNAPSHOT fields — captured once at order creation, never recomputed.
    product_name: Mapped[str] = mapped_column(String(255))
    product_sku: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[int] = mapped_column()
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order: Mapped["Order"] = relationship(back_populates="items")


# Fixed, allow-listed order-status transition graph (Section 9).
# order_state_machine.py is the ONLY code path allowed to change Order.order_status,
# and it rejects any transition not present here (e.g. DELIVERED -> PAYMENT_PENDING).
ALLOWED_ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAYMENT_PENDING, OrderStatus.CANCELLED},
    OrderStatus.PAYMENT_PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.PROCESSING, OrderStatus.REFUND_REQUESTED, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.REFUND_REQUESTED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED, OrderStatus.REFUND_REQUESTED},
    OrderStatus.DELIVERED: {OrderStatus.REFUND_REQUESTED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUND_REQUESTED: {OrderStatus.REFUNDED, OrderStatus.PAID},  # PAID = refund request denied
    OrderStatus.REFUNDED: set(),
}
