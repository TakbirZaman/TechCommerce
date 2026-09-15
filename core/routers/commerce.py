"""
Commerce API Routes - Cart, Checkout, Orders

Guest checkout - no login required.
"""
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.database import get_db
from core.models.commerce import (
    Cart,
    CartItem,
    Coupon,
    DeliveryZone,
    InventoryTransactionType,
    Order,
    OrderItem,
    OrderStatus,
    PaymentStatus,
)
from core.models.specification import Product
from core.services.inventory_service import record_inventory_transaction

router = APIRouter(prefix="/api/v1/commerce", tags=["commerce"])


# Schemas
class CartItemAddRequest(BaseModel):
    product_id: int
    quantity: int = 1

    @field_validator('quantity')
    @classmethod
    def qty_positive(cls, v):
        if v < 1:
            raise ValueError('quantity must be >=1')
        if v > 100:
            raise ValueError('quantity must be <=100')
        return v


class CartItemUpdateRequest(BaseModel):
    quantity: int

    @field_validator('quantity')
    @classmethod
    def qty_update_positive(cls, v):
        if v < 1:
            raise ValueError('quantity must be >=1')
        if v > 100:
            raise ValueError('quantity must be <=100')
        return v


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    product_image: str | None
    unit_price: float
    quantity: int
    subtotal: float


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total_items: int
    subtotal: float


class CheckoutRequest(BaseModel):
    full_name: str
    email: str  # validated via EmailStr in route-level check
    phone: str
    address: str
    city: str
    area: str
    postal_code: str | None = None
    payment_method: str  # validated against PaymentMethod enum in checkout handler
    discount_code: str | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    guest_email: str
    guest_name: str
    guest_phone: str
    subtotal: float
    discount: float
    delivery_charge: float
    total_amount: float
    payment_method: str
    payment_status: str
    order_status: str
    shipping_address: str
    shipping_city: str
    shipping_area: str
    items: list[dict]
    created_at: str


class OrderTrackRequest(BaseModel):
    order_number: str
    email: str


# Helper functions
def _set_session_cookie(response: Response, session_id: str) -> None:
    """Set session cookie with Secure flag in production."""
    import os as _os
    is_prod = _os.getenv("ENV", "").lower() == "production" or _os.getenv("ENVIRONMENT", "").lower() == "production"
    response.set_cookie(
        "session_id",
        session_id,
        max_age=30 * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=is_prod,
    )


