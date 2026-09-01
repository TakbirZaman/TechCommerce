"""
Icecat Product Import Script

Fetches product data from Open Icecat API and imports into TechCommerce.

Usage:
  python -m scripts.import_icecat --brand apple --category laptops --limit 20
  python -m scripts.import_icecat --all --limit 50
  python -m scripts.import_icecat --search "iphone 15"

Requires ICECAT_API_KEY environment variable (get from https://icecat.com)
"""
import argparse
import os
import re
import sys
import time
import hashlib
from typing import Optional

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal, init_db
from core.models.catalog import Brand, Category
from core.models.specification import (
    Product,
    ProductImage,
    ProductSpecification,
    SpecificationTemplate,
)


# Icecat API config
ICECAT_API_KEY = os.getenv("ICECAT_API_KEY", "")
ICECAT_BASE_URL = "https://api.icecat.com/v1"

# Brand name normalization
BRAND_ALIASES = {
    "apple": "apple",
    "samsung": "samsung",
    "dell": "dell",
    "lenovo": "lenovo",
    "hp": "hp",
    "hewlett-packard": "hp",
    "asus": "asus",
    "msi": "msi",
    "sony": "sony",
    "lg": "lg",
    "xiaomi": "xiaomi",
    "oneplus": "oneplus",
    "intel": "intel",
    "amd": "amd",
    "nvidia": "nvidia",
    "corsair": "corsair",
    "gigabyte": "gigabyte",
    "kingston": "kingston",
    "western digital": "wd",
    "wd": "wd",
    "benq": "benq",
    "logitech": "logitech",
}

CATEGORY_MAP = {
    "laptops": "laptops",
    "notebook": "laptops",
    "smartphones": "phones",
    "phone": "phones",
    "mobile phone": "phones",
    "monitors": "monitors",
    "monitor": "monitors",
    "processors": "processors",
    "cpu": "processors",
    "processor": "processors",
    "graphics cards": "graphics-cards",
    "video card": "graphics-cards",
    "graphics": "graphics-cards",
    "ram": "ram",
    "memory": "ram",
    "storage": "storage",
    "ssd": "storage",
    "hdd": "storage",
    "hard drive": "storage",
    "motherboards": "motherboards",
    "motherboard": "motherboards",
    "power supplies": "power-supplies",
    "psu": "power-supplies",
    "cases": "cases",
    "case": "cases",
    "keyboards": "keyboards",
    "keyboard": "keyboards",
    "mice": "mice",
    "mouse": "mice",
    "headsets": "headsets",
    "headphone": "headsets",
    "tablets": "tablets",
    "tablet": "tablets",
}

# BDT conversion rate (approximate)
USD_TO_BDT = 120.0


def normalize_brand(brand_name: str) -> str:
    """Normalize brand name to slug."""
    lower = brand_name.lower().strip()
    return BRAND_ALIASES.get(lower, lower.replace(" ", "-"))


def map_category(icecat_category: str) -> Optional[str]:
    """Map Icecat category to our category slug."""
    lower = icecat_category.lower().strip()
    for key, value in CATEGORY_MAP.items():
        if key in lower:
            return value
    return None


def parse_price(price_str: str) -> float:
    """Parse price string to float (in BDT)."""
    if not price_str:
        return 0.0
    # Remove currency symbols and spaces
    cleaned = re.sub(r"[^\d.,]", "", price_str)
    cleaned = cleaned.replace(",", "")
    try:
        usd = float(cleaned)
        return round(usd * USD_TO_BDT, 2)
    except ValueError:
        return 0.0


