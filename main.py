"""
TechCommerce - Main FastAPI Application

Architecture:
- Layer 1: Core Platform (Auth, RBAC)
- Layer 2: Product Catalog (Specification Engine)
- Layer 3: Commerce (Cart, Orders, Payments)
- Layer 4: Smart Features (Comparison, PC Builder, AI Advisor)
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import logging
import time

from fastapi import Request
from fastapi.responses import JSONResponse

from core.database import init_db
from core.routers import auth, catalog, commerce, comparison, pc_builder, advisor, admin, employee, payments, invoices, notifications


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — never block deployment if DB is temporarily unavailable
    # (Render Postgres free tier can sleep/cold-start). Health endpoint stays up.
    try:
        init_db()
    except Exception as e:
        _logger.warning("init_db failed (will retry on first request): %s", e)
    # Ensure RBAC catalog is synced (idempotent)
    try:
        from core.database import SessionLocal
        from core.services.permissions import sync_rbac_catalog
        db_rbac = SessionLocal()
        try:
            sync_rbac_catalog(db_rbac)
        finally:
            db_rbac.close()
    except Exception:
        pass  # don't block startup if RBAC sync fails
    # Auto-seed if DB is empty
    try:
        from core.database import SessionLocal as _SessionLocal
        from core.models.user import User
        db = _SessionLocal()
        try:
            if db.query(User).count() == 0:
                from scripts.seed import seed
                seed()
        finally:
            db.close()
    except Exception as e:
        _logger.warning("auto-seed check failed (DB may be cold): %s", e)
    yield
    # Shutdown (no-op)


app = FastAPI(
    title="TechCommerce",
    description="E-commerce platform with AI-powered product recommendations",
    version="1.0.0",
    lifespan=lifespan,
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Production observability — Sentry (no-op if DSN not set)
try:
    import sentry_sdk  # type: ignore

    _sentry_dsn = os.getenv("SENTRY_DSN")
    if _sentry_dsn:
        sentry_sdk.init(dsn=_sentry_dsn, traces_sample_rate=0.1)
except Exception:
    pass

# CORS — explicit origins + regex for Vercel preview + Cloudflare Workers deployments.
# `allow_origins` does NOT support wildcards like "https://*.vercel.app" literally,
# so we use `allow_origin_regex` for that pattern.
# Also allow workers.dev for Cloudflare frontend (techcommerce-frontend.workers.dev).
_CORS_ORIGINS = list({
    FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://techcommerce-frontend.techcommerce-frontend.workers.dev",
})
# Also honor comma-separated extra origins via env var for flexibility
_extra = os.getenv("CORS_EXTRA_ORIGINS", "")
if _extra:
    for o in _extra.split(","):
        o = o.strip()
        if o:
            _CORS_ORIGINS.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.(vercel\.app|workers\.dev)",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Session-ID", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# Structured access log + security headers + request ID
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
_logger = logging.getLogger("techcommerce.access")


@app.middleware("http")
async def add_security_and_logging(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:  # global error envelope (never leak stack in prod)
        _logger.exception("unhandled error %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    # Security headers (CSP is intentionally relaxed for Swagger/Next.js inline; tighten per-route if needed)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "") or response.headers.get("X-Request-ID", "")
    # CSP: allow self + Swagger CDN when needed
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https: blob:; connect-src 'self' *",
    )
    dur = (time.time() - start) * 1000
    _logger.info("%s %s %s %.1fms", request.method, request.url.path, response.status_code, dur)
    return response


# Include routers
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(commerce.router)
app.include_router(comparison.router)
app.include_router(pc_builder.router)
app.include_router(advisor.router)
app.include_router(admin.router)
app.include_router(employee.router)
app.include_router(payments.router)
app.include_router(invoices.router)
app.include_router(notifications.router)

# Serve uploaded files
uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/")
def root():
    return {
        "name": "TechCommerce",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/v1/auth",
            "catalog": "/api/v1/catalog",
            "commerce": "/api/v1/commerce",
            "compare": "/api/v1/compare",
            "pc-builder": "/api/v1/pc-builder",
            "advisor": "/api/v1/advisor",
            "admin": "/api/v1/admin",
            "employee": "/api/v1/employee",
            "payments": "/api/v1/payments",
            "invoices": "/api/v1/invoices",
            "notifications": "/api/v1/notifications",
        },
    }


@app.get("/health")
def health():
    # Deep health: check DB connectivity, but never 500 — return degraded status
    try:
        from sqlalchemy import text as _text
        from core.database import engine as _engine
        with _engine.connect() as _conn:
            _conn.execute(_text("SELECT 1"))
        return {"status": "ok", "database": "up"}
    except Exception as e:
        _logger.warning("health DB check failed: %s", e)
        return JSONResponse(
            status_code=200,
            content={"status": "degraded", "database": "down", "detail": str(e)[:200]},
        )