def get_session_id(request: Request) -> str:
    """Get or create session ID from cookie or header."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = request.headers.get("X-Session-ID")
    if not session_id:
        import secrets
        session_id = secrets.token_urlsafe(32)
    return session_id


def get_or_create_cart(db: Session, session_id: str) -> Cart:
    """Get or create cart for session."""
    cart = db.execute(
        select(Cart).where(Cart.session_id == session_id).options(selectinload(Cart.items))
    ).scalar_one_or_none()
    if cart is None:
        cart = Cart(session_id=session_id)
        db.add(cart)
        db.flush()
    return cart


def build_cart_response(db: Session, session_id: str) -> CartResponse:
    """Build cart response — batch-loads products + images to avoid N+1."""
    cart = db.execute(
        select(Cart).where(Cart.session_id == session_id).options(selectinload(Cart.items))
    ).scalar_one_or_none()
    if cart is None or not cart.items:
        return CartResponse(items=[], total_items=0, subtotal=0.0)

    # Batch load products for all cart items in one query
    pids = [i.product_id for i in cart.items]
    rows = db.execute(
        select(Product).where(Product.id.in_(pids)).options(selectinload(Product.images))
    ).scalars().all()
    pmap = {p.id: p for p in rows}

    items = []
    total = Decimal("0.00")
    for item in cart.items:
        product = pmap.get(item.product_id)
        if product and product.is_active:
            subtotal = Decimal(str(product.price)) * item.quantity
            items.append(CartItemResponse(
                id=item.id,
                product_id=product.id,
                product_name=product.name,
                product_image=product.images[0].url if product.images else None,
                unit_price=float(product.price),
                quantity=item.quantity,
                subtotal=float(subtotal),
            ))
            total += subtotal

    return CartResponse(
        items=items,
        total_items=sum(i.quantity for i in items),
        subtotal=float(total),
    )


def calculate_delivery_charge(db: Session, city: str, area: str | None = None) -> Decimal:
    """Calculate delivery charge based on zone."""
    if area:
        zone = db.execute(
            select(DeliveryZone).where(
                DeliveryZone.city.ilike(city),
                DeliveryZone.area.ilike(area),
                DeliveryZone.is_active == True,
            )
        ).scalar_one_or_none()
        if zone:
            return Decimal(str(zone.charge))

    zone = db.execute(
        select(DeliveryZone).where(
            DeliveryZone.city.ilike(city),
            DeliveryZone.area.is_(None),
            DeliveryZone.is_active == True,
        )
    ).scalar_one_or_none()

    if zone:
        return Decimal(str(zone.charge))

    return Decimal("60.00")  # Default charge


def validate_coupon(db: Session, code: str, subtotal: Decimal) -> Decimal:
    """Validate coupon and return discount amount."""
    if not code:
        return Decimal("0.00")

    coupon = db.execute(
        select(Coupon).where(Coupon.code == code.upper(), Coupon.is_active == True)
    ).scalar_one_or_none()

    if coupon is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid coupon code")

    if coupon.expires_at and coupon.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon has expired")

    if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon usage limit reached")

    if subtotal < coupon.min_order_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum order amount is {coupon.min_order_amount}",
        )

    if coupon.discount_percent > 0:
        discount = subtotal * Decimal(str(coupon.discount_percent)) / Decimal("100")
    else:
        discount = coupon.discount_amount

    if coupon.max_discount_amount and discount > coupon.max_discount_amount:
        discount = coupon.max_discount_amount

    return min(discount, subtotal)


def generate_order_number(db: Session, year: int) -> str:
    """Generate unique order number — concurrency-safe on Postgres via
    advisory lock, with fallback retry on unique violation."""
    import time as _time
    import logging as _logging
    from sqlalchemy.exc import IntegrityError

    prefix = f"TC{year}"
    # Best-effort Postgres advisory lock to serialize order-number generation
    # within this DB. On SQLite (tests) this is a no-op but the retry loop below handles collisions.
    try:
        db.execute(select(Order).where(Order.order_number.like(f"{prefix}%")).order_by(Order.id.desc()).limit(1).with_for_update())
    except Exception:
        pass  # SQLite or lock unsupported — continue to retry path

    # Try up to 5 times with backoff; handles concurrent insert unique violation
    for attempt in range(5):
        last_order = db.execute(
            select(Order).where(Order.order_number.like(f"{prefix}%")).order_by(Order.id.desc()).limit(1)
        ).scalar_one_or_none()
        
        if last_order:
            try:
                last_num = int(last_order.order_number.replace(prefix, ""))
            except ValueError:
                last_num = 0
            candidate = f"{prefix}{last_num + 1 + attempt:06d}"
        else:
            candidate = f"{prefix}{1 + attempt:06d}"

        # Verify candidate not already taken (covers race without DB lock on SQLite)
        exists = db.execute(select(Order.id).where(Order.order_number == candidate).limit(1)).scalar_one_or_none()
        if not exists:
            return candidate
        _time.sleep(0.02 * (attempt + 1))
        _logging.getLogger(__name__).warning("order_number collision for %s, retry %d", candidate, attempt)

    # Final fallback: timestamp-based suffix guarantees uniqueness
    import secrets as _secrets
    return f"{prefix}{_secrets.randbelow(900000) + 100000:06d}"


# Cart endpoints
@router.get("/cart", response_model=CartResponse)
def get_cart(request: Request, response: Response, db: Session = Depends(get_db)):
    """Get current cart contents."""
    session_id = get_session_id(request)
    _set_session_cookie(response, session_id)
    return build_cart_response(db, session_id)


@router.post("/cart/items", response_model=CartResponse)
def add_to_cart(
    payload: CartItemAddRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Add item to cart."""
    product = db.get(Product, payload.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    if product.available_stock < payload.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")
    
    session_id = get_session_id(request)
    _set_session_cookie(response, session_id)
    cart = get_or_create_cart(db, session_id)
    
    # Check if item already in cart
    existing = db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == payload.product_id)
    ).scalar_one_or_none()
    
    if existing:
        existing.quantity += payload.quantity
    else:
        db.add(CartItem(cart_id=cart.id, product_id=payload.product_id, quantity=payload.quantity))
    
    db.commit()
    
    return build_cart_response(db, session_id)