def sanitize_slug(name: str) -> str:
    """Create URL-friendly slug from product name."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:280]


def create_sku(brand_slug: str, name: str) -> str:
    """Create unique SKU from brand and product name."""
    prefix = brand_slug[:3].upper()
    h = hashlib.md5(name.encode()).hexdigest()[:8].upper()
    return f"{prefix}-{h}"


def fetch_icecat_products(
    brand: str = None,
    category: str = None,
    search: str = None,
    limit: int = 20,
    page: int = 1,
) -> list[dict]:
    """Fetch products from Icecat API."""
    headers = {}
    if ICECAT_API_KEY:
        headers["Authorization"] = f"Bearer {ICECAT_API_KEY}"

    params = {"limit": limit, "page": page}
    if brand:
        params["brand"] = brand
    if category:
        params["category"] = category
    if search:
        params["q"] = search

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{ICECAT_BASE_URL}/products", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("products", data.get("items", []))
    except Exception as e:
        print(f"[ERROR] Failed to fetch from Icecat: {e}")
        return []


def fetch_icecat_product_detail(product_id: str) -> Optional[dict]:
    """Fetch detailed product data from Icecat."""
    headers = {}
    if ICECAT_API_KEY:
        headers["Authorization"] = f"Bearer {ICECAT_API_KEY}"

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{ICECAT_BASE_URL}/products/{product_id}", headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch product {product_id}: {e}")
        return None


def import_product(db, product_data: dict, brand_slug: str, category_slug: str) -> Optional[Product]:
    """Import a single product from Icecat data."""
    name = product_data.get("name", product_data.get("title", ""))
    if not name:
        return None

    product_id = product_data.get("id", product_data.get("product_id", ""))
    slug = sanitize_slug(name)

    # Check if product already exists
    existing = db.query(Product).filter(Product.slug == slug).first()
    if existing:
        return None

    # Get brand
    brand = db.query(Brand).filter(Brand.slug == brand_slug).first()
    if not brand:
        return None

    # Get category
    category = db.query(Category).filter(Category.slug == category_slug).first()
    if not category:
        return None

    # Parse price
    price = 0.0
    if "price" in product_data:
        if isinstance(product_data["price"], (int, float)):
            price = round(float(product_data["price"]) * USD_TO_BDT, 2)
        else:
            price = parse_price(str(product_data["price"]))

    if price <= 0:
        price = round(50000 * USD_TO_BDT, 2)  # Default placeholder price

    # Parse compare_at_price
    compare_at = None
    if "msrp" in product_data:
        msrp = product_data["msrp"]
        if isinstance(msrp, (int, float)):
            compare_at = round(float(msrp) * USD_TO_BDT, 2)
        else:
            compare_at = parse_price(str(msrp))
        if compare_at and compare_at <= price:
            compare_at = None

    # Create product
    product = Product(
        name=name,
        slug=slug,
        sku=create_sku(brand_slug, str(product_id)),
        description=product_data.get("description", product_data.get("short_description", "")),
        price=price,
        compare_at_price=compare_at,
        stock_quantity=product_data.get("stock", product_data.get("quantity", 10)),
        brand_id=brand.id,
        category_id=category.id,
        is_active=True,
    )
    db.add(product)
    db.flush()

    # Add images
    images = product_data.get("images", product_data.get("image_urls", []))
    if isinstance(images, str):
        images = [images]
    elif not isinstance(images, list):
        images = []

    # Main image
    main_image = product_data.get("image_url", product_data.get("thumbnail", ""))
    if main_image:
        images.insert(0, main_image)

    for i, img_url in enumerate(images[:5]):  # Max 5 images
        if img_url and isinstance(img_url, str):
            db.add(ProductImage(
                product_id=product.id,
                url=img_url,
                alt_text=f"{name} image {i+1}",
                sort_order=i,
                is_primary=(i == 0),
            ))

    # Add specifications
    specs = product_data.get("specs", product_data.get("specifications", {}))
    if isinstance(specs, dict):
        for key, value in specs.items():
            if value is not None and str(value).strip():
                db.add(ProductSpecification(
                    product_id=product.id,
                    spec_key=key[:50],
                    value=str(value)[:500],
                ))

    return product


def generate_sample_products(db, brand_slug: str, category_slug: str, count: int = 10) -> int:
    """Generate realistic sample products for testing when Icecat is unavailable."""
    sample_data = {
        "laptops": [
            {"name": "MacBook Pro 14-inch M3 Pro", "brand": "apple", "price": 2499, "specs": {"cpu": "Apple M3 Pro", "ram_gb": "18", "storage_type": "SSD", "storage_gb": "512", "display_size": "14.2", "display_resolution": "3024 x 1964", "gpu": "Apple M3 Pro 14-core", "weight_kg": "1.55", "os": "macOS"}},
            {"name": "MacBook Pro 16-inch M3 Max", "brand": "apple", "price": 3499, "specs": {"cpu": "Apple M3 Max", "ram_gb": "36", "storage_type": "SSD", "storage_gb": "1024", "display_size": "16.2", "display_resolution": "3456 x 2234", "gpu": "Apple M3 Max 40-core", "weight_kg": "2.14", "os": "macOS"}},
            {"name": "Dell XPS 13 Plus 9340", "brand": "dell", "price": 1299, "specs": {"cpu": "Intel Core Ultra 7 155H", "ram_gb": "16", "storage_type": "SSD", "storage_gb": "512", "display_size": "13.4", "display_resolution": "3456 x 2160", "gpu": "Intel Arc", "weight_kg": "1.19", "os": "Windows 11"}},
            {"name": "Dell Inspiron 16 5640", "brand": "dell", "price": 899, "specs": {"cpu": "Intel Core i7-1355U", "ram_gb": "16", "storage_type": "SSD", "storage_gb": "512", "display_size": "16", "display_resolution": "1920 x 1200", "gpu": "Intel Iris Xe", "weight_kg": "1.87", "os": "Windows 11"}},
            {"name": "Lenovo ThinkPad X1 Carbon Gen 12", "brand": "lenovo", "price": 1849, "specs": {"cpu": "Intel Core Ultra 7 155U", "ram_gb": "32", "storage_type": "SSD", "storage_gb": "1024", "display_size": "14", "display_resolution": "2880 x 1800", "gpu": "Intel Arc", "weight_kg": "1.08", "os": "Windows 11"}},
            {"name": "Lenovo Legion Pro 5i 16", "brand": "lenovo", "price": 1799, "specs": {"cpu": "Intel Core i9-14900HX", "ram_gb": "32", "storage_type": "SSD", "storage_gb": "1024", "display_size": "16", "display_resolution": "2560 x 1600", "gpu": "NVIDIA RTX 4070", "weight_kg": "2.5", "os": "Windows 11"}},
            {"name": "HP Spectre x360 14", "brand": "hp", "price": 1449, "specs": {"cpu": "Intel Core Ultra 7 155H", "ram_gb": "16", "storage_type": "SSD", "storage_gb": "1024", "display_size": "14", "display_resolution": "2880 x 1800", "gpu": "Intel Arc", "weight_kg": "1.44", "os": "Windows 11"}},
            {"name": "ASUS ROG Strix G16 2024", "brand": "asus", "price": 1999, "specs": {"cpu": "Intel Core i9-14900HX", "ram_gb": "32", "storage_type": "SSD", "storage_gb": "1024", "display_size": "16", "display_resolution": "2560 x 1600", "gpu": "NVIDIA RTX 4080", "weight_kg": "2.5", "os": "Windows 11"}},
            {"name": "ASUS Zenbook 14 OLED", "brand": "asus", "price": 1099, "specs": {"cpu": "AMD Ryzen 7 8840U", "ram_gb": "16", "storage_type": "SSD", "storage_gb": "512", "display_size": "14", "display_resolution": "2880 x 1800", "gpu": "AMD Radeon 780M", "weight_kg": "1.28", "os": "Windows 11"}},
            {"name": "MSI Raider GE78 HX", "brand": "msi", "price": 2899, "specs": {"cpu": "Intel Core i9-14900HX", "ram_gb": "32", "storage_type": "SSD", "storage_gb": "2048", "display_size": "17.3", "display_resolution": "2560 x 1600", "gpu": "NVIDIA RTX 4090", "weight_kg": "3.1", "os": "Windows 11"}},
        ],
        "phones": [
            {"name": "Samsung Galaxy Z Fold 5", "brand": "samsung", "price": 1799, "specs": {"chipset": "Snapdragon 8 Gen 2", "ram_gb": "12", "storage_gb": "256", "display_size": "7.6", "display_resolution": "2176 x 1812", "refresh_rate": "120", "camera_mp": "50", "battery_mah": "4400", "os": "Android 14"}},
            {"name": "Samsung Galaxy A54 5G", "brand": "samsung", "price": 449, "specs": {"chipset": "Exynos 1380", "ram_gb": "8", "storage_gb": "128", "display_size": "6.4", "display_resolution": "2340 x 1080", "refresh_rate": "120", "camera_mp": "50", "battery_mah": "5000", "os": "Android 14"}},
            {"name": "iPhone 15 Pro", "brand": "apple", "price": 999, "specs": {"chipset": "Apple A17 Pro", "ram_gb": "8", "storage_gb": "128", "display_size": "6.1", "display_resolution": "2556 x 1179", "refresh_rate": "120", "camera_mp": "48", "battery_mah": "3274", "os": "iOS 17"}},
            {"name": "iPhone 15", "brand": "apple", "price": 799, "specs": {"chipset": "Apple A16 Bionic", "ram_gb": "6", "storage_gb": "128", "display_size": "6.1", "display_resolution": "2556 x 1179", "refresh_rate": "60", "camera_mp": "48", "battery_mah": "3349", "os": "iOS 17"}},
            {"name": "OnePlus Nord CE4", "brand": "oneplus", "price": 299, "specs": {"chipset": "Snapdragon 7 Gen 3", "ram_gb": "8", "storage_gb": "128", "display_size": "6.7", "display_resolution": "2412 x 1080", "refresh_rate": "120", "camera_mp": "50", "battery_mah": "5500", "os": "Android 14"}},
            {"name": "Xiaomi 13T Pro", "brand": "xiaomi", "price": 649, "specs": {"chipset": "Dimensity 9200+", "ram_gb": "12", "storage_gb": "256", "display_size": "6.67", "display_resolution": "2712 x 1220", "refresh_rate": "144", "camera_mp": "50", "battery_mah": "5000", "os": "Android 14"}},
            {"name": "Samsung Galaxy S23 FE", "brand": "samsung", "price": 599, "specs": {"chipset": "Exynos 2200", "ram_gb": "8", "storage_gb": "128", "display_size": "6.4", "display_resolution": "2340 x 1080", "refresh_rate": "120", "camera_mp": "50", "battery_mah": "4500", "os": "Android 14"}},
            {"name": "Sony Xperia 1 V", "brand": "sony", "price": 1399, "specs": {"chipset": "Snapdragon 8 Gen 2", "ram_gb": "12", "storage_gb": "256", "display_size": "6.5", "display_resolution": "3840 x 1644", "refresh_rate": "120", "camera_mp": "52", "battery_mah": "5000", "os": "Android 13"}},
        ],
        "monitors": [
            {"name": "Samsung Odyssey OLED G8 34", "brand": "samsung", "price": 1299, "specs": {"display_size": "34", "display_resolution": "3440 x 1440", "refresh_rate": "175", "panel_type": "OLED", "response_time": "0.1", "hdr": "HDR True Black 400"}},
            {"name": "LG 27GP95R-B UltraGear", "brand": "lg", "price": 799, "specs": {"display_size": "27", "display_resolution": "3840 x 2160", "refresh_rate": "144", "panel_type": "Nano IPS", "response_time": "1", "hdr": "HDR600"}},
            {"name": "ASUS ProArt PA279CRV", "brand": "asus", "price": 549, "specs": {"display_size": "27", "display_resolution": "3840 x 2160", "refresh_rate": "60", "panel_type": "IPS", "response_time": "5", "hdr": "HDR400"}},
            {"name": "BenQ MOBIUZ EX2710U", "brand": "benq", "price": 649, "specs": {"display_size": "27", "display_resolution": "3840 x 2160", "refresh_rate": "144", "panel_type": "IPS", "response_time": "1", "hdr": "HDR600"}},
            {"name": "Dell S2722QC 27 4K", "brand": "dell", "price": 319, "specs": {"display_size": "27", "display_resolution": "3840 x 2160", "refresh_rate": "60", "panel_type": "IPS", "response_time": "8", "hdr": "HDR"}},
            {"name": "LG UltraWide 34WQ73A-B", "brand": "lg", "price": 449, "specs": {"display_size": "34", "display_resolution": "3440 x 1440", "refresh_rate": "60", "panel_type": "IPS", "response_time": "5", "hdr": "HDR10"}},
            {"name": "Samsung ViewFinity S9 27", "brand": "samsung", "price": 1599, "specs": {"display_size": "27", "display_resolution": "5120 x 2880", "refresh_rate": "60", "panel_type": "IPS", "response_time": "5", "hdr": "HDR400"}},
        ],
        "processors": [
            {"name": "AMD Ryzen 7 7800X3D", "brand": "amd", "price": 369, "specs": {"socket": "AM5", "tdp": "120", "benchmark_score": "34000"}},
            {"name": "AMD Ryzen 5 7600X", "brand": "amd", "price": 199, "specs": {"socket": "AM5", "tdp": "105", "benchmark_score": "28000"}},
            {"name": "Intel Core i7-14700K", "brand": "intel", "price": 399, "specs": {"socket": "LGA 1700", "tdp": "253", "benchmark_score": "36000"}},
            {"name": "Intel Core i5-14600K", "brand": "intel", "price": 289, "specs": {"socket": "LGA 1700", "tdp": "181", "benchmark_score": "30000"}},
        ],
        "graphics-cards": [
            {"name": "NVIDIA GeForce RTX 4090", "brand": "nvidia", "price": 1599, "specs": {"tdp": "450", "benchmark_score": "48000"}},
            {"name": "NVIDIA GeForce RTX 4080 Super", "brand": "nvidia", "price": 999, "specs": {"tdp": "320", "benchmark_score": "40000"}},
            {"name": "NVIDIA GeForce RTX 4060 Ti", "brand": "nvidia", "price": 399, "specs": {"tdp": "160", "benchmark_score": "28000"}},
            {"name": "AMD Radeon RX 7900 XTX", "brand": "amd", "price": 949, "specs": {"tdp": "355", "benchmark_score": "38000"}},
        ],
        "ram": [
            {"name": "Corsair Vengeance DDR5 32GB 6000MHz", "brand": "corsair", "price": 119, "specs": {"capacity_gb": "32", "speed_mhz": "6000", "type": "DDR5", "cas_latency": "36"}},
            {"name": "Kingston Fury Beast DDR5 16GB 5200MHz", "brand": "kingston", "price": 59, "specs": {"capacity_gb": "16", "speed_mhz": "5200", "type": "DDR5", "cas_latency": "40"}},
            {"name": "Corsair Dominator DDR5 64GB 6400MHz", "brand": "corsair", "price": 279, "specs": {"capacity_gb": "64", "speed_mhz": "6400", "type": "DDR5", "cas_latency": "32"}},
            {"name": "Kingston Fury Beast DDR4 32GB 3200MHz", "brand": "kingston", "price": 69, "specs": {"capacity_gb": "32", "speed_mhz": "3200", "type": "DDR4", "cas_latency": "16"}},
        ],
        "storage": [
            {"name": "Samsung 990 Pro 2TB NVMe SSD", "brand": "samsung", "price": 189, "specs": {"capacity_gb": "2048", "interface": "PCIe 4.0 NVMe", "read_speed": "7450", "write_speed": "6900", "type": "SSD"}},
            {"name": "WD Black SN850X 1TB NVMe SSD", "brand": "western-digital", "price": 99, "specs": {"capacity_gb": "1024", "interface": "PCIe 4.0 NVMe", "read_speed": "7300", "write_speed": "6300", "type": "SSD"}},
            {"name": "Samsung 870 EVO 1TB SATA SSD", "brand": "samsung", "price": 89, "specs": {"capacity_gb": "1024", "interface": "SATA III", "read_speed": "560", "write_speed": "530", "type": "SSD"}},
            {"name": "Kingston NV2 2TB NVMe SSD", "brand": "kingston", "price": 109, "specs": {"capacity_gb": "2048", "interface": "PCIe 4.0 NVMe", "read_speed": "3500", "write_speed": "2800", "type": "SSD"}},
        ],
        "motherboards": [
            {"name": "ASUS ROG Strix Z790-E Gaming WiFi", "brand": "asus", "price": 379, "specs": {"socket": "LGA 1700", "chipset": "Z790", "form_factor": "ATX", "memory_slots": "4", "max_memory_gb": "128", "wifi": "WiFi 6E"}},
            {"name": "MSI MAG B650 Tomahawk WiFi", "brand": "msi", "price": 229, "specs": {"socket": "AM5", "chipset": "B650", "form_factor": "ATX", "memory_slots": "4", "max_memory_gb": "128", "wifi": "WiFi 6E"}},
            {"name": "Gigabyte B760 Aorus Elite AX", "brand": "gigabyte", "price": 189, "specs": {"socket": "LGA 1700", "chipset": "B760", "form_factor": "ATX", "memory_slots": "4", "max_memory_gb": "128", "wifi": "WiFi 6E"}},
        ],
        "power-supplies": [
            {"name": "Corsair RM850x 850W 80+ Gold", "brand": "corsair", "price": 149, "specs": {"wattage": "850", "efficiency": "80+ Gold", "modular": "Full", "fan_size": "135mm"}},
            {"name": "Corsair RM1000x 1000W 80+ Gold", "brand": "corsair", "price": 189, "specs": {"wattage": "1000", "efficiency": "80+ Gold", "modular": "Full", "fan_size": "135mm"}},
        ],
        "cases": [
            {"name": "Corsair 4000D Airflow", "brand": "corsair", "price": 104, "specs": {"type": "Mid Tower", "motherboard_support": "ATX", "max_gpu_length": "360", "max_cpu_cooler_height": "170"}},
            {"name": "NZXT H7 Flow", "brand": "corsair", "price": 129, "specs": {"type": "Mid Tower", "motherboard_support": "ATX", "max_gpu_length": "400", "max_cpu_cooler_height": "185"}},
        ],
        "keyboards": [
            {"name": "Corsair K100 RGB Mechanical", "brand": "corsair", "price": 229, "specs": {"switch_type": "Cherry MX Speed", "layout": "Full", "backlight": "RGB", "connection": "Wired"}},
            {"name": "Logitech MX Keys S", "brand": "logitech", "price": 109, "specs": {"switch_type": "Membrane", "layout": "Full", "backlight": "White LED", "connection": "Wireless"}},
        ],
        "mice": [
            {"name": "Logitech MX Master 3S", "brand": "logitech", "price": 99, "specs": {"sensor": "Darkfield", "dpi": "8000", "buttons": "7", "connection": "Wireless", "weight_g": "141"}},
            {"name": "Corsair M65 RGB Ultra", "brand": "corsair", "price": 79, "specs": {"sensor": "PMW3391", "dpi": "26000", "buttons": "8", "connection": "Wired", "weight_g": "97"}},
        ],
        "headsets": [
            {"name": "Corsair HS80 RGB Wireless", "brand": "corsair", "price": 149, "specs": {"driver_size": "50", "frequency_response": "20Hz-40kHz", "microphone": "Omnidirectional", "connection": "Wireless", "battery_hours": "20"}},
            {"name": "Logitech G Pro X 2", "brand": "logitech", "price": 249, "specs": {"driver_size": "50", "frequency_response": "20Hz-20kHz", "microphone": "Detachable Boom", "connection": "Wireless", "battery_hours": "50"}},
        ],
        "tablets": [
            {"name": "Apple iPad Pro 12.9-inch M2", "brand": "apple", "price": 1099, "specs": {"chipset": "Apple M2", "storage_gb": "256", "display_size": "12.9", "display_resolution": "2732 x 2048", "apple_pencil": "2nd Gen", "os": "iPadOS"}},
            {"name": "Samsung Galaxy Tab S9 Ultra", "brand": "samsung", "price": 1199, "specs": {"chipset": "Snapdragon 8 Gen 2", "storage_gb": "256", "display_size": "14.6", "display_resolution": "2960 x 1848", "refresh_rate": "120", "os": "Android 14"}},
        ],
    }

    products = sample_data.get(category_slug, [])
    if brand_slug and brand_slug != "all":
        by_brand = [p for p in products if p.get("brand") == brand_slug]
        products = by_brand if by_brand else products

    category = db.query(Category).filter(Category.slug == category_slug).first()
    if not category:
        return 0

    created = 0
    for data in products[:count]:
        slug = sanitize_slug(data["name"])
        if db.query(Product).filter(Product.slug == slug).first():
            continue

        p_brand_slug = data.get("brand", brand_slug)
        if p_brand_slug == "all":
            p_brand_slug = brand_slug
        brand = db.query(Brand).filter(Brand.slug == p_brand_slug).first()
        if not brand:
            continue

        sku = create_sku(p_brand_slug, slug)
        suffix = 1
        while db.query(Product).filter(Product.sku == sku).first():
            sku = create_sku(p_brand_slug, slug) + f"-{suffix}"
            suffix += 1

        product = Product(
            name=data["name"],
            slug=slug,
            sku=sku,
            description=f"{data['name']} by {brand.name}",
            price=round(data["price"] * USD_TO_BDT, 2),
            stock_quantity=10,
            brand_id=brand.id,
            category_id=category.id,
            is_active=True,
        )
        db.add(product)
        db.flush()

        for key, value in data.get("specs", {}).items():
            db.add(ProductSpecification(
                product_id=product.id,
                spec_key=key[:50],
                value=str(value)[:500],
            ))
        created += 1

    return created


def main():
    parser = argparse.ArgumentParser(description="Import products from Icecat")
    parser.add_argument("--brand", help="Filter by brand slug")
    parser.add_argument("--category", help="Filter by category slug")
    parser.add_argument("--search", help="Search query")
    parser.add_argument("--limit", type=int, default=20, help="Max products to import")
    parser.add_argument("--all", action="store_true", help="Import all categories")
    parser.add_argument("--sample", action="store_true", help="Generate sample data instead of using Icecat")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()

    try:
        if args.sample or not ICECAT_API_KEY:
            print("[INFO] No ICECAT_API_KEY found. Generating sample products...")
            print("[INFO] Set ICECAT_API_KEY env var to use real Icecat data.\n")

            categories = ["laptops", "phones", "monitors", "processors", "graphics-cards", "ram", "storage", "motherboards", "power-supplies", "cases", "keyboards", "mice", "headsets", "tablets"]
            total = 0

            for cat in categories:
                if args.category and args.category != cat:
                    continue
                print(f"  Importing {cat}...")
                count = generate_sample_products(db, args.brand or "all", cat, args.limit)
                total += count
                print(f"    +{count} products")

            db.commit()
            print(f"\n[DONE] Created {total} sample products")
        else:
            print(f"[INFO] Fetching from Icecat API (limit={args.limit})...")
            products = fetch_icecat_products(
                brand=args.brand,
                category=args.category,
                search=args.search,
                limit=args.limit,
            )

            if not products:
                print("[WARN] No products found from Icecat")
                return

            imported = 0
            for p_data in products:
                brand_slug = normalize_brand(p_data.get("brand", {}).get("name", "unknown"))
                category_slug = map_category(p_data.get("category", "unknown"))

                if not category_slug:
                    continue

                product = import_product(db, p_data, brand_slug, category_slug)
                if product:
                    imported += 1
                    print(f"  +{product.name}")

            db.commit()
            print(f"\n[DONE] Imported {imported} products from Icecat")

    finally:
        db.close()


if __name__ == "__main__":
    main()
