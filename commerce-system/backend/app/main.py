from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.v1.admin_orders import router as admin_orders_router
from app.api.v1.cart import router as cart_router
from app.api.v1.checkout import router as checkout_router
from app.api.v1.invoices import router as invoices_router
from app.api.v1.orders import router as orders_router
from app.api.v1.payments import router as payments_router

app = FastAPI(
    title="Commerce Service",
    description="Cart, checkout, order, payment, invoice lifecycle (feature/commerce)",
    version="0.1.0",
)

register_error_handlers(app)

app.include_router(cart_router)
app.include_router(checkout_router)
app.include_router(orders_router)
app.include_router(admin_orders_router)
app.include_router(payments_router)
app.include_router(invoices_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
