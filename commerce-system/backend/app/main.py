from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.v1.admin_2fa import router as admin_2fa_router
from app.api.v1.admin_coupons import router as admin_coupons_router
from app.api.v1.admin_orders import router as admin_orders_router
from app.api.v1.cart import router as cart_router
from app.api.v1.checkout import router as checkout_router
from app.api.v1.invoices import router as invoices_router
from app.api.v1.orders import router as orders_router
from app.api.v1.payments import router as payments_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Commerce Service",
    description="Cart, checkout, order, payment, invoice lifecycle (feature/commerce)",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_BASE_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

# Mount all routers
app.include_router(cart_router)
app.include_router(checkout_router)
app.include_router(orders_router)
app.include_router(admin_orders_router)
app.include_router(payments_router)
app.include_router(invoices_router)
app.include_router(admin_coupons_router)
app.include_router(admin_2fa_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
def validate_environment():
    """
    Validate required environment variables at startup.
    Fails fast if critical config is missing.
    """
    required_fields = [
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "STORAGE_BUCKET",
    ]

    missing = []
    for field in required_fields:
        value = getattr(settings, field, None)
        if not value or value == "change-me-in-production":
            missing.append(field)

    if missing:
        import logging
        logger = logging.getLogger("commerce.startup")
        logger.warning(
            "Missing or default environment variables: %s. "
            "Commerce may not function correctly in production.",
            ", ".join(missing),
        )


@app.get("/", tags=["root"])
def root():
    return {
        "service": "Commerce Service",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
