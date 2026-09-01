"""
PC Builder Models

Allows users to build custom PC configurations.
Enforces compatibility rules between components.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class PCBuild(Base):
    """A user's PC build configuration."""
    __tablename__ = "pc_builds"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="My PC Build")
    
    # Calculated totals
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    estimated_power_consumption: Mapped[int] = mapped_column(Integer, default=0)  # Watts
    
    # Compatibility status
    is_compatible: Mapped[bool] = mapped_column(Boolean, default=True)
    compatibility_notes: Mapped[str | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    components: Mapped[list["PCBuildComponent"]] = relationship(back_populates="build", cascade="all, delete-orphan")


class PCBuildComponent(Base):
    """A component in a PC build."""
    __tablename__ = "pc_build_components"

    id: Mapped[int] = mapped_column(primary_key=True)
    build_id: Mapped[int] = mapped_column(ForeignKey("pc_builds.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    component_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Types: cpu, motherboard, ram, storage, gpu, psu, case, cooler, monitor
    
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    build: Mapped["PCBuild"] = relationship(back_populates="components")
    product: Mapped["Product"] = relationship("Product")


class CompatibilityRule(Base):
    """
    Defines compatibility rules between components.
    
    Examples:
    - CPU socket must match motherboard socket
    - RAM type must match motherboard support
    - PSU wattage must exceed total power consumption
    """
    __tablename__ = "compatibility_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Rule definition
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "cpu"
    source_spec: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "socket"
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "motherboard"
    target_spec: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "socket"
    comparison: Mapped[str] = mapped_column(String(20), default="equals")  # equals, min, max, contains
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
