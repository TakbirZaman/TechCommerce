from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus, PaymentMethod, PaymentStatus


class DeliveryInfo(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=6, max_length=32)
    address: str = Field(min_length=1)
    city: str = Field(min_length=1, max_length=120)
    area: str = Field(min_length=1, max_length=120)
    postal_code: str | None = Field(default=None, max_length=20)


class CheckoutRequest(BaseModel):
    """
    Client provides ONLY delivery info + payment method choice.
    No price/discount/total fields exist here — the backend recomputes
    everything from the user's current cart + server-side rules (Section 6).
    """

    delivery: DeliveryInfo
    payment_method: PaymentMethod
    discount_code: str | None = None


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    subtotal: Decimal
    discount: Decimal
    delivery_charge: Decimal
    total_amount: Decimal
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    order_status: OrderStatus
    shipping_full_name: str
    shipping_phone: str
    shipping_address: str
    shipping_city: str
    shipping_area: str
    shipping_postal_code: str | None
    items: list[OrderItemResponse]
    created_at: datetime


class OrderSummary(BaseModel):
    """Lightweight row for order-history list views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    total_amount: Decimal
    payment_status: PaymentStatus
    order_status: OrderStatus


class AdminOrderStatusUpdateRequest(BaseModel):
    order_status: OrderStatus
