from pydantic import BaseModel


class PaymentInitiateRequest(BaseModel):
    order_id: int


class PaymentInitiateResponse(BaseModel):
    payment_id: int
    redirect_url: str | None
    gateway_transaction_id: str | None


class PaymentCallbackResult(BaseModel):
    status: str
    duplicate: bool
    order_number: str | None = None
