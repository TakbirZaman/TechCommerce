"""
Homepage sections endpoint (Section 23).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.stubs import Product
from app.models.featured import HomepageSectionOverride
from app.schemas.product import ProductSummary

router = APIRouter(tags=["homepage"])


@router.get("/homepage/sections")
def get_homepage_sections(db: Session = Depends(get_db)):
    """
    Returns curated homepage sections:
    - featured: Admin-pinned featured products
    - trending: Products with highest popularity score
    - new_arrivals: Most recently added products
    - deals: Products on sale (price < original price, if tracked)
    """
    # Featured products (admin-curated)
    featured_products = (
        db.query(Product)
        .filter(Product.is_featured == True, Product.is_visible == True, Product.is_active == True)
        .order_by(Product.popularity_score.desc())
        .limit(12)
        .all()
    )

    # Trending products (by popularity score)
    trending_products = (
        db.query(Product)
        .filter(Product.is_visible == True, Product.is_active == True)
        .order_by(Product.popularity_score.desc())
        .limit(12)
        .all()
    )

    # New arrivals (most recent)
    new_arrivals = (
        db.query(Product)
        .filter(Product.is_visible == True, Product.is_active == True)
        .order_by(Product.created_at.desc())
        .limit(12)
        .all()
    )

    return {
        "featured": [ProductSummary.model_validate(p) for p in featured_products],
        "trending": [ProductSummary.model_validate(p) for p in trending_products],
        "new_arrivals": [ProductSummary.model_validate(p) for p in new_arrivals],
    }


@router.get("/homepage/sections/{section_key}")
def get_homepage_section(
    section_key: str,
    db: Session = Depends(get_db),
):
    """
    Returns products for a specific homepage section with admin overrides
    (pin/exclude) applied.
    """
    # Get admin overrides for this section
    overrides = (
        db.query(HomepageSectionOverride)
        .filter(HomepageSectionOverride.section_key == section_key)
        .all()
    )

    pinned_ids = {o.product_id for o in overrides if o.action == "pin"}
    excluded_ids = {o.product_id for o in overrides if o.action == "exclude"}

    query = db.query(Product).filter(Product.is_visible == True, Product.is_active == True)

    # Apply section-specific sorting
    if section_key == "trending":
        query = query.order_by(Product.popularity_score.desc())
    elif section_key == "new_arrivals":
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.popularity_score.desc())

    products = query.limit(24).all()

    # Apply overrides
    result = []
    for p in products:
        if p.id in excluded_ids:
            continue
        result.append(ProductSummary.model_validate(p))

    # Add pinned products at the beginning
    if pinned_ids:
        pinned_products = (
            db.query(Product)
            .filter(Product.id.in_(pinned_ids), Product.is_visible == True)
            .all()
        )
        pinned_summaries = [ProductSummary.model_validate(p) for p in pinned_products]
        result = pinned_summaries + [r for r in result if r.id not in pinned_ids]

    return {"section_key": section_key, "products": result[:24]}
