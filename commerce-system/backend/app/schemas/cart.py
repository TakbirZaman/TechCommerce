from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


class CartItemCreateRequest(BaseModel):
    """
    Client sends ONLY product_id and quantity. Price is never accepted
    from the client (Branch 2, Section 3).
    """

    product_id: int
    quantity: int = Field(gt=0, le=999)


class CartItemUpdateRequest(BaseModel):
    quantity: int = Field(gt=0, le=999)


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    product_image_url: str | None = None
    unit_price: Decimal
    quantity: int
    subtotal: Decimal
    available_stock: int


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    subtotal: Decimal
    total_items: int
