"""
PC Builder API Routes

Build custom PC configurations with compatibility checking.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from core.database import get_db
from core.models.pc_builder import PCBuild, PCBuildComponent, CompatibilityRule
from core.models.specification import Product

router = APIRouter(prefix="/api/v1/pc-builder", tags=["pc-builder"])

# Component types for PC building
COMPONENT_TYPES = {
    "cpu": "Processor",
    "motherboard": "Motherboard",
    "ram": "RAM",
    "storage": "Storage",
    "gpu": "Graphics Card",
    "psu": "Power Supply",
    "case": "PC Case",
    "cooler": "CPU Cooler",
    "monitor": "Monitor",
}


# Schemas
class ComponentAddRequest(BaseModel):
    product_id: int
    component_type: str


class ComponentResponse(BaseModel):
    id: int
    product_id: int
    component_type: str
    product_name: str
    product_price: float
    product_image: str | None
    specs: dict

    class Config:
        from_attributes = True


class PCBuildResponse(BaseModel):
    id: int
    name: str
    total_price: float
    estimated_power_consumption: int
    is_compatible: bool
    compatibility_notes: list[str]
    components: list[ComponentResponse]
    component_types: dict

    class Config:
        from_attributes = True


class CompatibilityCheckResponse(BaseModel):
    is_compatible: bool
    issues: list[dict]
    warnings: list[str]


class SuggestedComponentResponse(BaseModel):
    product_id: int
    name: str
    price: float
    image: str | None
    reason: str


# Helper functions
def get_session_id(request: Request) -> str:
    """Get session ID from cookie."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        import secrets
        session_id = secrets.token_urlsafe(32)
    return session_id


def get_or_create_build(db: Session, session_id: str) -> PCBuild:
    """Get or create PC build for session."""
    build = db.execute(
        select(PCBuild).where(PCBuild.session_id == session_id)
    ).scalar_one_or_none()
    
    if build is None:
        build = PCBuild(session_id=session_id, name="My PC Build")
        db.add(build)
        db.flush()
    
    return build


def check_compatibility(db: Session, build: PCBuild) -> CompatibilityCheckResponse:
    """
    Check compatibility of all components in the build.
    
    Rules:
    - CPU socket must match motherboard socket
    - RAM type must match motherboard support
    - PSU wattage must exceed total power consumption
    """
    issues = []
    warnings = []
    
    components = {}
    for comp in build.components:
        product = db.get(Product, comp.product_id)
        if product:
            specs = {s.spec_key: s.value for s in product.specifications}
            components[comp.component_type] = {"product": product, "specs": specs}
    
    # Check CPU <-> Motherboard socket compatibility
    if "cpu" in components and "motherboard" in components:
        cpu_socket = components["cpu"]["specs"].get("socket", "")
        mb_socket = components["motherboard"]["specs"].get("socket", "")
        
        if cpu_socket and mb_socket and cpu_socket != mb_socket:
            issues.append({
                "type": "incompatible",
                "message": f"CPU socket {cpu_socket} is not compatible with motherboard socket {mb_socket}",
                "components": ["cpu", "motherboard"],
            })
    
    # Check RAM type compatibility
    if "ram" in components and "motherboard" in components:
        ram_type = components["ram"]["specs"].get("type", "")
        mb_ram_support = components["motherboard"]["specs"].get("ram_type", "")
        
        if ram_type and mb_ram_support and ram_type not in mb_ram_support:
            issues.append({
                "type": "incompatible",
                "message": f"RAM type {ram_type} is not supported by motherboard (supports {mb_ram_support})",
                "components": ["ram", "motherboard"],
            })
    
    # Check PSU wattage
    if "psu" in components:
        psu_wattage = 0
        try:
            psu_wattage = int(components["psu"]["specs"].get("wattage", "0"))
        except ValueError:
            pass
        
        total_power = 0
        for comp_type in ["cpu", "gpu", "ram", "storage"]:
            if comp_type in components:
                try:
                    tdp = int(components[comp_type]["specs"].get("tdp", "0"))
                    total_power += tdp
                except ValueError:
                    pass
        
        # Add 100W for motherboard and other components
        total_power += 100
        
        if psu_wattage > 0 and total_power > psu_wattage:
            issues.append({
                "type": "insufficient",
                "message": f"PSU {psu_wattage}W is insufficient for estimated {total_power}W consumption",
                "components": ["psu"],
            })
        elif psu_wattage > 0 and total_power > psu_wattage * 0.8:
            warnings.append(f"PSU is running at {int(total_power/psu_wattage*100)}% capacity. Consider a higher wattage PSU.")
    
    # Check if GPU fits in case
    if "gpu" in components and "case" in components:
        gpu_length = components["gpu"]["specs"].get("length_mm", "0")
        case_max_gpu = components["case"]["specs"].get("max_gpu_length_mm", "999")
        
        try:
            if int(gpu_length) > int(case_max_gpu):
                issues.append({
                    "type": "incompatible",
                    "message": f"GPU length {gpu_length}mm exceeds case maximum {case_max_gpu}mm",
                    "components": ["gpu", "case"],
                })
        except ValueError:
            pass
    
    return CompatibilityCheckResponse(
        is_compatible=len(issues) == 0,
        issues=issues,
        warnings=warnings,
    )


