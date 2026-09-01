"""
Comparison Engine API Routes

Compare products side-by-side within the same category.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from core.database import get_db
from core.models.comparison import Comparison, ComparisonItem, MAX_COMPARISON_ITEMS
from core.models.specification import Product, SpecificationTemplate

router = APIRouter(prefix="/api/v1/compare", tags=["comparison"])


# Schemas
class CompareAddRequest(BaseModel):
    product_id: int


class CompareProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    price: float
    brand: dict
    image: str | None
    specs: dict

    class Config:
        from_attributes = True


class ComparisonResponse(BaseModel):
    id: int
    category: dict
    products: list[CompareProductResponse]
    spec_keys: list[str]
    spec_labels: dict

    class Config:
        from_attributes = True


class ComparisonSummaryResponse(BaseModel):
    id: int
    product_count: int
    category_name: str

    class Config:
        from_attributes = True


# Helper functions
def get_session_id(request: Request) -> str:
    """Get session ID from cookie."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        import secrets
        session_id = secrets.token_urlsafe(32)
    return session_id


def get_or_create_comparison(db: Session, session_id: str, category_id: int) -> Comparison:
    """Get or create comparison for session and category."""
    comparison = db.execute(
        select(Comparison).where(
            Comparison.session_id == session_id,
            Comparison.category_id == category_id,
        )
    ).scalar_one_or_none()
    
    if comparison is None:
        comparison = Comparison(session_id=session_id, category_id=category_id)
        db.add(comparison)
        db.flush()
    
    return comparison


# Endpoints
@router.get("/sessions", response_model=list[ComparisonSummaryResponse])
def list_comparisons(request: Request, db: Session = Depends(get_db)):
    """List all comparison sessions for current user."""
    session_id = get_session_id(request)
    
    comparisons = db.execute(
        select(Comparison).where(Comparison.session_id == session_id)
    ).scalars().all()
    
    result = []
    for comp in comparisons:
        category = db.get("Category", comp.category_id)
        result.append(ComparisonSummaryResponse(
            id=comp.id,
            product_count=len(comp.items),
            category_name=category.name if category else "Unknown",
        ))
    
    return result


@router.get("/{comparison_id}", response_model=ComparisonResponse)
def get_comparison(
    comparison_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get comparison details with all products and specs."""
    session_id = get_session_id(request)
    
    comparison = db.execute(
        select(Comparison).where(
            Comparison.id == comparison_id,
            Comparison.session_id == session_id,
        )
    ).scalar_one_or_none()
    
    if not comparison:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison not found")
    
    # Get category and spec template
    category = db.get("Category", comparison.category_id)
    template = db.execute(
        select(SpecificationTemplate).where(SpecificationTemplate.category_id == comparison.category_id)
    ).scalar_one_or_none()
    
    spec_keys = []
    spec_labels = {}
    if template and template.template:
        for key, config in template.template.items():
            spec_keys.append(key)
            spec_labels[key] = config.get("name", key)
    
    # Get products with specs
    products = []
    for item in comparison.items:
        product = db.execute(
            select(Product)
            .options(
                joinedload(Product.brand),
                joinedload(Product.images),
                joinedload(Product.specifications),
            )
            .where(Product.id == item.product_id)
        ).scalar_one_or_none()
        
        if product:
            # Build specs dict
            specs = {s.spec_key: s.value for s in product.specifications}
            
            products.append(CompareProductResponse(
                id=product.id,
                name=product.name,
                slug=product.slug,
                price=float(product.price),
                brand={"id": product.brand.id, "name": product.brand.name, "slug": product.brand.slug} if product.brand else {},
                image=product.images[0].url if product.images else None,
                specs=specs,
            ))
    
    return ComparisonResponse(
        id=comparison.id,
        category={"id": category.id, "name": category.name, "slug": category.slug} if category else {},
        products=products,
        spec_keys=spec_keys,
        spec_labels=spec_labels,
    )


@router.post("/add", response_model=ComparisonSummaryResponse)
def add_to_comparison(
    payload: CompareAddRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Add a product to comparison."""
    session_id = get_session_id(request)
    
    # Get product
    product = db.get(Product, payload.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    # Get or create comparison for this category
    comparison = get_or_create_comparison(db, session_id, product.category_id)
    
    # Check if already in comparison
    existing = db.execute(
        select(ComparisonItem).where(
            ComparisonItem.comparison_id == comparison.id,
            ComparisonItem.product_id == payload.product_id,
        )
    ).scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product already in comparison")
    
    # Check max items
    if len(comparison.items) >= MAX_COMPARISON_ITEMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_COMPARISON_ITEMS} products can be compared",
        )
    
    # Check category matches
    if comparison.items:
        first_item = comparison.items[0]
        first_product = db.get(Product, first_item.product_id)
        if first_product and first_product.category_id != product.category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only compare products within the same category",
            )
    
    # Add item
    item = ComparisonItem(
        comparison_id=comparison.id,
        product_id=payload.product_id,
        sort_order=len(comparison.items),
    )
    db.add(item)
    db.commit()
    
    category = db.get("Category", comparison.category_id)
    return ComparisonSummaryResponse(
        id=comparison.id,
        product_count=len(comparison.items) + 1,
        category_name=category.name if category else "Unknown",
    )


