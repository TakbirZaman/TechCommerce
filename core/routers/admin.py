"""
Admin API Routes

Protected endpoints for admin management.
Requires admin authentication (admin@gmail.com / admin123).
"""
import json
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from core.database import get_db, SessionLocal
from core.models.catalog import Brand, Category
from core.models.commerce import Coupon, DeliveryZone, Order, OrderItem, PaymentStatus, OrderStatus
from core.models.specification import (
    Product,
    ProductImage,
    ProductSpecification,
    SpecificationTemplate,
    SpecificationOption,
)
from core.models.user import AuditLog, User, UserRole
from core.services.auth_service import hash_password
from core.services.token_service import verify_token

LOW_STOCK_THRESHOLD = 10


def get_current_admin_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Verify the Bearer token and return the authenticated admin User.

    Raises 401 for missing/invalid/expired tokens or unknown users,
    403 for inactive users or non-admin roles.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(auth_header[7:])
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return user


def require_admin(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin_user),
) -> User:
    """Router-level guard: every /api/v1/admin endpoint requires a valid admin."""
    return user


def log_audit(
    request: Request,
    user: User,
    action: str,
    resource: str,
    resource_id: int | None = None,
    details: dict | None = None,
) -> None:
    """Persist an AuditLog row for a mutating admin action.

    Uses a short-lived dedicated session so the request session (and any ORM
    objects the endpoint still needs to serialize) is not expired/affected.
    Best-effort: logging failures must never break the request.
    """
    try:
        with SessionLocal() as audit_db:
            audit_db.add(AuditLog(
                user_id=user.id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                details=json.dumps(details, default=str) if details else None,
                ip_address=request.client.host if request.client else None,
            ))
            audit_db.commit()
    except Exception:
        logging.getLogger(__name__).warning(
            "audit log write failed for %s/%s", resource, action, exc_info=True)


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],  # enforced on EVERY admin endpoint
)


# Schemas
class BrandCreateRequest(BaseModel):
    name: str
    slug: str
    logo_url: str | None = None
    description: str | None = None


class CategoryCreateRequest(BaseModel):
    name: str
    slug: str
    parent_id: int | None = None
    description: str | None = None
    icon: str | None = None


class ProductCreateRequest(BaseModel):
    name: str
    slug: str
    sku: str
    description: str | None = None
    brand_id: int
    category_id: int
    price: float
    compare_at_price: float | None = None
    stock_quantity: int = 0
    is_active: bool = True
    is_featured: bool = False
    image_url: str | None = None
    specifications: dict = {}


class ProductUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    compare_at_price: float | None = None
    stock_quantity: int | None = None
    is_active: bool | None = None
    is_featured: bool | None = None
    image_url: str | None = None
    specifications: dict | None = None


class SpecTemplateCreateRequest(BaseModel):
    category_id: int
    template: dict


class SpecOptionCreateRequest(BaseModel):
    template_id: int
    spec_key: str
    value: str
    display_name: str | None = None
    sort_order: int = 0


class CouponCreateRequest(BaseModel):
    code: str
    description: str | None = None
    discount_percent: float = 0
    discount_amount: float = 0
    min_order_amount: float = 0
    max_discount_amount: float | None = None
    usage_limit: int | None = None
    expires_at: datetime | None = None


class DeliveryZoneCreateRequest(BaseModel):
    city: str
    area: str | None = None
    charge: float
    estimated_days: int = 3


class OrderStatusUpdateRequest(BaseModel):
    order_status: str


class UserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone: str | None = None
    role: str = "customer"


# Dashboard
@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """Get admin dashboard stats."""
    total_products = db.query(func.count(Product.id)).scalar()
    total_orders = db.query(func.count(Order.id)).scalar()
    total_users = db.query(func.count(User.id)).scalar()
    total_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.payment_status == PaymentStatus.PAID
    ).scalar() or 0
    
    pending_orders = db.query(func.count(Order.id)).filter(
        Order.order_status.in_([OrderStatus.PENDING, OrderStatus.PAYMENT_PENDING])
    ).scalar()
    
    return {
        "total_products": total_products,
        "total_orders": total_orders,
        "total_users": total_users,
        "total_revenue": float(total_revenue),
        "pending_orders": pending_orders,
    }


