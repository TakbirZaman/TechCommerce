"""
TechCommerce - Main FastAPI Application

Architecture:
- Layer 1: Core Platform (Auth, RBAC)
- Layer 2: Product Catalog (Specification Engine)
- Layer 3: Commerce (Cart, Orders, Payments)
- Layer 4: Smart Features (Comparison, PC Builder, AI Advisor)
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.database import init_db
from core.routers import auth, catalog, commerce, comparison, pc_builder, advisor, admin
# Optional routers (employee/payments etc. added later) — don't crash if import fails
try:
    from core.routers import employee as _employee_router  # type: ignore
except Exception:
    _employee_router = None
try:
    from core.routers import payments as _payments_router  # type: ignore
except Exception:
    _payments_router = None
try:
    from core.routers import invoices as _invoices_router  # type: ignore
except Exception:
    _invoices_router = None
try:
    from core.routers import notifications as _notifications_router  # type: ignore
except Exception:
    _notifications_router = None

import logging
from contextlib import asynccontextmanager
from fastapi import Request
from fastapi.responses import JSONResponse
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
_logger = logging.getLogger("techcommerce.access")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as e:
        _logger.warning("init_db failed: %s", e)
    try:
        from core.database import SessionLocal
        from core.services.permissions import sync_rbac_catalog
        db_rbac = SessionLocal()
        try:
            sync_rbac_catalog(db_rbac)
        finally:
            db_rbac.close()
    except Exception:
        pass
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
        _logger.warning("auto-seed failed: %s", e)
    yield

app = FastAPI(
    title="TechCommerce",
    description="E-commerce platform with AI-powered product recommendations",
    version="1.0.0",
    lifespan=lifespan,
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

_CORS_ORIGINS = list({
    FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://techcommerce-frontend.techcommerce-frontend.workers.dev",
})
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

@app.middleware("http")
async def add_logging(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        _logger.exception("unhandled %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
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
if _employee_router is not None:
    app.include_router(_employee_router.router)
if _payments_router is not None:
    app.include_router(_payments_router.router)
if _invoices_router is not None:
    app.include_router(_invoices_router.router)
if _notifications_router is not None:
    app.include_router(_notifications_router.router)

# Serve uploaded files
uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")





@app.get("/")
def root():
    eps = {
        "auth": "/api/v1/auth",
        "catalog": "/api/v1/catalog",
        "commerce": "/api/v1/commerce",
        "compare": "/api/v1/compare",
        "pc-builder": "/api/v1/pc-builder",
        "advisor": "/api/v1/advisor",
        "admin": "/api/v1/admin",
    }
    if _employee_router is not None:
        eps["employee"] = "/api/v1/employee"
    if _payments_router is not None:
        eps["payments"] = "/api/v1/payments"
    if _invoices_router is not None:
        eps["invoices"] = "/api/v1/invoices"
    if _notifications_router is not None:
        eps["notifications"] = "/api/v1/notifications"
    return {
        "name": "TechCommerce",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": eps,
    }


@app.get("/health")
def health():
    try:
        from sqlalchemy import text as _text
        from core.database import engine as _engine
        with _engine.connect() as _conn:
            _conn.execute(_text("SELECT 1"))
        return {"status": "ok", "database": "up"}
    except Exception as e:
        _logger.warning("health DB check failed: %s", e)
        return JSONResponse(status_code=200, content={"status": "degraded", "database": "down", "detail": str(e)[:200]})
