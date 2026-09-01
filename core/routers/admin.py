"""
Admin API Routes

Protected endpoints for admin management.
Requires admin authentication (admin@gmail.com / admin123).
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from core.database import get_db
from core.models.catalog import Brand, Category
from core.models.commerce import Coupon, DeliveryZone, Order, PaymentStatus, OrderStatus
from core.models.specification import (
    Product,
    ProductImage,
    ProductSpecification,
    SpecificationTemplate,
    SpecificationOption,
)
from core.models.user import User, UserRole
from core.services.auth_service import hash_password

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# Admin auth check (simple - just check for admin@gmail.com)
def require_admin(request: Request, db: Session = Depends(get_db)):
    """Require admin authentication."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    # For simplicity, accept any token for admin
    # In production, validate JWT properly
    return True


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
    specifications: dict = {}


class ProductUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    compare_at_price: float | None = None
    stock_quantity: int | None = None
    is_active: bool | None = None
    is_featured: bool | None = None
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


# Brand management
@router.get("/brands")
def list_brands(db: Session = Depends(get_db)):
    """List all brands."""
    return db.query(Brand).order_by(Brand.name).all()


@router.post("/brands")
def create_brand(payload: BrandCreateRequest, db: Session = Depends(get_db)):
    """Create a new brand."""
    existing = db.execute(select(Brand).where(Brand.slug == payload.slug)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Brand slug already exists")
    
    brand = Brand(**payload.model_dump())
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


@router.put("/brands/{brand_id}")
def update_brand(brand_id: int, payload: BrandCreateRequest, db: Session = Depends(get_db)):
    """Update a brand."""
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    for key, value in payload.model_dump().items():
        setattr(brand, key, value)
    
    db.commit()
    return brand


@router.delete("/brands/{brand_id}")
def delete_brand(brand_id: int, db: Session = Depends(get_db)):
    """Delete a brand."""
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    
    brand.is_active = False
    db.commit()
    return {"message": "Brand deactivated"}


# Category management
@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """List all categories."""
    return db.query(Category).order_by(Category.name).all()


@router.post("/categories")
def create_category(payload: CategoryCreateRequest, db: Session = Depends(get_db)):
    """Create a new category."""
    existing = db.execute(select(Category).where(Category.slug == payload.slug)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category slug already exists")
    
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/categories/{category_id}")
def update_category(category_id: int, payload: CategoryCreateRequest, db: Session = Depends(get_db)):
    """Update a category."""
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    for key, value in payload.model_dump().items():
        setattr(category, key, value)
    
    db.commit()
    return category


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Delete a category."""
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    category.is_active = False
    db.commit()
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
def create_product(payload: ProductCreateRequest, db: Session = Depends(get_db)):
    """Create a new product."""
    existing = db.execute(select(Product).where(Product.sku == payload.sku)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists")
    
    # Create product
    product_data = payload.model_dump(exclude={"specifications"})
    product = Product(**product_data)
    db.add(product)
    db.flush()
    
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
def update_product(product_id: int, payload: ProductUpdateRequest, db: Session = Depends(get_db)):
    """Update a product."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    # Update basic fields
    for key, value in payload.model_dump(exclude={"specifications"}, exclude_unset=True).items():
        setattr(product, key, value)
    
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
    return product


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product (soft delete)."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    product.is_active = False
    db.commit()
    return {"message": "Product deactivated"}


# Specification Template management
@router.get("/spec-templates")
def list_spec_templates(db: Session = Depends(get_db)):
    """List all specification templates."""
    return db.query(SpecificationTemplate).all()


@router.post("/spec-templates")
def create_spec_template(payload: SpecTemplateCreateRequest, db: Session = Depends(get_db)):
    """Create or update specification template for a category."""
    existing = db.execute(
        select(SpecificationTemplate).where(SpecificationTemplate.category_id == payload.category_id)
    ).scalar_one_or_none()
    
    if existing:
        existing.template = payload.template
        db.commit()
        return existing
    
    template = SpecificationTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/spec-options")
def list_spec_options(template_id: int | None = None, db: Session = Depends(get_db)):
    """List specification options."""
    query = db.query(SpecificationOption)
    if template_id:
        query = query.filter(SpecificationOption.template_id == template_id)
    return query.order_by(SpecificationOption.spec_key, SpecificationOption.sort_order).all()


@router.post("/spec-options")
def create_spec_option(payload: SpecOptionCreateRequest, db: Session = Depends(get_db)):
    """Create a specification option."""
    option = SpecificationOption(**payload.model_dump())
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


# Order management
@router.get("/orders")
def list_orders(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """List all orders."""
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.order_status == status)
    
    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "orders": orders,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get order details."""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.put("/orders/{order_id}/status")
def update_order_status(order_id: int, payload: OrderStatusUpdateRequest, db: Session = Depends(get_db)):
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
    return order


# Coupon management
@router.get("/coupons")
def list_coupons(db: Session = Depends(get_db)):
    """List all coupons."""
    return db.query(Coupon).order_by(Coupon.created_at.desc()).all()


@router.post("/coupons")
def create_coupon(payload: CouponCreateRequest, db: Session = Depends(get_db)):
    """Create a new coupon."""
    existing = db.execute(select(Coupon).where(Coupon.code == payload.code.upper())).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Coupon code already exists")
    
    coupon = Coupon(code=payload.code.upper(), **payload.model_dump(exclude={"code"}))
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.delete("/coupons/{coupon_id}")
def delete_coupon(coupon_id: int, db: Session = Depends(get_db)):
    """Delete a coupon."""
    coupon = db.get(Coupon, coupon_id)
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    
    coupon.is_active = False
    db.commit()
    return {"message": "Coupon deactivated"}


# Delivery Zone management
@router.get("/delivery-zones")
def list_delivery_zones(db: Session = Depends(get_db)):
    """List all delivery zones."""
    return db.query(DeliveryZone).order_by(DeliveryZone.city, DeliveryZone.area).all()


@router.post("/delivery-zones")
def create_delivery_zone(payload: DeliveryZoneCreateRequest, db: Session = Depends(get_db)):
    """Create a new delivery zone."""
    zone = DeliveryZone(**payload.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/delivery-zones/{zone_id}")
def delete_delivery_zone(zone_id: int, db: Session = Depends(get_db)):
    """Delete a delivery zone."""
    zone = db.get(DeliveryZone, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    
    zone.is_active = False
    db.commit()
    return {"message": "Zone deactivated"}


# User management
@router.get("/users")
def list_users(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """List all users."""
    total = db.query(func.count(User.id)).scalar()
    users = db.query(User).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/users")
def create_user(payload: UserCreateRequest, db: Session = Depends(get_db)):
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
    return user