@router.get("/analytics")
def get_analytics(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Aggregated analytics for the admin dashboard (last 30 days revenue, etc.)."""
    now = datetime.now(UTC)

    # Totals
    total_products = db.query(func.count(Product.id)).scalar() or 0
    active_products = (
        db.query(func.count(Product.id)).filter(Product.is_active == True).scalar() or 0  # noqa: E712
    )
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    revenue_total = (
        db.query(func.sum(Order.total_amount))
        .filter(Order.payment_status == PaymentStatus.PAID)
        .scalar()
        or 0
    )
    pending_orders = (
        db.query(func.count(Order.id))
        .filter(Order.order_status.in_([OrderStatus.PENDING, OrderStatus.PAYMENT_PENDING]))
        .scalar()
        or 0
    )
    low_stock_count = (
        db.query(func.count(Product.id))
        .filter(Product.is_active == True, Product.stock_quantity <= LOW_STOCK_THRESHOLD)  # noqa: E712
        .scalar()
        or 0
    )

    # Revenue by day (last 30 days, paid orders only) - zero-filled
    day_start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    revenue_rows = db.query(
        func.date(Order.created_at).label("day"),
        func.sum(Order.total_amount).label("revenue"),
        func.count(Order.id).label("orders"),
    ).filter(
        Order.payment_status == PaymentStatus.PAID,
        Order.created_at >= day_start,
    ).group_by(func.date(Order.created_at)).all()
    revenue_map = {
        str(row.day): {"revenue": float(row.revenue or 0), "orders": int(row.orders or 0)}
        for row in revenue_rows
    }
    revenue_by_day = []
    for offset in range(29, -1, -1):
        day = (now - timedelta(days=offset)).date().isoformat()
        entry = revenue_map.get(day, {"revenue": 0.0, "orders": 0})
        revenue_by_day.append({"date": day, "revenue": entry["revenue"], "orders": entry["orders"]})

    # Orders grouped by status
    status_rows = db.query(
        Order.order_status, func.count(Order.id)
    ).group_by(Order.order_status).all()
    orders_by_status = [
        {
            "status": s.value if hasattr(s, "value") else str(s),
            "count": int(count),
        }
        for s, count in status_rows
    ]

    # Top products by units sold (order_items snapshots survive product deletion)
    top_rows = db.query(
        OrderItem.product_id.label("product_id"),
        func.max(OrderItem.product_name).label("name"),
        func.sum(OrderItem.quantity).label("units"),
        func.sum(OrderItem.subtotal).label("revenue"),
    ).group_by(OrderItem.product_id).order_by(desc(func.sum(OrderItem.quantity))).limit(10).all()
    top_products = [
        {
            "product_id": row.product_id,
            "name": row.name,
            "units_sold": int(row.units or 0),
            "revenue": float(row.revenue or 0),
        }
        for row in top_rows
    ]

    # Low stock (active products, ascending stock, top 10)
    low_stock_products = (
        db.query(Product)
        .filter(Product.is_active == True, Product.stock_quantity <= LOW_STOCK_THRESHOLD)  # noqa: E712
        .order_by(Product.stock_quantity.asc())
        .limit(10)
        .all()
    )
    low_stock = [
        {
            "product_id": p.id,
            "name": p.name,
            "sku": p.sku,
            "stock_quantity": p.stock_quantity,
        }
        for p in low_stock_products
    ]

    # Recent orders (latest 10)
    recent = db.query(Order).order_by(Order.created_at.desc(), Order.id.desc()).limit(10).all()
    recent_orders = [
        {
            "id": o.id,
            "order_number": o.order_number,
            "customer": o.guest_name,
            "total_amount": float(o.total_amount),
            "payment_status": o.payment_status.value if hasattr(o.payment_status, "value") else str(o.payment_status),
            "order_status": o.order_status.value if hasattr(o.order_status, "value") else str(o.order_status),
            "created_at": (o.created_at.isoformat() + "Z") if o.created_at else None,
        }
        for o in recent
    ]

    return {
        "totals": {
            "products": int(total_products),
            "active_products": int(active_products),
            "users": int(total_users),
            "orders": int(total_orders),
            "revenue_total": float(revenue_total),
            "pending_orders": int(pending_orders),
            "low_stock_count": int(low_stock_count),
        },
        "revenue_by_day": revenue_by_day,
        "orders_by_status": orders_by_status,
        "top_products": top_products,
        "low_stock": low_stock,
        "recent_orders": recent_orders,
    }


# Brand management
@router.get("/brands")
def list_brands(db: Session = Depends(get_db)):
    """List all brands."""
    return db.query(Brand).order_by(Brand.name).all()


@router.post("/brands")
def create_brand(
    payload: BrandCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Create a new brand."""
    existing = db.execute(select(Brand).where(Brand.slug == payload.slug)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Brand slug already exists")
    
    brand = Brand(**payload.model_dump())
    db.add(brand)
    db.commit()
    db.refresh(brand)
    log_audit(request, admin_user, "create", "brand", brand.id, {"name": brand.name, "slug": brand.slug})
    return brand


@router.put("/brands/{brand_id}")
def update_brand(
    brand_id: int,
    payload: BrandCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Update a brand."""
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    for key, value in payload.model_dump().items():
        setattr(brand, key, value)
    
    db.commit()
    log_audit(request, admin_user, "update", "brand", brand.id, {"name": brand.name, "slug": brand.slug})
    return brand


@router.delete("/brands/{brand_id}")
def delete_brand(
    brand_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Delete a brand."""
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    brand.is_active = False
    db.commit()
    log_audit(request, admin_user, "delete", "brand", brand.id, {"name": brand.name, "slug": brand.slug})
    return {"message": "Brand deactivated"}


# Category management
@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """List all categories."""
    return db.query(Category).order_by(Category.name).all()


@router.post("/categories")
def create_category(
    payload: CategoryCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Create a new category."""
    existing = db.execute(select(Category).where(Category.slug == payload.slug)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category slug already exists")
    
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    log_audit(request, admin_user, "create", "category", category.id, {"name": category.name, "slug": category.slug})
    return category


@router.put("/categories/{category_id}")
def update_category(
    category_id: int,
    payload: CategoryCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Update a category."""
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    for key, value in payload.model_dump().items():
        setattr(category, key, value)
    
    db.commit()
    log_audit(request, admin_user, "update", "category", category.id, {"name": category.name, "slug": category.slug})
    return category


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Delete a category."""
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    category.is_active = False
    db.commit()
    log_audit(request, admin_user, "delete", "category", category.id, {"name": category.name, "slug": category.slug})
    return {"message": "Category deactivated"}


# Product management
@router.get("/products")
def list_products(
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """List all products with pagination."""
    query = db.query(Product).options(
        joinedload(Product.brand),
        joinedload(Product.category),
        joinedload(Product.images),
    )
    
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    
    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "products": products,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/products")
def create_product(
    payload: ProductCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Create a new product."""
    existing = db.execute(select(Product).where(Product.sku == payload.sku)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists")
    
    # Create product
    product_data = payload.model_dump(exclude={"specifications", "image_url"})
    product = Product(**product_data)
    db.add(product)
    db.flush()
    
    # Add primary image if provided
    if payload.image_url:
        db.add(ProductImage(
            product_id=product.id,
            url=payload.image_url,
            alt_text=payload.name,
            sort_order=0,
            is_primary=True,
        ))
    
    # Add specifications
    for spec_key, spec_value in payload.specifications.items():
        numeric_value = None
        try:
            numeric_value = float(str(spec_value).replace("GB", "").replace("TB", "").replace(" ", ""))
        except ValueError:
            pass
        
        spec = ProductSpecification(
            product_id=product.id,
            spec_key=spec_key,
            value=str(spec_value),
            numeric_value=numeric_value,
        )
        db.add(spec)
    
    db.commit()
    db.refresh(product)
    log_audit(request, admin_user, "create", "product", product.id, {"name": product.name, "sku": product.sku})
    return product


@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get product details."""
    product = db.execute(
        select(Product)
        .options(
            joinedload(Product.brand),
            joinedload(Product.category),
            joinedload(Product.images),
            joinedload(Product.specifications),
        )
        .where(Product.id == product_id)
    ).scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    return product


@router.put("/products/{product_id}")
def update_product(
    product_id: int,
    payload: ProductUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Update a product."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    # Update basic fields
    for key, value in payload.model_dump(exclude={"specifications", "image_url"}, exclude_unset=True).items():
        setattr(product, key, value)
    
    # Update primary image if provided
    if payload.image_url is not None:
        existing_image = db.query(ProductImage).filter(
            ProductImage.product_id == product_id,
            ProductImage.is_primary == True,
        ).first()
        if existing_image:
            existing_image.url = payload.image_url
        else:
            db.add(ProductImage(
                product_id=product.id,
                url=payload.image_url,
                alt_text=product.name,
                sort_order=0,
                is_primary=True,
            ))
    
    # Update specifications
    if payload.specifications is not None:
        # Delete existing specs
        db.query(ProductSpecification).filter(ProductSpecification.product_id == product_id).delete()
        
        # Add new specs
        for spec_key, spec_value in payload.specifications.items():
            numeric_value = None
            try:
                numeric_value = float(str(spec_value).replace("GB", "").replace("TB", "").replace(" ", ""))
            except ValueError:
                pass
            
            spec = ProductSpecification(
                product_id=product.id,
                spec_key=spec_key,
                value=str(spec_value),
                numeric_value=numeric_value,
            )
            db.add(spec)
    
    db.commit()
    log_audit(request, admin_user, "update", "product", product.id, {"name": product.name, "sku": product.sku})
    return product


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Delete a product (soft delete)."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    product.is_active = False
    db.commit()
    log_audit(request, admin_user, "delete", "product", product.id, {"name": product.name, "sku": product.sku})
    return {"message": "Product deactivated"}


# Image upload
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads" / "products"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/upload-image")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    product_id: int | None = None,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Upload a product image."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")
    
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    
    original_name = file.filename or ""
    ext = original_name.split(".")[-1].lower() if "." in original_name else "jpg"
    allowed_exts = {t.split("/")[-1] for t in ALLOWED_TYPES}
    if ext not in allowed_exts:
        ext = "jpg"
    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    filepath = UPLOAD_DIR / filename
    
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(contents)
    
    url = f"/uploads/products/{filename}"
    log_audit(request, admin_user, "create", "product_image", product_id, {"url": url, "filename": filename})
    
    # If product_id provided, also create ProductImage record
    if product_id:
        product = db.get(Product, product_id)
        if product:
            db.add(ProductImage(
                product_id=product_id,
                url=url,
                alt_text=product.name,
                sort_order=db.query(ProductImage).filter(ProductImage.product_id == product_id).count(),
                is_primary=not db.query(ProductImage).filter(ProductImage.product_id == product_id, ProductImage.is_primary == True).first(),
            ))
            db.commit()
    
    return {"url": url, "filename": filename}


@router.delete("/images/{image_id}")
def delete_image(
    image_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Delete a product image."""
    image = db.get(ProductImage, image_id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    image_url = image.url
    db.delete(image)
    db.commit()
    log_audit(request, admin_user, "delete", "product_image", image_id, {"url": image_url})
    return {"message": "Image deleted"}


# Specification Template management
@router.get("/spec-templates")
def list_spec_templates(db: Session = Depends(get_db)):
    """List all specification templates."""
    return db.query(SpecificationTemplate).all()


@router.post("/spec-templates")
def create_spec_template(
    payload: SpecTemplateCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Create or update specification template for a category."""
    existing = db.execute(
        select(SpecificationTemplate).where(SpecificationTemplate.category_id == payload.category_id)
    ).scalar_one_or_none()
    
    if existing:
        existing.template = payload.template
        db.commit()
        log_audit(request, admin_user, "update", "spec_template", existing.id, {"category_id": existing.category_id, "spec_keys": sorted(payload.template.keys())})
        return existing
    
    template = SpecificationTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    log_audit(request, admin_user, "create", "spec_template", template.id, {"category_id": template.category_id, "spec_keys": sorted(payload.template.keys())})
    return template


@router.get("/spec-options")
def list_spec_options(template_id: int | None = None, db: Session = Depends(get_db)):
    """List specification options."""
    query = db.query(SpecificationOption)
    if template_id:
        query = query.filter(SpecificationOption.template_id == template_id)
    return query.order_by(SpecificationOption.spec_key, SpecificationOption.sort_order).all()


@router.post("/spec-options")
def create_spec_option(
    payload: SpecOptionCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Create a specification option."""
    option = SpecificationOption(**payload.model_dump())
    db.add(option)
    db.commit()
    db.refresh(option)
    log_audit(request, admin_user, "create", "spec_option", option.id, {"template_id": option.template_id, "spec_key": option.spec_key, "value": option.value})
    return option


# Order management
@router.get("/orders")
def list_orders(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """List all orders."""
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.order_status == status)
    
    if search:
        query = query.filter(
            Order.order_number.ilike(f"%{search}%") |
            Order.guest_name.ilike(f"%{search}%") |
            Order.guest_email.ilike(f"%{search}%")
        )
    
    total = query.count()
    orders = query.options(joinedload(Order.items)).order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "orders": orders,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get order details."""
    order = db.execute(
        select(Order).options(joinedload(Order.items)).where(Order.id == order_id)
    ).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.put("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Update order status."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    # Validate status transition
    from core.models.commerce import ALLOWED_ORDER_TRANSITIONS
    current_status = OrderStatus(order.order_status)
    new_status = OrderStatus(payload.order_status)
    
    if new_status not in ALLOWED_ORDER_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {current_status.value} to {new_status.value}",
        )
    
    order.order_status = new_status
    db.commit()
    log_audit(request, admin_user, "update", "order_status", order.id, {"order_number": order.order_number, "from": current_status.value, "to": new_status.value})
    return order


# Coupon management
@router.get("/coupons")
def list_coupons(db: Session = Depends(get_db)):
    """List all coupons."""
    return db.query(Coupon).order_by(Coupon.created_at.desc()).all()


@router.post("/coupons")
def create_coupon(
    payload: CouponCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Create a new coupon."""
    existing = db.execute(select(Coupon).where(Coupon.code == payload.code.upper())).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Coupon code already exists")
    
    coupon = Coupon(code=payload.code.upper(), **payload.model_dump(exclude={"code"}))
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    log_audit(request, admin_user, "create", "coupon", coupon.id, {"code": coupon.code})
    return coupon


@router.put("/coupons/{coupon_id}")
def update_coupon(
    coupon_id: int,
    payload: CouponCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Update a coupon."""
    coupon = db.get(Coupon, coupon_id)
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "code":
            coupon.code = value.upper()
        else:
            setattr(coupon, key, value)
    
    db.commit()
    log_audit(request, admin_user, "update", "coupon", coupon.id, {"code": coupon.code})
    return coupon


@router.delete("/coupons/{coupon_id}")
def delete_coupon(
    coupon_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Delete a coupon."""
    coupon = db.get(Coupon, coupon_id)
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    
    coupon.is_active = False
    db.commit()
    log_audit(request, admin_user, "delete", "coupon", coupon.id, {"code": coupon.code})
    return {"message": "Coupon deactivated"}


# Delivery Zone management
@router.get("/delivery-zones")
def list_delivery_zones(db: Session = Depends(get_db)):
    """List all delivery zones."""
    return db.query(DeliveryZone).order_by(DeliveryZone.city, DeliveryZone.area).all()


@router.post("/delivery-zones")
def create_delivery_zone(
    payload: DeliveryZoneCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Create a new delivery zone."""
    zone = DeliveryZone(**payload.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    log_audit(request, admin_user, "create", "delivery_zone", zone.id, {"city": zone.city, "area": zone.area, "charge": float(zone.charge)})
    return zone


@router.put("/delivery-zones/{zone_id}")
def update_delivery_zone(
    zone_id: int,
    payload: DeliveryZoneCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Update a delivery zone."""
    zone = db.get(DeliveryZone, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(zone, key, value)
    
    db.commit()
    log_audit(request, admin_user, "update", "delivery_zone", zone.id, {"city": zone.city, "area": zone.area, "charge": float(zone.charge)})
    return zone


@router.delete("/delivery-zones/{zone_id}")
def delete_delivery_zone(
    zone_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Delete a delivery zone."""
    zone = db.get(DeliveryZone, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    
    zone.is_active = False
    db.commit()
    log_audit(request, admin_user, "delete", "delivery_zone", zone.id, {"city": zone.city, "area": zone.area})
    return {"message": "Zone deactivated"}


# User management
@router.get("/users")
def list_users(
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """List all users (excluding sensitive fields)."""
    query = db.query(User)
    
    if search:
        query = query.filter(
            User.full_name.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%")
        )
    
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # Filter out sensitive fields
    safe_users = []
    for u in users:
        safe_users.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "phone": u.phone,
            "role": u.role.value if hasattr(u.role, 'value') else u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })
    
    return {
        "users": safe_users,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/users")
def create_user(
    payload: UserCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """Create a new user."""
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=UserRole(payload.role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_audit(request, admin_user, "create", "user", user.id, {"email": user.email, "role": user.role.value if hasattr(user.role, "value") else str(user.role)})
    # Never serialize credential material (password_hash, reset_token, ...)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": (user.created_at.isoformat() + "Z") if user.created_at else None,
    }
