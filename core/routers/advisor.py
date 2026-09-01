"""
AI Product Advisor API Routes

Natural language product recommendations.
User writes: "Suggest a laptop under 100k for programming"
AI extracts requirements and recommends products.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from core.database import get_db
from core.models.advisor import AIRecommendation, UserEvent
from core.models.catalog import Brand, Category
from core.models.specification import Product

router = APIRouter(prefix="/api/v1/advisor", tags=["advisor"])


# Schemas
class AdvisorQueryRequest(BaseModel):
    query: str
    session_id: str | None = None


class ExtractedRequirements(BaseModel):
    category: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    use_case: str | None = None
    preferences: dict = {}


class RecommendedProduct(BaseModel):
    id: int
    name: str
    slug: str
    price: float
    image: str | None
    brand: str
    score: float
    reasons: list[str]
    tradeoffs: list[str]
    specs: dict


class AdvisorResponse(BaseModel):
    query: str
    extracted_requirements: ExtractedRequirements
    recommendations: list[RecommendedProduct]
    total_candidates: int
    message: str


# Simple keyword extraction (no LLM needed initially)
def extract_requirements(query: str) -> ExtractedRequirements:
    """
    Extract requirements from natural language query.
    
    Simple rule-based extraction:
    - Budget: "under 100k", "below 50000", etc.
    - Category: "laptop", "phone", "monitor", etc.
    - Use case: "programming", "gaming", "editing", etc.
    """
    query_lower = query.lower()
    
    # Extract budget
    budget_max = None
    budget_min = None
    
    # Common budget patterns
    import re
    budget_patterns = [
        r"under\s+(\d+)k",
        r"below\s+(\d+)k",
        r"less\s+than\s+(\d+)k",
        r"budget\s+(?:of\s+)?(\d+)k",
        r"under\s+(\d+)",
        r"below\s+(\d+)",
        r"less\s+than\s+(\d+)",
    ]
    
    for pattern in budget_patterns:
        match = re.search(pattern, query_lower)
        if match:
            amount = float(match.group(1))
            # If amount is in thousands (e.g., "100k")
            if "k" in pattern:
                amount *= 1000
            budget_max = amount
            break
    
    # Extract category
    category = None
    category_keywords = {
        "laptop": ["laptop", "notebook", "macbook"],
        "phone": ["phone", "smartphone", "mobile", "iphone", "galaxy"],
        "monitor": ["monitor", "display", "screen"],
        "desktop": ["desktop", "pc", "computer"],
        "tablet": ["tablet", "ipad"],
        "gpu": ["gpu", "graphics card", "rtx", "gtx"],
        "cpu": ["cpu", "processor", "ryzen", "intel", "core"],
    }
    
    for cat, keywords in category_keywords.items():
        for kw in keywords:
            if kw in query_lower:
                category = cat
                break
        if category:
            break
    
    # Extract use case
    use_case = None
    use_case_keywords = {
        "programming": ["programming", "coding", "developer", "software"],
        "gaming": ["gaming", "games", "gamer"],
        "editing": ["editing", "video editing", "photo editing", "photoshop"],
        "design": ["design", "graphic design", "ui/ux"],
        "office": ["office", "work", "business", "productivity"],
        "student": ["student", "study", "college", "university"],
    }
    
    for case, keywords in use_case_keywords.items():
        for kw in keywords:
            if kw in query_lower:
                use_case = case
                break
        if use_case:
            break
    
    return ExtractedRequirements(
        category=category,
        budget_min=budget_min,
        budget_max=budget_max,
        use_case=use_case,
    )


def score_product(product: Product, requirements: ExtractedRequirements) -> tuple[float, list[str], list[str]]:
    """
    Score a product based on requirements.
    
    Returns: (score, reasons, tradeoffs)
    """
    score = 50.0  # Base score
    reasons = []
    tradeoffs = []
    
    specs = {s.spec_key: s.value for s in product.specifications}
    
    # Budget match (30% weight)
    if requirements.budget_max:
        if product.price <= requirements.budget_max:
            budget_ratio = product.price / requirements.budget_max
            # Better score for products closer to budget (not too cheap)
            if budget_ratio > 0.5:
                score += 15 * budget_ratio
                reasons.append(f"Fits budget (৳{product.price:,.0f} / ৳{requirements.budget_max:,.0f})")
            else:
                score += 10
                reasons.append("Well within budget")
        else:
            over_by = (product.price - requirements.budget_max) / requirements.budget_max
            if over_by < 0.1:  # Within 10% over budget
                score -= 5
                tradeoffs.append(f"Slightly over budget by ৳{product.price - requirements.budget_max:,.0f}")
            else:
                score -= 20
                tradeoffs.append(f"Over budget by ৳{product.price - requirements.budget_max:,.0f}")
    
    # Spec scoring (50% weight)
    spec_score = 0
    spec_count = 0
    
    # RAM
    if "ram_gb" in specs:
        try:
            ram = int(specs["ram_gb"].replace("GB", "").strip())
            if ram >= 16:
                spec_score += 20
                reasons.append(f"{ram}GB RAM - great for multitasking")
            elif ram >= 8:
                spec_score += 10
                reasons.append(f"{ram}GB RAM - sufficient for most tasks")
            else:
                spec_score += 5
                tradeoffs.append(f"{ram}GB RAM - may be limiting")
            spec_count += 1
        except ValueError:
            pass
    
    # Storage
    if "storage_gb" in specs:
        try:
            storage = int(specs["storage_gb"].replace("GB", "").replace("TB", "").strip())
            if "TB" in specs.get("storage_gb", ""):
                storage *= 1000
            if storage >= 512:
                spec_score += 15
                reasons.append(f"{storage}GB storage - ample space")
            elif storage >= 256:
                spec_score += 10
                reasons.append(f"{storage}GB storage - decent capacity")
            else:
                spec_score += 5
                tradeoffs.append(f"{storage}GB storage - may need external storage")
            spec_count += 1
        except ValueError:
            pass
    
    # CPU (simplified scoring)
    if "cpu" in specs:
        cpu = specs["cpu"].lower()
        if "i7" in cpu or "ryzen 7" in cpu:
            spec_score += 20
            reasons.append("Powerful CPU for demanding tasks")
        elif "i5" in cpu or "ryzen 5" in cpu:
            spec_score += 15
            reasons.append("Good CPU for everyday use")
        elif "i3" in cpu or "ryzen 3" in cpu:
            spec_score += 10
            tradeoffs.append("Entry-level CPU")
        elif "i9" in cpu or "ryzen 9" in cpu:
            spec_score += 25
            reasons.append("High-end CPU for intensive workloads")
        spec_count += 1
    
    # Use case matching
    if requirements.use_case == "programming":
        if "ram_gb" in specs:
            try:
                ram = int(specs["ram_gb"].replace("GB", "").strip())
                if ram >= 16:
                    score += 10
                    reasons.append("Good for programming with multiple IDEs")
            except ValueError:
                pass
    elif requirements.use_case == "gaming":
        if "gpu" in specs:
            gpu = specs["gpu"].lower()
            if "rtx" in gpu:
                score += 15
                reasons.append("Great GPU for gaming")
            elif "gtx" in gpu:
                score += 10
                reasons.append("Decent GPU for gaming")
        else:
            tradeoffs.append("No dedicated GPU - not ideal for gaming")
    
    # Normalize score
    if spec_count > 0:
        score += (spec_score / spec_count) * 0.5
    
    # Clamp score
    score = max(0, min(100, score))
    
    return score, reasons, tradeoffs


# Endpoints
@router.post("/recommend", response_model=AdvisorResponse)
def get_recommendations(
    payload: AdvisorQueryRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get product recommendations based on natural language query.
    
    Example: "Suggest a laptop under 100k for programming"
    """
    session_id = payload.session_id or request.cookies.get("session_id", "anonymous")
    
    # Extract requirements from query
    requirements = extract_requirements(payload.query)
    
    # Build query
    query = db.query(Product).options(
        joinedload(Product.brand),
        joinedload(Product.category),
        joinedload(Product.images),
        joinedload(Product.specifications),
    ).filter(Product.is_active == True)
    
    # Filter by category
    if requirements.category:
        query = query.join(Category).filter(
            Category.slug.contains(requirements.category) |
            Category.name.ilike(f"%{requirements.category}%")
        )
    
    # Filter by budget
    if requirements.budget_max:
        query = query.filter(Product.price <= requirements.budget_max * 1.1)  # 10% tolerance
    
    # Get candidates
    candidates = query.limit(50).all()
    
    # Score and rank
    scored_products = []
    for product in candidates:
        score, reasons, tradeoffs = score_product(product, requirements)
        
        image = product.images[0].url if product.images else None
        specs = {s.spec_key: s.value for s in product.specifications}
        
        scored_products.append(RecommendedProduct(
            id=product.id,
            name=product.name,
            slug=product.slug,
            price=float(product.price),
            image=image,
            brand=product.brand.name if product.brand else "Unknown",
            score=score,
            reasons=reasons,
            tradeoffs=tradeoffs,
            specs=specs,
        ))
    
    # Sort by score
    scored_products.sort(key=lambda x: x.score, reverse=True)
    
    # Take top 5
    recommendations = scored_products[:5]
    
    # Track event
    event = UserEvent(
        session_id=session_id,
        event_type="advisor_query",
        query=payload.query,
        filters=requirements.model_dump(),
        result_count=len(candidates),
        selected_product_id=recommendations[0].id if recommendations else None,
    )
    db.add(event)
    
    # Track recommendation
    ai_rec = AIRecommendation(
        session_id=session_id,
        query=payload.query,
        extracted_requirements=requirements.model_dump(),
        recommended_product_ids=[r.id for r in recommendations],
        scores={str(r.id): r.score for r in recommendations},
    )
    db.add(ai_rec)
    
    db.commit()
    
    # Generate message
    if not recommendations:
        message = "No products found matching your requirements. Try adjusting your criteria."
    elif requirements.category and requirements.budget_max:
        message = f"Found {len(recommendations)} {requirements.category} options under ৳{requirements.budget_max:,.0f}"
    elif requirements.category:
        message = f"Here are the best {requirements.category} options for you"
    else:
        message = f"Here are my top recommendations based on your query"
    
    return AdvisorResponse(
        query=payload.query,
        extracted_requirements=requirements,
        recommendations=recommendations,
        total_candidates=len(candidates),
        message=message,
    )


