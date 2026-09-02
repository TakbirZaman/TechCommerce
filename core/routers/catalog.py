"""
Catalog API Routes - Brands, Categories, Products

All endpoints are public for browsing.
Admin endpoints are protected separately.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from core.database import get_db
from core.models.catalog import Brand, Category
from core.models.specification import (
    Product,
    ProductImage,
    ProductSpecification,
    SpecificationTemplate,
    SpecificationOption,
)

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


# Response schemas
class BrandResponse(BaseModel):
    id: int
    name: str
    slug: str
    logo_url: str | None
    description: str | None
    is_active: bool

    class Config:
        from_attributes = True


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    parent_id: int | None
    description: str | None
    icon: str | None
    is_active: bool
    children: list["CategoryResponse"] = []

    class Config:
        from_attributes = True


class ProductImageResponse(BaseModel):
    id: int
    url: str
    alt_text: str | None
    is_primary: bool

    class Config:
        from_attributes = True


class SpecificationResponse(BaseModel):
    spec_key: str
    value: str
    numeric_value: float | None

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    sku: str
    description: str | None
    price: float
    compare_at_price: float | None
    stock_quantity: int
    is_active: bool
    is_featured: bool
    popularity_score: float
    brand: BrandResponse
    category: "CategoryResponse"
    images: list[ProductImageResponse]
    specifications: list[SpecificationResponse]

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    id: int
    name: str
    slug: str
    sku: str
    price: float
    compare_at_price: float | None
    stock_quantity: int
    is_featured: bool
    brand: BrandResponse
    category: "CategoryResponse"
    images: list[ProductImageResponse]

    class Config:
        from_attributes = True


class SpecificationOptionResponse(BaseModel):
    id: int
    spec_key: str
    value: str
    display_name: str | None
    sort_order: int

    class Config:
        from_attributes = True


class SpecificationTemplateResponse(BaseModel):
    id: int
    category_id: int
    template: dict
    options: list[SpecificationOptionResponse]

    class Config:
        from_attributes = True


# Brand endpoints
@router.get("/brands", response_model=list[BrandResponse])
def list_brands(db: Session = Depends(get_db)):
    """List all active brands."""
    brands = db.query(Brand).filter(Brand.is_active == True).order_by(Brand.name).all()
    return brands


@router.get("/brands/{slug}", response_model=BrandResponse)
def get_brand(slug: str, db: Session = Depends(get_db)):
    """Get brand by slug."""
    brand = db.query(Brand).filter(Brand.slug == slug, Brand.is_active == True).first()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return brand


# Category endpoints
@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """List all active categories with hierarchy."""
    categories = (
        db.query(Category)
        .filter(Category.parent_id.is_(None), Category.is_active == True)
        .order_by(Category.name)
        .all()
    )
    return categories


@router.get("/categories/{slug}", response_model=CategoryResponse)
def get_category(slug: str, db: Session = Depends(get_db)):
    """Get category by slug."""
    category = db.query(Category).filter(Category.slug == slug, Category.is_active == True).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@router.get("/categories/{slug}/spec-template", response_model=SpecificationTemplateResponse)
def get_category_spec_template(slug: str, db: Session = Depends(get_db)):
    """Get specification template for a category."""
    category = db.query(Category).filter(Category.slug == slug, Category.is_active == True).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    template = db.query(SpecificationTemplate).filter(
        SpecificationTemplate.category_id == category.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No spec template for this category")
    
    return template


# Product endpoints
@router.get("/products", response_model=list[ProductListResponse])
def list_products(
    category: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    sort: str = "popularity",
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List products with filtering and sorting."""
    query = (
        db.query(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.category),
            joinedload(Product.images),
        )
        .filter(Product.is_active == True)
    )
    
    # Filters
    if category:
        query = query.join(Category).filter(Category.slug == category)
    if brand:
        query = query.join(Brand).filter(Brand.slug == brand)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%"),
            )
        )
    
    # Sorting
    sort_options = {
        "popularity": Product.popularity_score.desc(),
        "price_asc": Product.price.asc(),
        "price_desc": Product.price.desc(),
        "newest": Product.created_at.desc(),
        "name": Product.name.asc(),
    }
    query = query.order_by(sort_options.get(sort, Product.popularity_score.desc()))
    
    # Pagination
    products = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return products


@router.get("/products/{slug}", response_model=ProductResponse)
def get_product(slug: str, db: Session = Depends(get_db)):
    """Get product by slug with all details."""
    product = (
        db.query(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.category),
            joinedload(Product.images),
            joinedload(Product.specifications),
        )
        .filter(Product.slug == slug, Product.is_active == True)
        .first()
    )
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    # Increment view count
    product.view_count += 1
    db.commit()
    
    return product