def calculate_total_power(db: Session, build: PCBuild) -> int:
    """Calculate estimated total power consumption."""
    total = 100  # Base system power
    
    for comp in build.components:
        product = db.get(Product, comp.product_id)
        if product:
            specs = {s.spec_key: s.value for s in product.specifications}
            try:
                tdp = int(specs.get("tdp", "0"))
                total += tdp * comp.quantity
            except ValueError:
                pass
    
    return total


def get_suggested_components(
    db: Session,
    build: PCBuild,
    component_type: str,
) -> list[SuggestedComponentResponse]:
    """
    Get suggested compatible components based on current build.
    
    Example: If CPU is selected, suggest compatible motherboards.
    """
    suggestions = []
    
    # Get current components' specs
    current_specs = {}
    for comp in build.components:
        product = db.get(Product, comp.product_id)
        if product:
            specs = {s.spec_key: s.value for s in product.specifications}
            current_specs[comp.component_type] = specs
    
    # Get products of the requested type
    products = db.execute(
        select(Product)
        .options(joinedload(Product.images), joinedload(Product.specifications))
        .where(Product.is_active == True)
    ).scalars().all()
    
    for product in products:
        # Check if product matches the component type by category
        category_slug = product.category.slug if product.category else ""
        
        # Simple matching based on category
        type_match = False
        if component_type == "cpu" and "processor" in category_slug.lower():
            type_match = True
        elif component_type == "motherboard" and "motherboard" in category_slug.lower():
            type_match = True
        elif component_type == "ram" and "memory" in category_slug.lower():
            type_match = True
        elif component_type == "storage" and ("ssd" in category_slug.lower() or "hdd" in category_slug.lower()):
            type_match = True
        elif component_type == "gpu" and ("graphics" in category_slug.lower() or "gpu" in category_slug.lower()):
            type_match = True
        elif component_type == "psu" and "power" in category_slug.lower():
            type_match = True
        elif component_type == "case" and "case" in category_slug.lower():
            type_match = True
        elif component_type == "cooler" and "cooler" in category_slug.lower():
            type_match = True
        
        if not type_match:
            continue
        
        # Check compatibility
        specs = {s.spec_key: s.value for s in product.specifications}
        compatible = True
        reason = "Compatible with your build"
        
        # CPU <-> Motherboard socket check
        if component_type == "motherboard" and "cpu" in current_specs:
            cpu_socket = current_specs["cpu"].get("socket", "")
            mb_socket = specs.get("socket", "")
            if cpu_socket and mb_socket and cpu_socket != mb_socket:
                compatible = False
                reason = f"Socket mismatch: needs {cpu_socket}"
        
        # RAM type check
        if component_type == "ram" and "motherboard" in current_specs:
            mb_ram = current_specs["motherboard"].get("ram_type", "")
            ram_type = specs.get("type", "")
            if mb_ram and ram_type and ram_type not in mb_ram:
                compatible = False
                reason = f"RAM type {ram_type} not supported by motherboard"
        
        if compatible:
            image = product.images[0].url if product.images else None
            suggestions.append(SuggestedComponentResponse(
                product_id=product.id,
                name=product.name,
                price=float(product.price),
                image=image,
                reason=reason,
            ))
    
    # Sort by price
    suggestions.sort(key=lambda x: x.price)
    
    return suggestions[:10]  # Return top 10 suggestions