@router.get("/trending")
def get_trending_products(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """Get trending products based on popularity."""
    products = (
        db.query(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.images),
        )
        .filter(Product.is_active == True)
        .order_by(Product.popularity_score.desc())
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "price": float(p.price),
            "image": p.images[0].url if p.images else None,
            "brand": p.brand.name if p.brand else "Unknown",
            "popularity": p.popularity_score,
        }
        for p in products
    ]


@router.get("/similar/{product_id}")
def get_similar_products(
    product_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
):
    """Get products similar to the given product."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    # Find products in same category, excluding current
    similar = (
        db.query(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.images),
        )
        .filter(
            Product.category_id == product.category_id,
            Product.id != product_id,
            Product.is_active == True,
        )
        .order_by(Product.popularity_score.desc())
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "price": float(p.price),
            "image": p.images[0].url if p.images else None,
            "brand": p.brand.name if p.brand else "Unknown",
        }
        for p in similar
    ]


@router.post("/track")
def track_event(
    event_type: str,
    product_id: int | None = None,
    query: str | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Track user interaction for improving recommendations."""
    session_id = request.cookies.get("session_id", "anonymous") if request else "anonymous"
    
    event = UserEvent(
        session_id=session_id,
        event_type=event_type,
        product_id=product_id,
        query=query,
    )
    db.add(event)
    db.commit()
    
    return {"message": "Event tracked"}