@router.get("/products/{slug}/specifications", response_model=list[SpecificationResponse])
def get_product_specifications(slug: str, db: Session = Depends(get_db)):
    """Get all specifications for a product."""
    product = db.query(Product).filter(Product.slug == slug, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    return product.specifications


@router.get("/products/{slug}/compare", response_model=ProductResponse)
def get_product_for_comparison(slug: str, db: Session = Depends(get_db)):
    """Get product for comparison (includes spec details)."""
    product = (
        db.query(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.category),
            joinedload(Product.images),
            joinedload(Product.specifications),
        )
        .filter(Product.slug == slug, Product.is_active == True)
        .first()
    )
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    return product


# Search endpoint
@router.get("/search", response_model=list[ProductListResponse])
def search_products(
    q: str = Query(..., min_length=1),
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search products."""
    query = (
        db.query(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.category),
            joinedload(Product.images),
        )
        .filter(Product.is_active == True)
        .filter(
            or_(
                Product.name.ilike(f"%{q}%"),
                Product.sku.ilike(f"%{q}%"),
                Product.description.ilike(f"%{q}%"),
                Brand.name.ilike(f"%{q}%"),
                Category.name.ilike(f"%{q}%"),
            )
        )
    )
    
    if category:
        query = query.join(Category).filter(Category.slug == category)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    products = query.offset((page - 1) * page_size).limit(page_size).all()
    return products


# Autocomplete endpoint
@router.get("/autocomplete")
def autocomplete(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Search autocomplete suggestions."""
    products = (
        db.query(Product)
        .filter(Product.is_active == True, Product.name.ilike(f"%{q}%"))
        .limit(10)
        .all()
    )
    
    brands = (
        db.query(Brand)
        .filter(Brand.is_active == True, Brand.name.ilike(f"%{q}%"))
        .limit(5)
        .all()
    )
    
    categories = (
        db.query(Category)
        .filter(Category.is_active == True, Category.name.ilike(f"%{q}%"))
        .limit(5)
        .all()
    )
    
    return {
        "products": [{"id": p.id, "name": p.name, "slug": p.slug} for p in products],
        "brands": [{"id": b.id, "name": b.name, "slug": b.slug} for b in brands],
        "categories": [{"id": c.id, "name": c.name, "slug": c.slug} for c in categories],
    }


# Product Reviews
class ReviewCreateRequest(BaseModel):
    rating: int
    title: str | None = None
    comment: str
    reviewer_name: str
    reviewer_email: str | None = None


@router.get("/products/{product_slug}/reviews")
def get_product_reviews(product_slug: str, db: Session = Depends(get_db)):
    """Get reviews for a product."""
    product = db.execute(
        select(Product).where(Product.slug == product_slug, Product.is_active == True)
    ).scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    from core.models.specification import ProductReview
    
    reviews = db.query(ProductReview).filter(
        ProductReview.product_id == product.id,
        ProductReview.is_active == True,
    ).order_by(ProductReview.created_at.desc()).all()
    
    avg_rating = db.query(func.avg(ProductReview.rating)).filter(
        ProductReview.product_id == product.id,
        ProductReview.is_active == True,
    ).scalar() or 0
    
    return {
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "title": r.title,
                "comment": r.comment,
                "reviewer_name": r.reviewer_name,
                "is_verified": r.is_verified,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reviews
        ],
        "average_rating": round(float(avg_rating), 1),
        "total_reviews": len(reviews),
    }


@router.post("/products/{product_slug}/reviews")
def create_product_review(
    product_slug: str,
    payload: ReviewCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a review for a product."""
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    product = db.execute(
        select(Product).where(Product.slug == product_slug, Product.is_active == True)
    ).scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    from core.models.specification import ProductReview
    
    review = ProductReview(
        product_id=product.id,
        reviewer_name=payload.reviewer_name,
        reviewer_email=payload.reviewer_email,
        rating=payload.rating,
        title=payload.title,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    
    return {"message": "Review submitted successfully", "id": review.id}


# ----------------------------- AI Search ------------------------------------
from core.services.ai_search import get_known_brands, parse_query, search_products as _ai_search_products


class AISearchResultItem(ProductListResponse):
    """Product card shape reused from ProductListResponse + ranking metadata."""
    score: float
    matched_on: list[str] = []


class AISearchResponse(BaseModel):
    query: str
    interpretation: dict
    results: list[AISearchResultItem]
    result_count: int


@router.get("/ai-search", response_model=AISearchResponse)
def ai_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(12, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Natural-language product search (local parser, no external APIs).

    Parses budget shorthand ("under 100k", "1.5 lakh"), use cases, category
    intents, brands and spec keywords; hard-filters where confident and
    soft-scores the rest. Gracefully relaxes filters instead of returning
    empty when over-filtered (documented in interpretation.notes).
    """
    interpretation = parse_query(q, known_brands=get_known_brands(db))
    matches = _ai_search_products(db, interpretation, limit=limit)

    results = []
    for m in matches:
        card = ProductListResponse.model_validate(m["product"])
        results.append(
            AISearchResultItem(
                **card.model_dump(),
                score=round(m["score"], 2),
                matched_on=m["matched_on"],
            )
        )

    return AISearchResponse(
        query=q,
        interpretation=interpretation,
        results=results,
        result_count=len(results),
    )
