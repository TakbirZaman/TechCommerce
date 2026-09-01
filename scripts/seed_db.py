"""
Seed script for populating the database with sample data.

Usage:
    python -m scripts.seed_db
    
This script creates sample data for development and testing.
Run against a real PostgreSQL database to populate it with:
- Brands (Apple, Samsung, Dell, etc.)
- Categories (Smartphones, Laptops, Monitors, etc.)
- Products with specifications
- Sample users
- Sample reviews
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.stubs import Base, Brand, Category, Product, User, ProductStatus

# Sample data
BRANDS = [
    {"name": "Apple", "slug": "apple", "description": "Premium electronics"},
    {"name": "Samsung", "slug": "samsung", "description": "Leading electronics manufacturer"},
    {"name": "Dell", "slug": "dell", "description": "Business and consumer laptops"},
    {"name": "Lenovo", "slug": "lenovo", "description": "ThinkPad and consumer laptops"},
    {"name": "HP", "slug": "hp", "description": "Hewlett-Packard laptops and printers"},
    {"name": "Asus", "slug": "asus", "description": "Republic of Gamers and consumer laptops"},
    {"name": "Xiaomi", "slug": "xiaomi", "description": "Value electronics"},
    {"name": "OnePlus", "slug": "oneplus", "description": "Flagship killer smartphones"},
]

CATEGORIES = [
    {"name": "Smartphones", "slug": "smartphones", "filterable_spec_schema": {"ram_gb": {"type": "numeric"}, "storage_gb": {"type": "numeric"}, "screen_size": {"type": "numeric"}}},
    {"name": "Laptops", "slug": "laptops", "filterable_spec_schema": {"ram_gb": {"type": "numeric"}, "cpu": {"type": "enum"}, "gpu": {"type": "enum"}, "screen_size": {"type": "numeric"}}},
    {"name": "Monitors", "slug": "monitors", "filterable_spec_schema": {"screen_size": {"type": "numeric"}, "resolution": {"type": "enum"}, "refresh_rate": {"type": "numeric"}}},
    {"name": "Tablets", "slug": "tablets", "filterable_spec_schema": {"ram_gb": {"type": "numeric"}, "storage_gb": {"type": "numeric"}, "screen_size": {"type": "numeric"}}},
    {"name": "Accessories", "slug": "accessories", "filterable_spec_schema": {}},
]

PRODUCTS = [
    # Smartphones
    {"name": "iPhone 15 Pro Max", "slug": "iphone-15-pro-max", "sku": "APL-IP15PM-256", "price": 159999, "brand": "apple", "category": "smartphones", "specs": {"ram_gb": 8, "storage_gb": 256, "screen_size": 6.7, "camera_mp": 48}},
    {"name": "Samsung Galaxy S24 Ultra", "slug": "samsung-galaxy-s24-ultra", "sku": "SAM-S24U-256", "price": 139999, "brand": "samsung", "category": "smartphones", "specs": {"ram_gb": 12, "storage_gb": 256, "screen_size": 6.8, "camera_mp": 200}},
    {"name": "OnePlus 12", "slug": "oneplus-12", "sku": "OP-12-256", "price": 69999, "brand": "oneplus", "category": "smartphones", "specs": {"ram_gb": 16, "storage_gb": 256, "screen_size": 6.82, "camera_mp": 50}},
    {"name": "Xiaomi 14", "slug": "xiaomi-14", "sku": "XI-14-256", "price": 59999, "brand": "xiaomi", "category": "smartphones", "specs": {"ram_gb": 12, "storage_gb": 256, "screen_size": 6.36, "camera_mp": 50}},
    
    # Laptops
    {"name": "MacBook Pro 16 M3 Max", "slug": "macbook-pro-16-m3-max", "sku": "APL-MBP16-M3M", "price": 349999, "brand": "apple", "category": "laptops", "specs": {"ram_gb": 36, "cpu": "Apple M3 Max", "gpu": "M3 Max 40-core", "screen_size": 16.2, "storage_gb": 1000}},
    {"name": "Dell XPS 15", "slug": "dell-xps-15", "sku": "DEL-XPS15-I7", "price": 189999, "brand": "dell", "category": "laptops", "specs": {"ram_gb": 16, "cpu": "Intel Core i7-13700H", "gpu": "RTX 4060", "screen_size": 15.6, "storage_gb": 512}},
    {"name": "Lenovo ThinkPad X1 Carbon", "slug": "lenovo-thinkpad-x1-carbon", "sku": "LEN-X1C-I7", "price": 159999, "brand": "lenovo", "category": "laptops", "specs": {"ram_gb": 16, "cpu": "Intel Core i7-1365U", "gpu": "Intel Iris Xe", "screen_size": 14, "storage_gb": 512}},
    {"name": "HP Spectre x360", "slug": "hp-spectre-x360", "sku": "HP-SPEC-I7", "price": 139999, "brand": "hp", "category": "laptops", "specs": {"ram_gb": 16, "cpu": "Intel Core i7-1355U", "gpu": "Intel Iris Xe", "screen_size": 14, "storage_gb": 512}},
    {"name": "Asus ROG Zephyrus G16", "slug": "asus-rog-zephyrus-g16", "sku": "ASUS-ROG-G16", "price": 219999, "brand": "asus", "category": "laptops", "specs": {"ram_gb": 32, "cpu": "Intel Core i9-14900HX", "gpu": "RTX 4080", "screen_size": 16, "storage_gb": 1000}},
    
    # Monitors
    {"name": "Dell UltraSharp 27 4K", "slug": "dell-ultrasharp-27-4k", "sku": "DEL-US27-4K", "price": 79999, "brand": "dell", "category": "monitors", "specs": {"screen_size": 27, "resolution": "3840x2160", "refresh_rate": 60}},
    {"name": "Samsung Odyssey G9 49", "slug": "samsung-odyssey-g9-49", "sku": "SAM-G9-49", "price": 149999, "brand": "samsung", "category": "monitors", "specs": {"screen_size": 49, "resolution": "5120x1440", "refresh_rate": 240}},
]

USERS = [
    {"email": "admin@techcommerce.com", "full_name": "Admin User", "is_admin": True, "role": "admin"},
    {"email": "user@example.com", "full_name": "Test User", "is_admin": False, "role": "customer"},
]


def seed_database():
    """Populate the database with sample data."""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Seed brands
        brand_map = {}
        for brand_data in BRANDS:
            existing = db.query(Brand).filter(Brand.slug == brand_data["slug"]).first()
            if not existing:
                brand = Brand(**brand_data)
                db.add(brand)
                db.flush()
                brand_map[brand_data["slug"]] = brand.id
            else:
                brand_map[brand_data["slug"]] = existing.id
        
        # Seed categories
        category_map = {}
        for cat_data in CATEGORIES:
            existing = db.query(Category).filter(Category.slug == cat_data["slug"]).first()
            if not existing:
                category = Category(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    filterable_spec_schema=cat_data.get("filterable_spec_schema", {}),
                )
                db.add(category)
                db.flush()
                category_map[cat_data["slug"]] = category.id
            else:
                category_map[cat_data["slug"]] = existing.id
        
        # Seed products
        for prod_data in PRODUCTS:
            existing = db.query(Product).filter(Product.sku == prod_data["sku"]).first()
            if not existing:
                product = Product(
                    name=prod_data["name"],
                    slug=prod_data["slug"],
                    sku=prod_data["sku"],
                    description=f"High-quality {prod_data['name']} with excellent performance.",
                    price=Decimal(str(prod_data["price"])),
                    brand_id=brand_map[prod_data["brand"]],
                    category_id=category_map[prod_data["category"]],
                    specifications=prod_data.get("specs", {}),
                    stock_quantity=50,
                    status=ProductStatus.AVAILABLE,
                    is_active=True,
                    is_visible=True,
                    is_purchasable=True,
                )
                db.add(product)
        
        # Seed users
        for user_data in USERS:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing:
                user = User(**user_data)
                db.add(user)
        
        db.commit()
        print("Database seeded successfully!")
        print(f"  - {len(BRANDS)} brands")
        print(f"  - {len(CATEGORIES)} categories")
        print(f"  - {len(PRODUCTS)} products")
        print(f"  - {len(USERS)} users")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
