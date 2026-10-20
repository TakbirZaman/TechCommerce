"""
Seed Database - Creates initial data for TechCommerce.

Run: python -m scripts.seed
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal, init_db
from core.models.user import User, UserRole
from core.models.catalog import Brand, Category
from core.models.specification import SpecificationTemplate, Product, ProductImage, ProductSpecification
from core.models.commerce import DeliveryZone
from core.services.auth_service import hash_password


def seed():
    init_db()
    db = SessionLocal()

    try:
        # Create an initial admin only with explicitly configured credentials.
        admin_email = os.getenv("SEED_ADMIN_EMAIL")
        admin_password = os.getenv("SEED_ADMIN_PASSWORD")
        if admin_email and admin_password:
            if not db.query(User).filter(User.email == admin_email).first():
                if len(admin_password) < 12:
                    raise ValueError("SEED_ADMIN_PASSWORD must contain at least 12 characters")
                db.add(User(
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    full_name="Admin",
                    role=UserRole.ADMIN,
                    is_active=True,
                ))
                db.commit()
                print("[OK] Created configured admin user")
            else:
                print("[--] Configured admin user already exists")
        else:
            print("[--] Admin creation skipped; set SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD to enable")

        # ── Brands ──
        brand_data = [
            ("Apple", "apple", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Apple_logo_grey.svg/200px-Apple_logo_grey.svg.png"),
            ("Samsung", "samsung", ""),
            ("Dell", "dell", ""),
            ("Lenovo", "lenovo", ""),
            ("HP", "hp", ""),
            ("ASUS", "asus", ""),
            ("MSI", "msi", ""),
            ("OnePlus", "oneplus", ""),
            ("Xiaomi", "xiaomi", ""),
            ("Sony", "sony", ""),
            ("Logitech", "logitech", ""),
            ("Intel", "intel", ""),
            ("AMD", "amd", ""),
            ("NVIDIA", "nvidia", ""),
            ("Corsair", "corsair", ""),
            ("Gigabyte", "gigabyte", ""),
            ("Kingston", "kingston", ""),
            ("WD", "western-digital", ""),
            ("LG", "lg", ""),
            ("BenQ", "benq", ""),
        ]
        brands = {}
        for name, slug, logo in brand_data:
            existing = db.query(Brand).filter(Brand.slug == slug).first()
            if not existing:
                b = Brand(name=name, slug=slug, logo_url=logo or None)
                db.add(b)
                db.flush()
                brands[slug] = b
            else:
                brands[slug] = existing
        db.commit()
        print(f"[OK] Created {len(brands)} brands")

        # ── Categories ──
        cat_data = [
            ("Laptops", "laptops"),
            ("Smartphones", "phones"),
            ("Monitors", "monitors"),
            ("Processors", "processors"),
            ("Graphics Cards", "graphics-cards"),
            ("RAM", "ram"),
            ("Storage", "storage"),
            ("Motherboards", "motherboards"),
            ("Power Supplies", "power-supplies"),
            ("Cases", "cases"),
            ("Keyboards", "keyboards"),
            ("Mice", "mice"),
            ("Headsets", "headsets"),
            ("Tablets", "tablets"),
            ("Accessories", "accessories"),
        ]
        cats = {}
        for name, slug in cat_data:
            existing = db.query(Category).filter(Category.slug == slug).first()
            if not existing:
                c = Category(name=name, slug=slug, is_active=True)
                db.add(c)
                db.flush()
                cats[slug] = c
            else:
                cats[slug] = existing
        db.commit()
        print(f"[OK] Created {len(cats)} categories")

        # ── Spec Templates ──
        laptop_template = {
            "cpu": {"name": "Processor", "type": "enum", "filterable": True, "comparable": True},
            "ram_gb": {"name": "RAM", "type": "number", "unit": "GB", "filterable": True, "comparable": True},
            "storage_type": {"name": "Storage Type", "type": "enum", "filterable": True, "comparable": True},
            "storage_gb": {"name": "Storage", "type": "number", "unit": "GB", "filterable": True, "comparable": True},
            "display_size": {"name": "Display Size", "type": "number", "unit": "inches", "filterable": True, "comparable": True},
            "display_resolution": {"name": "Resolution", "type": "text", "comparable": True},
            "gpu": {"name": "Graphics", "type": "enum", "filterable": True, "comparable": True},
            "battery_wh": {"name": "Battery", "type": "number", "unit": "Wh", "filterable": True, "comparable": True},
            "weight_kg": {"name": "Weight", "type": "number", "unit": "kg", "filterable": True, "comparable": True},
            "os": {"name": "OS", "type": "enum", "filterable": True},
        }
        phone_template = {
            "chipset": {"name": "Chipset", "type": "enum", "filterable": True, "comparable": True},
            "ram_gb": {"name": "RAM", "type": "number", "unit": "GB", "filterable": True, "comparable": True},
            "storage_gb": {"name": "Storage", "type": "number", "unit": "GB", "filterable": True, "comparable": True},
            "display_size": {"name": "Display Size", "type": "number", "unit": "inches", "filterable": True, "comparable": True},
            "display_resolution": {"name": "Resolution", "type": "text", "comparable": True},
            "refresh_rate": {"name": "Refresh Rate", "type": "number", "unit": "Hz", "filterable": True, "comparable": True},
            "camera_mp": {"name": "Main Camera", "type": "number", "unit": "MP", "filterable": True, "comparable": True},
            "battery_mah": {"name": "Battery", "type": "number", "unit": "mAh", "filterable": True, "comparable": True},
            "os": {"name": "OS", "type": "enum", "filterable": True},
        }
        monitor_template = {
            "display_size": {"name": "Screen Size", "type": "number", "unit": "inches", "filterable": True, "comparable": True},
            "display_resolution": {"name": "Resolution", "type": "text", "filterable": True, "comparable": True},
            "refresh_rate": {"name": "Refresh Rate", "type": "number", "unit": "Hz", "filterable": True, "comparable": True},
            "panel_type": {"name": "Panel Type", "type": "enum", "filterable": True, "comparable": True},
            "response_time": {"name": "Response Time", "type": "number", "unit": "ms", "filterable": True, "comparable": True},
            "hdr": {"name": "HDR", "type": "boolean", "filterable": True, "comparable": True},
        }
        component_template = {
            "socket": {"name": "Socket", "type": "enum", "filterable": True, "comparable": True},
            "tdp": {"name": "TDP", "type": "number", "unit": "W", "filterable": True, "comparable": True},
            "benchmark_score": {"name": "Benchmark", "type": "number", "filterable": True, "comparable": True},
        }

        for slug, tmpl in [
            ("laptops", laptop_template),
            ("phones", phone_template),
            ("monitors", monitor_template),
            ("processors", component_template),
            ("graphics-cards", component_template),
        ]:
            cat = cats.get(slug)
            if cat:
                existing = db.query(SpecificationTemplate).filter(
                    SpecificationTemplate.category_id == cat.id
                ).first()
                if not existing:
                    t = SpecificationTemplate(category_id=cat.id, template=tmpl)
                    db.add(t)
        db.commit()
        print("[OK] Created spec templates for laptops, phones, monitors, processors, GPUs")

        # ── Delivery Zones ──
        zones = [
            ("Dhaka Metro", None, 60, 1),
            ("Dhaka District", None, 100, 2),
            ("Chittagong", None, 120, 3),
            ("Sylhet", None, 130, 3),
            ("Rajshahi", None, 140, 3),
            ("Khulna", None, 130, 3),
            ("Rangpur", None, 150, 4),
            ("Barisal", None, 140, 4),
            ("Mymensingh", None, 130, 3),
        ]
        for city, area, charge, days in zones:
            if not db.query(DeliveryZone).filter(DeliveryZone.city == city).first():
                db.add(DeliveryZone(city=city, area=area, charge=charge, estimated_days=days, is_active=True))
        db.commit()
        print("[OK] Created delivery zones")

        # ── Extended catalog seeding ──
        # Source-linked catalog and local product photos; no fabricated activity.
        from scripts.seed_catalog import seed_catalog
        seed_catalog(db)

        print("\n[DONE] Database seeded successfully!")
        print("   Backend API: http://localhost:8000/docs")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