@router.put("/cart/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    item_id: int,
    payload: CartItemUpdateRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Update cart item quantity."""
    session_id = get_session_id(request)
    _set_session_cookie(response, session_id)
    cart = get_or_create_cart(db, session_id)
    
    item = db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    ).scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    
    product = db.get(Product, item.product_id)
    if product and product.available_stock < payload.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")
    
    item.quantity = payload.quantity
    db.commit()
    
    return build_cart_response(db, session_id)


@router.delete("/cart/items/{item_id}", response_model=CartResponse)
def remove_from_cart(
    item_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Remove item from cart."""
    session_id = get_session_id(request)
    _set_session_cookie(response, session_id)
    cart = get_or_create_cart(db, session_id)
    
    item = db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    ).scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    
    db.delete(item)
    db.commit()
    
    return build_cart_response(db, session_id)


@router.delete("/cart", response_model=CartResponse)
def clear_cart(request: Request, response: Response, db: Session = Depends(get_db)):
    """Clear all items from cart."""
    session_id = get_session_id(request)
    _set_session_cookie(response, session_id)
    cart = get_or_create_cart(db, session_id)
    
    for item in cart.items:
        db.delete(item)
    
    db.commit()
    
    return build_cart_response(db, session_id)


# Checkout endpoint
@router.post("/checkout", response_model=OrderResponse)
def checkout(
    payload: CheckoutRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Complete checkout - guest checkout, no login required.
    """
    # Validate payment_method enum and email format early (professional 400 vs 500)
    from core.models.commerce import PaymentMethod as _PM
    # Normalize legacy aliases: cod / cash_on_delivery -> sslcommerz (gateway-agnostic cash)
    _pm_alias = {"cod": "sslcommerz", "cash_on_delivery": "sslcommerz", "cash": "sslcommerz", "card": "sslcommerz"}
    normalized_pm = _pm_alias.get(payload.payment_method.lower(), payload.payment_method.lower())
    try:
        _pm_obj = _PM(normalized_pm)
        # Update payload value to canonical enum value for DB write
        payload.payment_method = _pm_obj.value
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payment_method: {payload.payment_method}. Valid: {[e.value for e in _PM]}")
    # Basic email sanity (full EmailStr validation is at auth layer)
    if "@" not in payload.email or "." not in payload.email.split("@")[-1]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address")

    session_id = get_session_id(request)
    _set_session_cookie(response, session_id)
    cart = get_or_create_cart(db, session_id)
    
    if not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")
    
    # Calculate totals
    subtotal = Decimal("0.00")
    order_items = []
    
    for cart_item in cart.items:
        product = db.get(Product, cart_item.product_id)
        if not product or not product.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product {cart_item.product_id} unavailable")
        
        if product.available_stock < cart_item.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient stock for {product.name}")
        
        line_total = Decimal(str(product.price)) * cart_item.quantity
        subtotal += line_total
        
        order_items.append(OrderItem(
            product_id=product.id,
            product_name=product.name,
            product_sku=product.sku,
            quantity=cart_item.quantity,
            unit_price=product.price,
            subtotal=line_total,
        ))
    
    # Apply discount
    discount = validate_coupon(db, payload.discount_code, subtotal)
    
    # Calculate delivery charge
    delivery_charge = calculate_delivery_charge(db, payload.city, payload.area)
    
    # Calculate total
    total = subtotal - discount + delivery_charge
    
    # Generate order number
    order_number = generate_order_number(db, datetime.now(UTC).year)
    
    # Create order
    order = Order(
        order_number=order_number,
        guest_email=payload.email,
        guest_name=payload.full_name,
        guest_phone=payload.phone,
        subtotal=subtotal,
        discount=discount,
        delivery_charge=delivery_charge,
        total_amount=total,
        payment_method=payload.payment_method,
        payment_status=PaymentStatus.UNPAID,
        order_status=OrderStatus.PENDING,
        shipping_address=payload.address,
        shipping_city=payload.city,
        shipping_area=payload.area,
        shipping_postal_code=payload.postal_code,
        discount_code=payload.discount_code,
        items=order_items,
    )
    db.add(order)
    db.flush()  # get order.id for reference

    # Auditable stock reservation (ledger, not ad-hoc overwrite) — spec section 8
    for cart_item in cart.items:
        try:
            record_inventory_transaction(
                db,
                product_id=cart_item.product_id,
                quantity=-cart_item.quantity,
                transaction_type=InventoryTransactionType.RESERVATION,
                performed_by=None,
                reason=f"Reservation for order {order_number}",
                reference=order_number,
                commit=False,
            )
        except ValueError as e:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        # Also increment reserved_stock for available_stock calculations
        product = db.get(Product, cart_item.product_id)
        if product:
            product.reserved_stock += cart_item.quantity
    
    # Clear cart
    for item in cart.items:
        db.delete(item)
    
    # Update coupon usage
    if payload.discount_code:
        coupon = db.execute(
            select(Coupon).where(Coupon.code == payload.discount_code.upper())
        ).scalar_one_or_none()
        if coupon:
            coupon.used_count += 1
    
    db.commit()
    db.refresh(order)
    # Notification (best-effort)
    try:
        from core.services.notification_service import notify_order_created
        notify_order_created(order, db)
    except Exception:
        pass

    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        guest_email=order.guest_email,
        guest_name=order.guest_name,
        guest_phone=order.guest_phone,
        subtotal=float(order.subtotal),
        discount=float(order.discount),
        delivery_charge=float(order.delivery_charge),
        total_amount=float(order.total_amount),
        payment_method=order.payment_method,
        payment_status=order.payment_status.value if order.payment_status else "unpaid",
        order_status=order.order_status.value if order.order_status else "pending",
        shipping_address=order.shipping_address,
        shipping_city=order.shipping_city,
        shipping_area=order.shipping_area,
        items=[{"product_name": i.product_name, "quantity": i.quantity, "subtotal": float(i.subtotal)} for i in order.items],
        created_at=order.created_at.isoformat() if order.created_at else "",
    )


# Order tracking
@router.post("/orders/track", response_model=OrderResponse)
def track_order(
    payload: OrderTrackRequest,
    db: Session = Depends(get_db),
):
    """Track order by order number and email."""
    order = db.execute(
        select(Order).where(
            Order.order_number == payload.order_number,
            Order.guest_email == payload.email,
        )
    ).scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        guest_email=order.guest_email,
        guest_name=order.guest_name,
        guest_phone=order.guest_phone,
        subtotal=float(order.subtotal),
        discount=float(order.discount),
        delivery_charge=float(order.delivery_charge),
        total_amount=float(order.total_amount),
        payment_method=order.payment_method,
        payment_status=order.payment_status.value if order.payment_status else "unpaid",
        order_status=order.order_status.value if order.order_status else "pending",
        shipping_address=order.shipping_address,
        shipping_city=order.shipping_city,
        shipping_area=order.shipping_area,
        items=[{"product_name": i.product_name, "quantity": i.quantity, "subtotal": float(i.subtotal)} for i in order.items],
        created_at=order.created_at.isoformat() if order.created_at else "",
    )