# Endpoints
@router.get("", response_model=PCBuildResponse)
def get_build(request: Request, db: Session = Depends(get_db)):
    """Get current PC build."""
    session_id = get_session_id(request)
    build = get_or_create_build(db, session_id)
    
    components = []
    component_types = {k: None for k in COMPONENT_TYPES.keys()}
    
    for comp in build.components:
        product = db.get(Product, comp.product_id)
        if product:
            specs = {s.spec_key: s.value for s in product.specifications}
            image = product.images[0].url if product.images else None
            
            components.append(ComponentResponse(
                id=comp.id,
                product_id=product.id,
                component_type=comp.component_type,
                product_name=product.name,
                product_price=float(product.price),
                product_image=image,
                specs=specs,
            ))
            
            component_types[comp.component_type] = comp.id
    
    # Calculate totals
    total_price = sum(c.product_price for c in components)
    total_power = calculate_total_power(db, build)
    
    # Check compatibility
    compat = check_compatibility(db, build)
    
    # Update build
    build.total_price = Decimal(str(total_price))
    build.estimated_power_consumption = total_power
    build.is_compatible = compat.is_compatible
    build.compatibility_notes = compat.issues
    db.commit()
    
    return PCBuildResponse(
        id=build.id,
        name=build.name,
        total_price=total_price,
        estimated_power_consumption=total_power,
        is_compatible=compat.is_compatible,
        compatibility_notes=[i["message"] for i in compat.issues] + compat.warnings,
        components=components,
        component_types=component_types,
    )


@router.post("/components", response_model=PCBuildResponse)
def add_component(
    payload: ComponentAddRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Add a component to the build."""
    if payload.component_type not in COMPONENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid component type. Valid types: {list(COMPONENT_TYPES.keys())}",
        )
    
    product = db.get(Product, payload.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    session_id = get_session_id(request)
    build = get_or_create_build(db, session_id)
    
    # Check if component type already exists
    existing = db.execute(
        select(PCBuildComponent).where(
            PCBuildComponent.build_id == build.id,
            PCBuildComponent.component_type == payload.component_type,
        )
    ).scalar_one_or_none()
    
    if existing:
        # Replace existing component
        existing.product_id = payload.product_id
    else:
        # Add new component
        component = PCBuildComponent(
            build_id=build.id,
            product_id=payload.product_id,
            component_type=payload.component_type,
        )
        db.add(component)
    
    db.commit()
    
    return get_build(request, db)


@router.delete("/components/{component_type}", response_model=PCBuildResponse)
def remove_component(
    component_type: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Remove a component from the build."""
    if component_type not in COMPONENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid component type. Valid types: {list(COMPONENT_TYPES.keys())}",
        )
    
    session_id = get_session_id(request)
    build = get_or_create_build(db, session_id)
    
    component = db.execute(
        select(PCBuildComponent).where(
            PCBuildComponent.build_id == build.id,
            PCBuildComponent.component_type == component_type,
        )
    ).scalar_one_or_none()
    
    if component:
        db.delete(component)
        db.commit()
    
    return get_build(request, db)


@router.delete("")
def clear_build(request: Request, db: Session = Depends(get_db)):
    """Clear all components from the build."""
    session_id = get_session_id(request)
    build = get_or_create_build(db, session_id)
    
    for component in build.components:
        db.delete(component)
    
    build.total_price = Decimal("0")
    build.estimated_power_consumption = 0
    build.is_compatible = True
    build.compatibility_notes = None
    
    db.commit()
    
    return {"message": "Build cleared"}


@router.get("/check-compatibility", response_model=CompatibilityCheckResponse)
def check_build_compatibility(request: Request, db: Session = Depends(get_db)):
    """Check compatibility of current build."""
    session_id = get_session_id(request)
    build = get_or_create_build(db, session_id)
    
    return check_compatibility(db, build)


@router.get("/suggestions/{component_type}", response_model=list[SuggestedComponentResponse])
def get_suggestions(
    component_type: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get suggested compatible components."""
    if component_type not in COMPONENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid component type. Valid types: {list(COMPONENT_TYPES.keys())}",
        )
    
    session_id = get_session_id(request)
    build = get_or_create_build(db, session_id)
    
    return get_suggested_components(db, build, component_type)


@router.get("/component-types")
def get_component_types():
    """Get list of valid component types."""
    return COMPONENT_TYPES
