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
        # ── Admin User ──
        if not db.query(User).filter(User.email == "admin@gmail.com").first():
            admin = User(
                email="admin@gmail.com",
                password_hash=hash_password("admin123"),
                full_name="Admin",
                phone="01700000000",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print("[OK] Created admin user (admin@gmail.com / admin123)")
        else:
            print("[--] Admin user already exists")

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

        # ── Sample Products ──
        products_data = [
            # Laptops
            {
                "name": "MacBook Air M3 15-inch",
                "slug": "macbook-air-m3-15",
                "sku": "APL-MBA-M3-15",
                "brand": "apple",
                "category": "laptops",
                "price": 159900,
                "compare_at_price": 179900,
                "description": "Supercharged by the M3 chip. With a stunning 15.3-inch Liquid Retina display, up to 18 hours of battery life, and a fanless design.",
                "stock": 25,
                "specs": {
                    "cpu": "Apple M3",
                    "ram_gb": "16",
                    "storage_type": "SSD",
                    "storage_gb": "512",
                    "display_size": "15.3",
                    "display_resolution": "2880 x 1864",
                    "gpu": "Apple M3 10-core",
                    "battery_wh": "66.5",
                    "weight_kg": "1.51",
                    "os": "macOS",
                },
            },
            {
                "name": "Dell XPS 15 9530",
                "slug": "dell-xps-15-9530",
                "sku": "DEL-XPS15-9530",
                "brand": "dell",
                "category": "laptops",
                "price": 189000,
                "compare_at_price": 219000,
                "description": "13th Gen Intel Core i7 processor, NVIDIA GeForce RTX 4060, 15.6-inch OLED 3.5K display.",
                "stock": 15,
                "specs": {
                    "cpu": "Intel Core i7-13700H",
                    "ram_gb": "16",
                    "storage_type": "SSD",
                    "storage_gb": "512",
                    "display_size": "15.6",
                    "display_resolution": "3456 x 2160",
                    "gpu": "NVIDIA RTX 4060",
                    "battery_wh": "86",
                    "weight_kg": "1.86",
                    "os": "Windows 11",
                },
            },
            {
                "name": "Lenovo ThinkPad X1 Carbon Gen 11",
                "slug": "lenovo-thinkpad-x1-carbon-gen11",
                "sku": "LEN-X1C-G11",
                "brand": "lenovo",
                "category": "laptops",
                "price": 165000,
                "description": "13th Gen Intel Core i7, 14-inch 2.8K OLED display, enterprise-grade security and manageability.",
                "stock": 20,
                "specs": {
                    "cpu": "Intel Core i7-1365U",
                    "ram_gb": "16",
                    "storage_type": "SSD",
                    "storage_gb": "512",
                    "display_size": "14",
                    "display_resolution": "2880 x 1800",
                    "gpu": "Intel Iris Xe",
                    "battery_wh": "57",
                    "weight_kg": "1.12",
                    "os": "Windows 11",
                },
            },
            {
                "name": "ASUS ROG Zephyrus G16",
                "slug": "asus-rog-zephyrus-g16",
                "sku": "ASU-ROG-G16",
                "brand": "asus",
                "category": "laptops",
                "price": 210000,
                "compare_at_price": 239000,
                "description": "Intel Core Ultra 9 185H, NVIDIA RTX 4070, 16-inch ROG Nebula OLED display, 240Hz.",
                "stock": 10,
                "specs": {
                    "cpu": "Intel Core Ultra 9 185H",
                    "ram_gb": "32",
                    "storage_type": "SSD",
                    "storage_gb": "1024",
                    "display_size": "16",
                    "display_resolution": "2560 x 1600",
                    "gpu": "NVIDIA RTX 4070",
                    "battery_wh": "90",
                    "weight_kg": "1.85",
                    "os": "Windows 11",
                },
            },
            # Phones
            {
                "name": "Samsung Galaxy S24 Ultra",
                "slug": "samsung-galaxy-s24-ultra",
                "sku": "SAM-S24U-256",
                "brand": "samsung",
                "category": "phones",
                "price": 139999,
                "compare_at_price": 159999,
                "description": "6.8-inch Dynamic AMOLED 2X, Snapdragon 8 Gen 3, 200MP camera, S Pen, Galaxy AI.",
                "stock": 30,
                "specs": {
                    "chipset": "Snapdragon 8 Gen 3",
                    "ram_gb": "12",
                    "storage_gb": "256",
                    "display_size": "6.8",
                    "display_resolution": "3120 x 1440",
                    "refresh_rate": "120",
                    "camera_mp": "200",
                    "battery_mah": "5000",
                    "os": "Android 14",
                },
            },
            {
                "name": "iPhone 15 Pro Max",
                "slug": "iphone-15-pro-max",
                "sku": "APL-15PM-256",
                "brand": "apple",
                "category": "phones",
                "price": 159900,
                "description": "A17 Pro chip, 48MP camera system, titanium design, Action button, USB-C.",
                "stock": 20,
                "specs": {
                    "chipset": "Apple A17 Pro",
                    "ram_gb": "8",
                    "storage_gb": "256",
                    "display_size": "6.7",
                    "display_resolution": "2796 x 1290",
                    "refresh_rate": "120",
                    "camera_mp": "48",
                    "battery_mah": "4441",
                    "os": "iOS 17",
                },
            },
            {
                "name": "OnePlus 12",
                "slug": "oneplus-12",
                "sku": "ONE-12-256",
                "brand": "oneplus",
                "category": "phones",
                "price": 69999,
                "compare_at_price": 79999,
                "description": "Snapdragon 8 Gen 3, 50MP Sony LYT-808, 100W SUPERVOOC, 2K 120Hz ProXDR display.",
                "stock": 40,
                "specs": {
                    "chipset": "Snapdragon 8 Gen 3",
                    "ram_gb": "12",
                    "storage_gb": "256",
                    "display_size": "6.82",
                    "display_resolution": "3168 x 1440",
                    "refresh_rate": "120",
                    "camera_mp": "50",
                    "battery_mah": "5400",
                    "os": "Android 14",
                },
            },
            {
                "name": "Xiaomi 14",
                "slug": "xiaomi-14",
                "sku": "XIA-14-256",
                "brand": "xiaomi",
                "category": "phones",
                "price": 79999,
                "description": "Leica光学镜头, Snapdragon 8 Gen 3, 6.36-inch 1.5K LTPO AMOLED.",
                "stock": 25,
                "specs": {
                    "chipset": "Snapdragon 8 Gen 3",
                    "ram_gb": "12",
                    "storage_gb": "256",
                    "display_size": "6.36",
                    "display_resolution": "2670 x 1200",
                    "refresh_rate": "120",
                    "camera_mp": "50",
                    "battery_mah": "4610",
                    "os": "Android 14",
                },
            },
            # Monitors
            {
                "name": "LG UltraGear 27GP950-B",
                "slug": "lg-ultragear-27gp950",
                "sku": "LG-27GP950",
                "brand": "lg",
                "category": "monitors",
                "price": 89000,
                "compare_at_price": 109000,
                "description": "27-inch 4K Nano IPS, 160Hz, 1ms GtG, HDMI 2.1, G-Sync & FreeSync Premium Pro.",
                "stock": 12,
                "specs": {
                    "display_size": "27",
                    "display_resolution": "3840 x 2160",
                    "refresh_rate": "160",
                    "panel_type": "Nano IPS",
                    "response_time": "1",
                    "hdr": "HDR600",
                },
            },
            {
                "name": "Samsung Odyssey G7 32-inch",
                "slug": "samsung-odyssey-g7-32",
                "sku": "SAM-G7-32",
                "brand": "samsung",
                "category": "monitors",
                "price": 52000,
                "compare_at_price": 62000,
                "description": "32-inch WQHD 1000R curved, 240Hz, 1ms, QLED, G-Sync Compatible.",
                "stock": 18,
                "specs": {
                    "display_size": "32",
                    "display_resolution": "2560 x 1440",
                    "refresh_rate": "240",
                    "panel_type": "VA QLED",
                    "response_time": "1",
                    "hdr": "HDR600",
                },
            },
            # PC Components
            {
                "name": "AMD Ryzen 9 7950X",
                "slug": "amd-ryzen-9-7950x",
                "sku": "AMD-R9-7950X",
                "brand": "amd",
                "category": "processors",
                "price": 52000,
                "compare_at_price": 59000,
                "description": "16 cores, 32 threads, up to 5.7GHz, 170W TDP, Zen 4 architecture.",
                "stock": 20,
                "specs": {
                    "socket": "AM5",
                    "tdp": "170",
                    "benchmark_score": "38000",
                },
            },
            {
                "name": "Intel Core i9-14900K",
                "slug": "intel-core-i9-14900k",
                "sku": "INT-I9-14900K",
                "brand": "intel",
                "category": "processors",
                "price": 58000,
                "description": "24 cores (8P+16E), up to 6.0GHz, 253W TDP.",
                "stock": 15,
                "specs": {
                    "socket": "LGA 1700",
                    "tdp": "253",
                    "benchmark_score": "40000",
                },
            },
            {
                "name": "NVIDIA GeForce RTX 4070 Ti Super",
                "slug": "nvidia-rtx-4070-ti-super",
                "sku": "NV-4070TIS",
                "brand": "nvidia",
                "category": "graphics-cards",
                "price": 85000,
                "compare_at_price": 95000,
                "description": "16GB GDDR6X, Ada Lovelace architecture, DLSS 3, ray tracing.",
                "stock": 10,
                "specs": {
                    "tdp": "285",
                    "benchmark_score": "32000",
                },
            },
        ]

        created = 0
        for p in products_data:
            if db.query(Product).filter(Product.slug == p["slug"]).first():
                continue

            brand = brands.get(p["brand"])
            cat = cats.get(p["category"])
            if not brand or not cat:
                continue

            product = Product(
                name=p["name"],
                slug=p["slug"],
                sku=p["sku"],
                description=p.get("description", ""),
                price=p["price"],
                compare_at_price=p.get("compare_at_price"),
                stock_quantity=p.get("stock", 0),
                brand_id=brand.id,
                category_id=cat.id,
                is_active=True,
            )
            db.add(product)
            db.flush()

            # Add specifications
            for key, value in p.get("specs", {}).items():
                spec = ProductSpecification(
                    product_id=product.id,
                    spec_key=key,
                    value=str(value),
                )
                db.add(spec)

            created += 1

        db.commit()
        print(f"[OK] Created {created} sample products")

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
        # ~1,000-1,500 real-world products across all 15 categories, spec
        # templates/options, reviews, coupons and sample orders. Idempotent.
        from scripts.seed_catalog import seed_catalog
        seed_catalog(db)

        print("\n[DONE] Database seeded successfully!")
        print("   Admin login: admin@gmail.com / admin123")
        print("   Backend API: http://localhost:8000/docs")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