@router.delete("/{comparison_id}/products/{product_id}")
def remove_from_comparison(
    comparison_id: int,
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Remove a product from comparison."""
    session_id = get_session_id(request)
    
    comparison = db.execute(
        select(Comparison).where(
            Comparison.id == comparison_id,
            Comparison.session_id == session_id,
        )
    ).scalar_one_or_none()
    
    if not comparison:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison not found")
    
    item = db.execute(
        select(ComparisonItem).where(
            ComparisonItem.comparison_id == comparison_id,
            ComparisonItem.product_id == product_id,
        )
    ).scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not in comparison")
    
    db.delete(item)
    
    # Delete comparison if empty
    remaining = db.execute(
        select(ComparisonItem).where(ComparisonItem.comparison_id == comparison_id)
    ).count()
    
    if remaining <= 1:  # Will be 0 after this delete
        db.delete(comparison)
    
    db.commit()
    
    return {"message": "Removed from comparison"}


@router.delete("/{comparison_id}")
def delete_comparison(
    comparison_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete entire comparison."""
    session_id = get_session_id(request)
    
    comparison = db.execute(
        select(Comparison).where(
            Comparison.id == comparison_id,
            Comparison.session_id == session_id,
        )
    ).scalar_one_or_none()
    
    if not comparison:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison not found")
    
    # Delete all items first
    for item in comparison.items:
        db.delete(item)
    
    db.delete(comparison)
    db.commit()
    
    return {"message": "Comparison deleted"}


@router.get("/{comparison_id}/winner")
def get_comparison_winner(
    comparison_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get the best value product from comparison.
    Simple scoring: lower price + higher specs = better value.
    """
    session_id = get_session_id(request)
    
    comparison = db.execute(
        select(Comparison).where(
            Comparison.id == comparison_id,
            Comparison.session_id == session_id,
        )
    ).scalar_one_or_none()
    
    if not comparison:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison not found")
    
    if len(comparison.items) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Need at least 2 products to compare")
    
    # Get products with specs
    products = []
    for item in comparison.items:
        product = db.execute(
            select(Product)
            .options(joinedload(Product.specifications))
            .where(Product.id == item.product_id)
        ).scalar_one_or_none()
        
        if product:
            products.append({
                "product": product,
                "specs": {s.spec_key: s.value for s in product.specifications},
            })
    
    # Simple scoring: normalize price and specs
    # Lower price = better, higher numeric specs = better
    scores = []
    for p in products:
        price_score = 1.0 / (p["product"].price / 100000)  # Normalize to 100k
        
        spec_score = 0
        spec_count = 0
        for key, value in p["specs"].items():
            try:
                numeric = float(value.replace("GB", "").replace("TB", "").replace(" ", ""))
                spec_score += numeric / 100  # Normalize
                spec_count += 1
            except (ValueError, AttributeError):
                pass
        
        if spec_count > 0:
            spec_score /= spec_count
        
        total_score = price_score * 0.4 + spec_score * 0.6  # Weight specs more
        
        scores.append({
            "product_id": p["product"].id,
            "product_name": p["product"].name,
            "price": p["product"].price,
            "score": total_score,
            "price_score": price_score,
            "spec_score": spec_score,
        })
    
    # Sort by score
    scores.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "winner": scores[0],
        "rankings": scores,
    }
