from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.v1 import (
    admin_2fa,
    admin_auth,
    admin_coupons,
    admin_orders,
    cart,
    checkout,
    invoices,
    orders,
    payments,
)
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Commerce Service",
    description="Cart, checkout, order, payment, invoice lifecycle",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

# Mount all routers
app.include_router(cart.router)
app.include_router(checkout.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(invoices.router)

# Admin routes (require authentication)
app.include_router(admin_auth.router)
app.include_router(admin_orders.router)
app.include_router(admin_coupons.router)
app.include_router(admin_2fa.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
def validate_environment():
    """Validate required environment variables at startup."""
    import logging
    logger = logging.getLogger("commerce.startup")
    
    warnings = settings.validate_required_settings()
    for warning in warnings:
        logger.warning(warning)


@app.get("/", tags=["root"])
def root():
    return {
        "service": "Commerce Service",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "admin_login": "/api/v1/admin/auth/login",
    }
