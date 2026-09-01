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

app = FastAPI(
    title="TechCommerce",
    description="E-commerce platform with AI-powered product recommendations",
    version="1.0.0",
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(commerce.router)
app.include_router(comparison.router)
app.include_router(pc_builder.router)
app.include_router(advisor.router)
app.include_router(admin.router)

# Serve uploaded files
uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.on_event("startup")
def startup():
    init_db()
    # Auto-seed if DB is empty
    from core.database import SessionLocal
    from core.models.user import User
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            from scripts.seed import seed
            seed()
    finally:
        db.close()


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
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}
