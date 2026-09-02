"""
Seed Catalog - Expands TechCommerce with a realistic, large-scale catalog.

Generates ~1,000-1,500 real-world tech products across all 15 categories
(real product lines x real variant combinations), spec templates + options
for ALL 15 categories, Bangladeshi-flavored product reviews, discount
coupons, sample guest orders spread over the last 60 days, and category
SVG placeholder images.

Design notes:
- Idempotent: preloads existing slugs/SKUs/coupon codes/order numbers and
  skips anything already present. Never deletes or duplicates base seed data.
- Deterministic: all randomness via random.Random(42).
- Batch inserts with periodic flush/commit for speed.
- BDT (Bangladeshi Taka) pricing approximating local retail (Startech/Ryans).

Run: python scripts/seed.py   (invoked automatically after base seeding)
"""
import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from core.models.catalog import Brand, Category
from core.models.commerce import (
    Coupon,
    DeliveryZone,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
)
from core.models.specification import (
    Product,
    ProductImage,
    ProductReview,
    ProductSpecification,
    SpecificationOption,
    SpecificationTemplate,
)

RNG = random.Random(42)
NOW = datetime.now(timezone.utc)

REPO_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_PRODUCTS = REPO_ROOT / "uploads" / "products"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def bdt(base: float, lo: float = 0.96, hi: float = 1.05) -> int:
    """Deterministic BDT price jitter, rounded to the nearest 100."""
    return int(round(base * RNG.uniform(lo, hi) / 100.0) * 100)


def pick_price(base: float) -> tuple:
    """Return (price, compare_at_price) — compare_at is a padded MSRP."""
    price = bdt(base)
    if RNG.random() < 0.45:
        compare = int(round(price * RNG.uniform(1.05, 1.18) / 100.0) * 100)
        if compare > price:
            return price, compare
    return price, None


def sku_code(text: str) -> str:
    letters = re.sub(r"[^a-z0-9]", "", text.lower())
    return letters[:3].upper() or "XXX"


CAT3 = {
    "laptops": "LAP", "phones": "PHO", "monitors": "MON", "processors": "CPU",
    "graphics-cards": "GPU", "ram": "RAM", "storage": "STO", "motherboards": "MOT",
    "power-supplies": "PSU", "cases": "CAS", "keyboards": "KEY", "mice": "MOU",
    "headsets": "HEA", "tablets": "TAB", "accessories": "ACC",
}


# ─────────────────────────────────────────────────────────────────────────────
# Spec templates for ALL 15 categories (supersets of the 5 existing ones)
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATES = {
    "laptops": {
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
    },
    "phones": {
        "chipset": {"name": "Chipset", "type": "enum", "filterable": True, "comparable": True},
        "ram_gb": {"name": "RAM", "type": "number", "unit": "GB", "filterable": True, "comparable": True},
        "storage_gb": {"name": "Storage", "type": "number", "unit": "GB", "filterable": True, "comparable": True},
        "display_size": {"name": "Display Size", "type": "number", "unit": "inches", "filterable": True, "comparable": True},
        "display_resolution": {"name": "Resolution", "type": "text", "comparable": True},
        "refresh_rate": {"name": "Refresh Rate", "type": "number", "unit": "Hz", "filterable": True, "comparable": True},
        "camera_mp": {"name": "Main Camera", "type": "number", "unit": "MP", "filterable": True, "comparable": True},
        "battery_mah": {"name": "Battery", "type": "number", "unit": "mAh", "filterable": True, "comparable": True},
        "os": {"name": "OS", "type": "enum", "filterable": True},
    },
    "monitors": {
        "display_size": {"name": "Screen Size", "type": "number", "unit": "inches", "filterable": True, "comparable": True},
        "display_resolution": {"name": "Resolution", "type": "text", "filterable": True, "comparable": True},
        "refresh_rate": {"name": "Refresh Rate", "type": "number", "unit": "Hz", "filterable": True, "comparable": True},
        "panel_type": {"name": "Panel Type", "type": "enum", "filterable": True, "comparable": True},
        "response_time": {"name": "Response Time", "type": "number", "unit": "ms", "filterable": True, "comparable": True},
        "hdr": {"name": "HDR", "type": "boolean", "filterable": True, "comparable": True},
    },
    "processors": {
        "socket": {"name": "Socket", "type": "enum", "filterable": True, "comparable": True},
        "tdp": {"name": "TDP", "type": "number", "unit": "W", "filterable": True, "comparable": True},
        "benchmark_score": {"name": "Benchmark", "type": "number", "filterable": True, "comparable": True},
        "cores": {"name": "Cores", "type": "number", "filterable": True, "comparable": True},
        "threads": {"name": "Threads", "type": "number", "filterable": True, "comparable": True},
        "base_clock_ghz": {"name": "Base Clock", "type": "number", "unit": "GHz", "filterable": True, "comparable": True},
        "boost_clock_ghz": {"name": "Boost Clock", "type": "number", "unit": "GHz", "filterable": True, "comparable": True},
        "tdp_w": {"name": "TDP (Package)", "type": "number", "unit": "W", "filterable": True, "comparable": True},
        "integrated_gpu": {"name": "Integrated Graphics", "type": "enum", "filterable": True, "comparable": True},
        "warranty": {"name": "Warranty", "type": "text"},
    },
    "graphics-cards": {
        "socket": {"name": "Interface", "type": "enum", "filterable": True, "comparable": True},
        "tdp": {"name": "TDP", "type": "number", "unit": "W", "filterable": True, "comparable": True},
        "benchmark_score": {"name": "Benchmark", "type": "number", "filterable": True, "comparable": True},
        "memory_gb": {"name": "Memory", "type": "number", "unit": "GB", "filterable": True, "comparable": True},
        "memory_type": {"name": "Memory Type", "type": "enum", "filterable": True, "comparable": True},
        "core_clock": {"name": "Core Clock", "type": "number", "unit": "MHz", "filterable": True, "comparable": True},
        "boost_clock": {"name": "Boost Clock", "type": "number", "unit": "MHz", "filterable": True, "comparable": True},
        "length_mm": {"name": "Card Length", "type": "number", "unit": "mm", "filterable": True, "comparable": True},
        "warranty": {"name": "Warranty", "type": "text"},
    },
    "ram": {
        "type": {"name": "Memory Type", "type": "enum", "filterable": True, "comparable": True},
        "capacity_gb": {"name": "Capacity", "type": "number", "unit": "GB", "filterable": True, "comparable": True},
        "speed_mhz": {"name": "Speed", "type": "number", "unit": "MHz", "filterable": True, "comparable": True},
        "modules": {"name": "Modules", "type": "number", "filterable": True, "comparable": True},
        "rgb": {"name": "RGB Lighting", "type": "boolean", "filterable": True},
        "warranty": {"name": "Warranty", "type": "text"},
    },
    "storage": {
        "capacity_gb": {"name": "Capacity", "type": "number", "unit": "GB", "filterable": True, "comparable": True},
        "interface": {"name": "Interface", "type": "enum", "filterable": True, "comparable": True},
        "read_mb_s": {"name": "Read Speed", "type": "number", "unit": "MB/s", "filterable": True, "comparable": True},
        "write_mb_s": {"name": "Write Speed", "type": "number", "unit": "MB/s", "filterable": True, "comparable": True},
        "form_factor": {"name": "Form Factor", "type": "enum", "filterable": True, "comparable": True},
        "warranty": {"name": "Warranty", "type": "text"},
    },
    "motherboards": {
        "socket": {"name": "Socket", "type": "enum", "filterable": True, "comparable": True},
        "chipset": {"name": "Chipset", "type": "enum", "filterable": True, "comparable": True},
        "form_factor": {"name": "Form Factor", "type": "enum", "filterable": True, "comparable": True},
        "memory_type": {"name": "Memory Support", "type": "enum", "filterable": True, "comparable": True},
        "m2_slots": {"name": "M.2 Slots", "type": "number", "filterable": True, "comparable": True},
        "warranty": {"name": "Warranty", "type": "text"},
    },
    "power-supplies": {
        "wattage": {"name": "Wattage", "type": "number", "unit": "W", "filterable": True, "comparable": True},
        "efficiency": {"name": "Efficiency Rating", "type": "enum", "filterable": True, "comparable": True},
        "modular": {"name": "Modularity", "type": "enum", "filterable": True, "comparable": True},
        "warranty": {"name": "Warranty", "type": "text"},
    },
    "cases": {
        "form_factor": {"name": "Motherboard Support", "type": "enum", "filterable": True, "comparable": True},
        "side_panel": {"name": "Side Panel", "type": "enum", "filterable": True, "comparable": True},
        "preinstalled_fans": {"name": "Pre-installed Fans", "type": "number", "filterable": True, "comparable": True},
        "warranty": {"name": "Warranty", "type": "text"},
    },
    "keyboards": {
        "switch_type": {"name": "Switch Type", "type": "enum", "filterable": True, "comparable": True},
        "layout": {"name": "Layout", "type": "enum", "filterable": True, "comparable": True},
        "connectivity": {"name": "Connectivity", "type": "enum", "filterable": True, "comparable": True},
        "rgb": {"name": "RGB Lighting", "type": "boolean", "filterable": True},
        "warranty": {"name": "Warranty", "type": "text"},
    },
    "mice": {
        "dpi_max": {"name": "Max DPI", "type": "number", "filterable": True, "comparable": True},
        "connectivity": {"name": "Connectivity", "type": "enum", "filterable": True, "comparable": True},
        "weight_g": {"name": "Weight", "type": "number", "unit": "g", "filterable": True, "comparable": True},
        "rgb": {"name": "RGB Lighting", "type": "boolean", "filterable": True},
        "warranty": {"name": "Warranty", "type": "text"},
    },
    "headsets": {
        "type": {"name": "Type", "type": "enum", "filterable": True, "comparable": True},
        "connectivity": {"name": "Connectivity", "type": "enum", "filterable": True, "comparable": True},
        "driver_mm": {"name": "Driver Size", "type": "number", "unit": "mm", "filterable": True, "comparable": True},
        "surround": {"name": "Surround Sound", "type": "boolean", "filterable": True},
        "warranty": {"name": "Warranty", "type": "text"},
    },
    "tablets": {
        "display_size": {"name": "Display Size", "type": "number", "unit": "inches", "filterable": True, "comparable": True},
        "chipset": {"name": "Chipset", "type": "text", "comparable": True},
        "ram_gb": {"name": "RAM", "type": "number", "unit": "GB", "filterable": True, "comparable": True},
        "storage_gb": {"name": "Storage", "type": "number", "unit": "GB", "filterable": True, "comparable": True},
        "battery_mah": {"name": "Battery", "type": "number", "unit": "mAh", "filterable": True, "comparable": True},
        "os": {"name": "OS", "type": "enum", "filterable": True},
    },
    "accessories": {
        "type": {"name": "Accessory Type", "type": "enum", "filterable": True, "comparable": True},
        "compatibility": {"name": "Compatibility", "type": "text"},
        "warranty": {"name": "Warranty", "type": "text"},
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Supplementary brands (real-world product lines need them; added idempotently)
# ─────────────────────────────────────────────────────────────────────────────

EXTRA_BRANDS = [
    ("Zotac", "zotac"), ("ASRock", "asrock"), ("G.Skill", "gskill"),
    ("TeamGroup", "teamgroup"), ("ADATA", "adata"), ("Crucial", "crucial"),
    ("Seagate", "seagate"), ("Acer", "acer"), ("Razer", "razer"),
    ("SteelSeries", "steelseries"), ("Redragon", "redragon"), ("HyperX", "hyperx"),
    ("Cooler Master", "cooler-master"), ("Seasonic", "seasonic"),
    ("Thermaltake", "thermaltake"), ("NZXT", "nzxt"), ("DeepCool", "deepcool"),
    ("Lian Li", "lian-li"), ("Noctua", "noctua"), ("Google", "google"),
    ("Realme", "realme"), ("Vivo", "vivo"), ("Oppo", "oppo"), ("Ugreen", "ugreen"),
    ("Baseus", "baseus"), ("Anker", "anker"), ("TP-Link", "tp-link"),
    ("SanDisk", "sandisk"), ("Arctic", "arctic"), ("Thermal Grizzly", "thermal-grizzly"),
    ("Infinix", "infinix"), ("Tecno", "tecno"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Category SVG placeholder art
# ─────────────────────────────────────────────────────────────────────────────

CAT_ART = {
    "laptops": ("#0f172a", "#2563eb", "💻", "Laptops"),
    "phones": ("#2e1065", "#9333ea", "📱", "Smartphones"),
    "monitors": ("#0c4a6e", "#0ea5e9", "🖥️", "Monitors"),
    "processors": ("#1c1917", "#f59e0b", "⚙️", "Processors"),
    "graphics-cards": ("#14532d", "#22c55e", "🎮", "Graphics Cards"),
    "ram": ("#450a0a", "#ef4444", "🧠", "RAM"),
    "storage": ("#164e63", "#06b6d4", "💾", "Storage"),
    "motherboards": ("#1e1b4b", "#818cf8", "🔌", "Motherboards"),
    "power-supplies": ("#422006", "#eab308", "🔋", "Power Supplies"),
    "cases": ("#111827", "#6b7280", "🗄️", "Cases"),
    "keyboards": ("#3b0764", "#a855f7", "⌨️", "Keyboards"),
    "mice": ("#0f766e", "#2dd4bf", "🖱️", "Mice"),
    "headsets": ("#500724", "#ec4899", "🎧", "Headsets"),
    "tablets": ("#1e293b", "#38bdf8", "📲", "Tablets"),
    "accessories": ("#292524", "#f97316", "🧰", "Accessories"),
}


def write_placeholder_svgs() -> int:
    """Create one gradient SVG placeholder per category in uploads/products/."""
    UPLOAD_PRODUCTS.mkdir(parents=True, exist_ok=True)
    created = 0
    for slug, (c1, c2, icon, label) in CAT_ART.items():
        path = UPLOAD_PRODUCTS / f"cat-{slug}.svg"
        if path.exists():
            continue
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">\n'
            '  <defs>\n'
            f'    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">\n'
            f'      <stop offset="0%" stop-color="{c1}"/>\n'
            f'      <stop offset="100%" stop-color="{c2}"/>\n'
            '    </linearGradient>\n'
            '  </defs>\n'
            '  <rect width="800" height="800" fill="url(#g)"/>\n'
            '  <circle cx="660" cy="120" r="220" fill="#ffffff" opacity="0.06"/>\n'
            '  <circle cx="120" cy="700" r="260" fill="#000000" opacity="0.12"/>\n'
            f'  <text x="400" y="420" font-size="220" text-anchor="middle">{icon}</text>\n'
            f'  <text x="400" y="600" font-family="Segoe UI, Arial, sans-serif" font-size="52" font-weight="bold" fill="#ffffff" text-anchor="middle" opacity="0.95">{label}</text>\n'
            f'  <text x="400" y="660" font-family="Segoe UI, Arial, sans-serif" font-size="26" fill="#ffffff" text-anchor="middle" opacity="0.65">TechCommerce</text>\n'
            '</svg>\n'
        )
        path.write_text(svg, encoding="utf-8")
        created += 1
    return created


def image_url(cat_slug: str) -> str:
    return f"/uploads/products/cat-{cat_slug}.svg"


# ─────────────────────────────────────────────────────────────────────────────
# Product generators — one per category. Each returns dicts:
#   {name, brand, price, compare_at, specs{key: str}}
# ─────────────────────────────────────────────────────────────────────────────

def gen_laptops():
    """(brand, name, cpu, gpu, ram, storage, size, res, weight, battery_wh, price)"""
    L = [
        ("apple", "MacBook Air M2 13", "Apple M2", "Apple M2 8-core", 8, 256, 13.6, "2560 x 1664", 1.24, 52.6, 134000),
        ("apple", "MacBook Air M2 15", "Apple M2", "Apple M2 10-core", 8, 256, 15.3, "2880 x 1864", 1.51, 66.5, 149000),
        ("apple", "MacBook Air M3 13", "Apple M3", "Apple M3 8-core", 8, 256, 13.6, "2560 x 1664", 1.24, 53.8, 149000),
        ("apple", "MacBook Air M3 15", "Apple M3", "Apple M3 10-core", 16, 512, 15.3, "2880 x 1864", 1.51, 66.5, 179000),
        ("apple", "MacBook Pro 14 M3 Pro", "Apple M3 Pro", "Apple M3 Pro 18-core", 18, 512, 14.2, "3024 x 1964", 1.61, 72.4, 239000),
        ("apple", "MacBook Pro 16 M3 Max", "Apple M3 Max", "Apple M3 Max 30-core", 36, 1024, 16.2, "3456 x 2234", 2.16, 100, 389000),
        ("dell", "Dell XPS 13 9315", "Intel Core i5-1230U", "Intel Iris Xe", 16, 512, 13.4, "1920 x 1200", 1.17, 51, 145000),
        ("dell", "Dell XPS 13 9340", "Intel Core Ultra 7 155H", "Intel Arc", 16, 512, 13.4, "1920 x 1200", 1.19, 55, 178000),
        ("dell", "Dell XPS 14 9440", "Intel Core Ultra 7 155H", "NVIDIA RTX 4050", 16, 1024, 14.5, "1920 x 1200", 1.68, 69.5, 225000),
        ("dell", "Dell XPS 16 9640", "Intel Core Ultra 9 185H", "NVIDIA RTX 4060", 32, 1024, 16.3, "3840 x 2400", 2.1, 99.5, 295000),
        ("dell", "Dell Inspiron 15 3520", "Intel Core i5-1235U", "Intel Iris Xe", 8, 256, 15.6, "1920 x 1080", 1.85, 41, 62000),
        ("dell", "Dell Inspiron 15 3530", "Intel Core i7-1355U", "Intel Iris Xe", 16, 512, 15.6, "1920 x 1080", 1.65, 41, 85000),
        ("dell", "Dell Inspiron 14 5420", "Intel Core i5-1240P", "Intel Iris Xe", 8, 512, 14.0, "1920 x 1200", 1.54, 54, 78000),
        ("dell", "Dell Inspiron 16 5640", "Intel Core Ultra 5 125H", "Intel Arc", 16, 512, 16.0, "1920 x 1200", 1.87, 64, 96000),
        ("dell", "Dell G15 5530", "Intel Core i5-13450HX", "NVIDIA RTX 4050", 8, 512, 15.6, "1920 x 1080", 2.65, 56, 118000),
        ("dell", "Dell G15 5530", "Intel Core i5-13450HX", "NVIDIA RTX 4060", 16, 512, 15.6, "1920 x 1080", 2.65, 56, 132000),
        ("dell", "Dell G16 7630", "Intel Core i7-13650HX", "NVIDIA RTX 4060", 16, 512, 16.0, "2560 x 1600", 2.87, 86, 158000),
        ("dell", "Dell G16 7630", "Intel Core i7-13650HX", "NVIDIA RTX 4070", 16, 1024, 16.0, "2560 x 1600", 2.87, 86, 178000),
        ("hp", "HP Pavilion 14", "Intel Core i5-1335U", "Intel Iris Xe", 8, 512, 14.0, "1920 x 1080", 1.41, 43, 68000),
        ("hp", "HP Pavilion 15", "Intel Core i7-1355U", "Intel Iris Xe", 16, 512, 15.6, "1920 x 1080", 1.75, 41, 88000),
        ("hp", "HP Pavilion x360 14", "Intel Core i5-1335U", "Intel Iris Xe", 8, 512, 14.0, "1920 x 1080", 1.59, 43, 78000),
        ("hp", "HP Victus 15", "Intel Core i5-12450H", "NVIDIA RTX 2050", 8, 512, 15.6, "1920 x 1080", 2.29, 52, 78000),
        ("hp", "HP Victus 15", "Intel Core i5-13420H", "NVIDIA RTX 3050", 16, 512, 15.6, "1920 x 1080", 2.29, 52, 94000),
        ("hp", "HP Victus 15", "Intel Core i5-13420H", "NVIDIA RTX 4050", 16, 1024, 15.6, "1920 x 1080", 2.29, 52, 106000),
        ("hp", "HP Victus 16", "Intel Core i7-13700H", "NVIDIA RTX 4060", 16, 1024, 16.1, "1920 x 1200", 2.3, 70, 138000),
        ("hp", "HP Omen 16", "Intel Core i7-14650HX", "NVIDIA RTX 4060", 16, 512, 16.1, "2560 x 1600", 2.35, 83, 162000),
        ("hp", "HP Omen 16", "Intel Core i7-14650HX", "NVIDIA RTX 4070", 16, 1024, 16.1, "2560 x 1600", 2.35, 83, 188000),
        ("hp", "HP Envy x360 15", "AMD Ryzen 7 7730U", "AMD Radeon Graphics", 16, 512, 15.6, "1920 x 1080", 1.71, 51, 92000),
        ("hp", "HP Spectre x360 14", "Intel Core Ultra 7 155H", "Intel Arc", 16, 1024, 14.0, "2880 x 1800", 1.44, 68, 168000),
        ("lenovo", "Lenovo IdeaPad Slim 3 15", "Intel Core i5-12450H", "Intel UHD Graphics", 8, 512, 15.6, "1920 x 1080", 1.62, 47, 58000),
        ("lenovo", "Lenovo IdeaPad Slim 3 15", "AMD Ryzen 5 7520U", "AMD Radeon 610M", 8, 256, 15.6, "1920 x 1080", 1.62, 47, 52000),
        ("lenovo", "Lenovo IdeaPad Slim 5 14", "Intel Core Ultra 5 125H", "Intel Arc", 16, 512, 14.0, "1920 x 1200", 1.46, 57, 95000),
        ("lenovo", "Lenovo IdeaPad Gaming 3", "AMD Ryzen 5 6600H", "NVIDIA RTX 3050", 8, 512, 15.6, "1920 x 1080", 2.32, 45, 82000),
        ("lenovo", "Lenovo LOQ 15", "Intel Core i5-12450HX", "NVIDIA RTX 4050", 12, 512, 15.6, "1920 x 1080", 2.38, 60, 108000),
        ("lenovo", "Lenovo LOQ 15", "Intel Core i7-13650HX", "NVIDIA RTX 4060", 16, 512, 15.6, "1920 x 1080", 2.38, 60, 134000),
        ("lenovo", "Lenovo Legion 5", "Intel Core i5-13450HX", "NVIDIA RTX 4060", 16, 512, 15.6, "1920 x 1080", 2.4, 80, 148000),
        ("lenovo", "Lenovo Legion 5", "AMD Ryzen 7 7745HX", "NVIDIA RTX 4070", 16, 1024, 15.6, "2560 x 1600", 2.4, 80, 178000),
        ("lenovo", "Lenovo Legion Pro 5", "Intel Core i9-14900HX", "NVIDIA RTX 4070", 16, 1024, 16.0, "2560 x 1600", 2.55, 80, 208000),
        ("lenovo", "Lenovo Legion Pro 5", "Intel Core i9-14900HX", "NVIDIA RTX 4080", 32, 1024, 16.0, "2560 x 1600", 2.55, 80, 268000),
        ("lenovo", "Lenovo Legion Slim 5", "AMD Ryzen 7 7840HS", "NVIDIA RTX 4060", 16, 1024, 16.0, "2560 x 1600", 2.3, 80, 158000),
        ("lenovo", "Lenovo Legion 7i", "Intel Core Ultra 9 185H", "NVIDIA RTX 4080", 32, 1024, 16.0, "2560 x 1600", 2.54, 99.9, 298000),
        ("lenovo", "Lenovo ThinkPad E14 Gen 5", "Intel Core i5-1335U", "Intel Iris Xe", 8, 512, 14.0, "1920 x 1080", 1.44, 57, 96000),
        ("lenovo", "Lenovo ThinkPad E14 Gen 5", "Intel Core i7-1355U", "Intel Iris Xe", 16, 512, 14.0, "1920 x 1080", 1.44, 57, 112000),
        ("lenovo", "Lenovo ThinkPad T14 Gen 4", "Intel Core i7-1365U", "Intel Iris Xe", 16, 512, 14.0, "1920 x 1200", 1.36, 52.5, 142000),
        ("asus", "ASUS Vivobook 14 X1404", "Intel Core i3-N305", "Intel UHD Graphics", 8, 256, 14.0, "1920 x 1080", 1.5, 42, 48000),
        ("asus", "ASUS Vivobook 15 X1504", "Intel Core i5-1235U", "Intel Iris Xe", 8, 512, 15.6, "1920 x 1080", 1.7, 42, 58000),
        ("asus", "ASUS Vivobook 15 X1504", "Intel Core i7-1355U", "Intel Iris Xe", 16, 512, 15.6, "1920 x 1080", 1.7, 42, 72000),
        ("asus", "ASUS Vivobook 16 X1605", "AMD Ryzen 7 7730U", "AMD Radeon Graphics", 16, 512, 16.0, "1920 x 1080", 1.88, 50, 78000),
        ("asus", "ASUS Vivobook S14 OLED", "Intel Core Ultra 5 125H", "Intel Arc", 16, 512, 14.0, "2880 x 1800", 1.29, 75, 106000),
        ("asus", "ASUS TUF Gaming F15", "Intel Core i5-12500H", "NVIDIA RTX 3050", 16, 512, 15.6, "1920 x 1080", 2.2, 56, 96000),
        ("asus", "ASUS TUF Gaming F15", "Intel Core i7-12700H", "NVIDIA RTX 4060", 16, 1024, 15.6, "1920 x 1080", 2.2, 56, 136000),
        ("asus", "ASUS TUF Gaming A15", "AMD Ryzen 7 7735HS", "NVIDIA RTX 4050", 16, 512, 15.6, "1920 x 1080", 2.2, 90, 120000),
        ("asus", "ASUS TUF Gaming A15", "AMD Ryzen 7 7735HS", "NVIDIA RTX 4060", 16, 1024, 15.6, "1920 x 1080", 2.2, 90, 138000),
        ("asus", "ASUS TUF Gaming F16", "Intel Core i7-13650HX", "NVIDIA RTX 4060", 16, 1024, 16.0, "1920 x 1200", 2.2, 90, 142000),
        ("asus", "ASUS ROG Strix G16", "Intel Core i7-13650HX", "NVIDIA RTX 4060", 16, 512, 16.0, "1920 x 1200", 2.5, 90, 168000),
        ("asus", "ASUS ROG Strix G16", "Intel Core i9-14900HX", "NVIDIA RTX 4070", 16, 1024, 16.0, "2560 x 1600", 2.5, 90, 208000),
        ("asus", "ASUS ROG Strix SCAR 16", "Intel Core i9-14900HX", "NVIDIA RTX 4080", 32, 2048, 16.0, "2560 x 1600", 2.5, 90, 325000),
        ("asus", "ASUS ROG Zephyrus G14", "AMD Ryzen 9 8945HS", "NVIDIA RTX 4060", 16, 1024, 14.0, "2560 x 1600", 1.5, 73, 198000),
        ("asus", "ASUS ROG Zephyrus M16", "Intel Core Ultra 9 185H", "NVIDIA RTX 4070", 16, 1024, 16.0, "2560 x 1600", 1.95, 90, 242000),
        ("asus", "ASUS ExpertBook B1", "Intel Core i5-1235U", "Intel Iris Xe", 8, 512, 14.0, "1920 x 1080", 1.45, 42, 75000),
        ("acer", "Acer Aspire 5 A515", "Intel Core i5-1235U", "Intel Iris Xe", 8, 512, 15.6, "1920 x 1080", 1.78, 50, 60000),
        ("acer", "Acer Aspire 5 A515", "Intel Core i7-1355U", "Intel Iris Xe", 16, 512, 15.6, "1920 x 1080", 1.78, 50, 74000),
        ("acer", "Acer Aspire 7 A715", "Intel Core i5-12450H", "NVIDIA RTX 3050", 8, 512, 15.6, "1920 x 1080", 1.99, 50, 85000),
        ("acer", "Acer Aspire 7 A715", "AMD Ryzen 5 7535HS", "NVIDIA RTX 2050", 16, 512, 15.6, "1920 x 1080", 1.99, 50, 78000),
        ("acer", "Acer Aspire Vero 15", "Intel Core i7-1355U", "Intel Iris Xe", 16, 512, 15.6, "1920 x 1080", 1.8, 53, 95000),
        ("acer", "Acer Nitro 5", "Intel Core i5-12450H", "NVIDIA RTX 3050", 8, 512, 15.6, "1920 x 1080", 2.2, 57.5, 88000),
        ("acer", "Acer Nitro 5", "AMD Ryzen 7 7735HS", "NVIDIA RTX 4050", 16, 512, 15.6, "1920 x 1080", 2.2, 57.5, 108000),
        ("acer", "Acer Nitro 16", "AMD Ryzen 7 7840HS", "NVIDIA RTX 4060", 16, 1024, 16.0, "2560 x 1600", 2.3, 90, 138000),
        ("acer", "Acer Predator Helios Neo 16", "Intel Core i7-13650HX", "NVIDIA RTX 4060", 16, 512, 16.0, "1920 x 1200", 2.7, 90, 152000),
        ("acer", "Acer Predator Helios Neo 16", "Intel Core i7-13650HX", "NVIDIA RTX 4070", 16, 1024, 16.0, "2560 x 1600", 2.7, 90, 178000),
        ("acer", "Acer Predator Helios 300", "Intel Core i7-12700H", "NVIDIA RTX 3060", 16, 1024, 15.6, "1920 x 1080", 2.4, 90, 135000),
        ("acer", "Acer Predator Triton 14", "Intel Core Ultra 7 155H", "NVIDIA RTX 4050", 16, 1024, 14.0, "2560 x 1600", 1.69, 76, 195000),
        ("msi", "MSI Katana 15", "Intel Core i7-13620H", "NVIDIA RTX 4050", 16, 512, 15.6, "1920 x 1080", 2.25, 53.5, 112000),
        ("msi", "MSI Katana 15", "Intel Core i7-13620H", "NVIDIA RTX 4060", 16, 1024, 15.6, "1920 x 1080", 2.25, 53.5, 132000),
        ("msi", "MSI Katana 17", "Intel Core i7-13620H", "NVIDIA RTX 4070", 16, 1024, 17.3, "1920 x 1080", 2.6, 53.5, 160000),
        ("msi", "MSI Cyborg 15", "Intel Core i5-12450H", "NVIDIA RTX 2050", 8, 512, 15.6, "1920 x 1080", 1.98, 53.5, 72000),
        ("msi", "MSI Cyborg 15", "Intel Core i5-12450H", "NVIDIA RTX 3050", 16, 512, 15.6, "1920 x 1080", 1.98, 53.5, 86000),
        ("msi", "MSI GF63 Thin", "Intel Core i5-11400H", "NVIDIA GTX 1650", 8, 512, 15.6, "1920 x 1080", 1.86, 51, 65000),
        ("msi", "MSI GF63 Thin", "Intel Core i5-12450H", "NVIDIA RTX 3050", 16, 512, 15.6, "1920 x 1080", 1.86, 51, 84000),
        ("msi", "MSI Modern 14", "Intel Core i5-1235U", "Intel Iris Xe", 16, 512, 14.0, "1920 x 1080", 1.4, 39.3, 58000),
        ("msi", "MSI Modern 15", "AMD Ryzen 7 7730U", "AMD Radeon Graphics", 16, 512, 15.6, "1920 x 1080", 1.7, 52, 72000),
        ("msi", "MSI Vector GP68", "Intel Core i7-13650HX", "NVIDIA RTX 4070", 16, 1024, 16.0, "1920 x 1200", 2.6, 65, 188000),
        ("msi", "MSI Raider GE78 HX", "Intel Core i9-13980HX", "NVIDIA RTX 4080", 32, 2048, 17.0, "2560 x 1600", 3.1, 99.9, 335000),
        ("samsung", "Samsung Galaxy Book3 15", "Intel Core i5-1335U", "Intel Iris Xe", 8, 256, 15.6, "1920 x 1080", 1.55, 54, 105000),
        ("samsung", "Samsung Galaxy Book3 Pro 14", "Intel Core Ultra 7 155H", "Intel Arc", 16, 512, 14.0, "2880 x 1800", 1.23, 63, 168000),
        ("samsung", "Samsung Galaxy Book4 15", "Intel Core Ultra 5 125H", "Intel Arc", 8, 256, 15.6, "1920 x 1080", 1.55, 54, 125000),
        ("samsung", "Samsung Galaxy Book4 Pro 16", "Intel Core Ultra 7 155H", "Intel Arc", 16, 512, 16.0, "2880 x 1800", 1.55, 76, 215000),
        ("apple", "MacBook Air M4 13", "Apple M4", "Apple M4 10-core", 16, 256, 13.6, "2560 x 1664", 1.24, 53.8, 159000),
        ("apple", "MacBook Air M4 15", "Apple M4", "Apple M4 10-core", 16, 256, 15.3, "2880 x 1864", 1.51, 66.5, 179000),
        ("dell", "Dell Inspiron 14 3420", "Intel Core i3-1215U", "Intel UHD Graphics", 8, 256, 14.0, "1920 x 1080", 1.5, 42, 48000),
        ("dell", "Dell Vostro 15 3530", "Intel Core i5-1335U", "Intel Iris Xe", 8, 512, 15.6, "1920 x 1080", 1.65, 41, 68000),
        ("hp", "HP 15s", "Intel Core i5-1235U", "Intel Iris Xe", 8, 512, 15.6, "1920 x 1080", 1.69, 41, 58000),
        ("hp", "HP Victus 16", "Intel Core i5-13420H", "NVIDIA RTX 3050", 8, 512, 16.1, "1920 x 1200", 2.3, 70, 105000),
        ("lenovo", "Lenovo IdeaPad Slim 5 16", "AMD Ryzen 7 8845HS", "AMD Radeon 780M", 16, 512, 16.0, "1920 x 1200", 1.89, 65, 105000),
        ("lenovo", "Lenovo ThinkBook 15", "Intel Core i7-1355U", "Intel Iris Xe", 16, 512, 15.6, "1920 x 1080", 1.7, 60, 92000),
        ("asus", "ASUS Vivobook Go 15", "AMD Ryzen 5 7520U", "AMD Radeon 610M", 8, 256, 15.6, "1920 x 1080", 1.63, 42, 50000),
        ("asus", "ASUS Zenbook 14 OLED", "Intel Core Ultra 7 155H", "Intel Arc", 16, 1024, 14.0, "2880 x 1800", 1.2, 75, 145000),
        ("acer", "Acer Swift Go 14", "Intel Core Ultra 5 125H", "Intel Arc", 16, 512, 14.0, "2880 x 1800", 1.32, 65, 110000),
        ("msi", "MSI Thin 15", "Intel Core i5-12450H", "NVIDIA RTX 2050", 16, 512, 15.6, "1920 x 1080", 1.86, 52.4, 78000),
        ("msi", "MSI Bravo 15", "AMD Ryzen 5 7535HS", "NVIDIA RTX 4050", 16, 512, 15.6, "1920 x 1080", 2.3, 53.5, 105000),
    ]
    out = []
    for brand, name, cpu, gpu, ram, sto, size, res, wt, bat, price in L:
        out.append({
            "name": f"{name} ({ram}GB/{sto}GB)" if (ram, sto) != (16, 512) else name,
            "brand": brand,
            "price": price,
            "compare_at": None,
            "specs": {
                "cpu": cpu, "ram_gb": str(ram), "storage_type": "SSD", "storage_gb": str(sto),
                "display_size": str(size), "display_resolution": res, "gpu": gpu,
                "battery_wh": str(bat), "weight_kg": str(wt),
                "os": "macOS" if brand == "apple" else "Windows 11",
            },
        })
        # Upgraded variant for base configs (16GB/1TB, price bump)
        if ram <= 8 and sto <= 512:
            out.append({
                "name": f"{name} ({16}GB/{1024}GB Upgrade)",
                "brand": brand,
                "price": price + 14000,
                "compare_at": None,
                "specs": {
                    "cpu": cpu, "ram_gb": "16", "storage_type": "SSD", "storage_gb": "1024",
                    "display_size": str(size), "display_resolution": res, "gpu": gpu,
                    "battery_wh": str(bat), "weight_kg": str(wt),
                    "os": "macOS" if brand == "apple" else "Windows 11",
                },
            })
    return out


def gen_phones():
    """(brand, name, chipset, ram, storage, size, res, refresh, camera, battery, price)"""
    P = [
        ("samsung", "Samsung Galaxy S24 FE", "Exynos 2400e", 8, 256, 6.7, "2340 x 1080", 120, 50, 4700, 85000),
        ("samsung", "Samsung Galaxy S24", "Exynos 2400", 8, 256, 6.2, "2340 x 1080", 120, 50, 4000, 98000),
        ("samsung", "Samsung Galaxy S24+", "Exynos 2400", 12, 256, 6.7, "3120 x 1440", 120, 50, 4900, 115000),
        ("samsung", "Samsung Galaxy S23 FE", "Exynos 2200", 8, 128, 6.4, "2340 x 1080", 120, 50, 4500, 65000),
        ("samsung", "Samsung Galaxy S23", "Snapdragon 8 Gen 2 for Galaxy", 8, 128, 6.1, "2340 x 1080", 120, 50, 3900, 85000),
        ("samsung", "Samsung Galaxy S23 Ultra", "Snapdragon 8 Gen 2 for Galaxy", 12, 256, 6.8, "3088 x 1440", 120, 200, 5000, 125000),
        ("samsung", "Samsung Galaxy S22", "Snapdragon 8 Gen 1", 8, 128, 6.1, "2340 x 1080", 120, 50, 3700, 55000),
        ("samsung", "Samsung Galaxy A15", "MediaTek Helio G99", 4, 128, 6.5, "2340 x 1080", 90, 50, 5000, 22000),
        ("samsung", "Samsung Galaxy A15 5G", "MediaTek Dimensity 6100+", 4, 128, 6.5, "2340 x 1080", 90, 50, 5000, 26000),
        ("samsung", "Samsung Galaxy A25 5G", "Exynos 1280", 8, 128, 6.5, "2340 x 1080", 120, 50, 5000, 30000),
        ("samsung", "Samsung Galaxy A35 5G", "Exynos 1380", 8, 128, 6.6, "2340 x 1080", 120, 50, 5000, 35000),
        ("samsung", "Samsung Galaxy A55 5G", "Exynos 1480", 8, 128, 6.6, "2340 x 1080", 120, 50, 5000, 40000),
        ("samsung", "Samsung Galaxy A55 5G (256GB)", "Exynos 1480", 8, 256, 6.6, "2340 x 1080", 120, 50, 5000, 44000),
        ("samsung", "Samsung Galaxy M34 5G", "Exynos 1280", 6, 128, 6.5, "2400 x 1080", 120, 50, 6000, 24000),
        ("samsung", "Samsung Galaxy A05s", "Snapdragon 680", 4, 128, 6.7, "2400 x 1080", 90, 50, 5000, 17000),
        ("samsung", "Samsung Galaxy Z Flip 5", "Snapdragon 8 Gen 2 for Galaxy", 8, 256, 6.7, "2640 x 1080", 120, 12, 3700, 120000),
        ("samsung", "Samsung Galaxy Z Flip 6", "Snapdragon 8 Gen 3", 12, 256, 6.7, "2640 x 1080", 120, 50, 4000, 150000),
        ("samsung", "Samsung Galaxy Z Fold 5", "Snapdragon 8 Gen 2 for Galaxy", 12, 256, 7.6, "2176 x 1812", 120, 50, 4400, 185000),
        ("samsung", "Samsung Galaxy Z Fold 6", "Snapdragon 8 Gen 3", 12, 256, 7.6, "2160 x 1856", 120, 50, 4400, 215000),
        ("apple", "iPhone 13", "Apple A15 Bionic", 4, 128, 6.1, "2532 x 1170", 60, 12, 3240, 95000),
        ("apple", "iPhone 14", "Apple A15 Bionic", 6, 128, 6.1, "2532 x 1170", 60, 12, 3279, 110000),
        ("apple", "iPhone 14 Plus", "Apple A15 Bionic", 6, 128, 6.7, "2778 x 1284", 60, 12, 4325, 125000),
        ("apple", "iPhone 14 Pro", "Apple A16 Bionic", 6, 128, 6.1, "2556 x 1179", 120, 48, 3200, 145000),
        ("apple", "iPhone 14 Pro Max", "Apple A16 Bionic", 6, 128, 6.7, "2796 x 1290", 120, 48, 4323, 160000),
        ("apple", "iPhone 15", "Apple A16 Bionic", 6, 128, 6.1, "2556 x 1179", 60, 48, 3349, 148000),
        ("apple", "iPhone 15 (256GB)", "Apple A16 Bionic", 6, 256, 6.1, "2556 x 1179", 60, 48, 3349, 163000),
        ("apple", "iPhone 15 Plus", "Apple A16 Bionic", 6, 128, 6.7, "2796 x 1290", 60, 48, 4383, 162000),
        ("apple", "iPhone 15 Pro", "Apple A17 Pro", 8, 128, 6.1, "2556 x 1179", 120, 48, 3274, 172000),
        ("apple", "iPhone 15 Pro Max", "Apple A17 Pro", 8, 256, 6.7, "2796 x 1290", 120, 48, 4441, 195000),
        ("apple", "iPhone 16", "Apple A18", 8, 128, 6.1, "2556 x 1179", 60, 48, 3561, 155000),
        ("apple", "iPhone 16 Plus", "Apple A18", 8, 128, 6.7, "2796 x 1290", 60, 48, 4674, 170000),
        ("apple", "iPhone 16 Pro", "Apple A18 Pro", 8, 128, 6.3, "2622 x 1206", 120, 48, 3582, 190000),
        ("apple", "iPhone 16 Pro Max", "Apple A18 Pro", 8, 256, 6.9, "2868 x 1320", 120, 48, 4685, 215000),
        ("xiaomi", "Xiaomi 13T Pro", "MediaTek Dimensity 9200+", 12, 256, 6.67, "2712 x 1220", 144, 50, 5000, 80000),
        ("xiaomi", "Xiaomi 14T Pro", "MediaTek Dimensity 9300+", 12, 512, 6.67, "2712 x 1220", 144, 50, 5000, 95000),
        ("xiaomi", "Xiaomi 14 Ultra", "Snapdragon 8 Gen 3", 16, 512, 6.73, "3200 x 1440", 120, 50, 5300, 135000),
        ("xiaomi", "Redmi Note 12", "Snapdragon 685", 8, 128, 6.67, "2400 x 1080", 120, 50, 5000, 20000),
        ("xiaomi", "Redmi Note 12 Pro", "MediaTek Dimensity 1080", 8, 256, 6.67, "2400 x 1080", 120, 50, 5000, 28000),
        ("xiaomi", "Redmi Note 13", "Snapdragon 685", 8, 128, 6.67, "2400 x 1080", 120, 108, 5000, 22000),
        ("xiaomi", "Redmi Note 13 Pro", "Snapdragon 7s Gen 2", 8, 256, 6.67, "2712 x 1220", 120, 200, 5100, 32000),
        ("xiaomi", "Redmi Note 13 Pro+", "MediaTek Dimensity 7200 Ultra", 12, 512, 6.67, "2712 x 1220", 120, 200, 5000, 42000),
        ("xiaomi", "Poco X6", "Snapdragon 7s Gen 2", 8, 256, 6.67, "2712 x 1220", 120, 64, 5100, 30000),
        ("xiaomi", "Poco X6 Pro", "MediaTek Dimensity 8300 Ultra", 12, 512, 6.67, "2712 x 1220", 120, 64, 5000, 38000),
        ("xiaomi", "Poco F5", "Snapdragon 7+ Gen 2", 8, 256, 6.67, "2400 x 1080", 120, 64, 5000, 35000),
        ("xiaomi", "Poco F6", "Snapdragon 8s Gen 3", 12, 512, 6.67, "2712 x 1220", 120, 50, 5000, 45000),
        ("xiaomi", "Poco M6 Pro", "MediaTek Helio G99 Ultra", 8, 256, 6.67, "2400 x 1080", 120, 64, 5000, 22000),
        ("xiaomi", "Poco C65", "MediaTek Helio G85", 6, 128, 6.74, "1600 x 720", 90, 50, 5000, 14000),
        ("oneplus", "OnePlus Nord CE 4", "Snapdragon 7 Gen 3", 8, 128, 6.7, "2412 x 1080", 120, 50, 5500, 32000),
        ("oneplus", "OnePlus Nord 3", "MediaTek Dimensity 9000", 8, 128, 6.74, "2772 x 1240", 120, 50, 5000, 40000),
        ("oneplus", "OnePlus Nord 4", "Snapdragon 7+ Gen 3", 8, 256, 6.74, "2772 x 1240", 120, 50, 5500, 48000),
        ("oneplus", "OnePlus 11R", "Snapdragon 8+ Gen 1", 8, 128, 6.74, "2772 x 1240", 120, 50, 5000, 52000),
        ("oneplus", "OnePlus 11", "Snapdragon 8 Gen 2", 16, 256, 6.7, "3216 x 1440", 120, 50, 5000, 85000),
        ("oneplus", "OnePlus 12R", "Snapdragon 8 Gen 2", 8, 256, 6.78, "2780 x 1264", 120, 50, 5500, 60000),
        ("oneplus", "OnePlus 13", "Snapdragon 8 Elite", 12, 256, 6.82, "3168 x 1440", 120, 50, 6000, 95000),
        ("google", "Google Pixel 6a", "Google Tensor", 6, 128, 6.1, "2400 x 1080", 60, 12.2, 4410, 38000),
        ("google", "Google Pixel 7a", "Google Tensor G2", 8, 128, 6.1, "2400 x 1080", 90, 64, 4385, 52000),
        ("google", "Google Pixel 8a", "Google Tensor G3", 8, 128, 6.1, "2400 x 1080", 120, 64, 4492, 58000),
        ("google", "Google Pixel 8", "Google Tensor G3", 8, 128, 6.2, "2400 x 1080", 120, 50, 4575, 85000),
        ("google", "Google Pixel 8 Pro", "Google Tensor G3", 12, 128, 6.7, "2992 x 1344", 120, 50, 5050, 115000),
        ("google", "Google Pixel 9", "Google Tensor G4", 12, 256, 6.3, "2424 x 1080", 120, 50, 4700, 105000),
        ("google", "Google Pixel 9 Pro XL", "Google Tensor G4", 16, 256, 6.8, "3200 x 1344", 120, 50, 5060, 145000),
        ("realme", "realme 12 Pro", "Snapdragon 6 Gen 1", 12, 256, 6.7, "2412 x 1080", 120, 50, 5000, 38000),
        ("realme", "realme 12 Pro+", "Snapdragon 7s Gen 2", 12, 256, 6.7, "2412 x 1080", 120, 64, 5000, 48000),
        ("realme", "realme GT 6", "Snapdragon 8s Gen 3", 12, 256, 6.78, "2780 x 1264", 120, 50, 5500, 60000),
        ("realme", "realme Narzo 70 Pro", "MediaTek Dimensity 7050", 8, 128, 6.67, "2400 x 1080", 120, 50, 5000, 28000),
        ("realme", "realme C67", "Snapdragon 685", 8, 128, 6.72, "2400 x 1080", 90, 108, 5000, 18000),
        ("vivo", "vivo V29e", "Snapdragon 695", 8, 256, 6.67, "2400 x 1080", 120, 64, 5000, 38000),
        ("vivo", "vivo V30", "Snapdragon 7 Gen 3", 12, 256, 6.78, "2800 x 1260", 120, 50, 5000, 55000),
        ("vivo", "vivo V40", "Snapdragon 7 Gen 3", 12, 256, 6.78, "2800 x 1260", 120, 50, 5500, 60000),
        ("vivo", "vivo X100", "MediaTek Dimensity 9300", 12, 256, 6.78, "2800 x 1260", 120, 50, 5000, 105000),
        ("vivo", "vivo Y200", "Snapdragon 4 Gen 2", 8, 128, 6.67, "2400 x 1080", 120, 50, 4800, 25000),
        ("oppo", "Oppo Reno 11F", "MediaTek Dimensity 7050", 8, 256, 6.7, "2412 x 1080", 120, 64, 5000, 38000),
        ("oppo", "Oppo Reno 12", "MediaTek Dimensity 8300", 12, 256, 6.7, "2412 x 1080", 120, 50, 5000, 55000),
        ("oppo", "Oppo Reno 12 Pro", "MediaTek Dimensity 7300", 12, 512, 6.7, "2412 x 1080", 120, 50, 5000, 65000),
        ("oppo", "Oppo A78", "Snapdragon 680", 8, 128, 6.56, "1612 x 720", 90, 50, 5000, 24000),
        ("oppo", "Oppo Find N3 Flip", "MediaTek Dimensity 9200", 12, 256, 6.8, "2520 x 1080", 120, 50, 4300, 130000),
        ("samsung", "Samsung Galaxy S23 Plus", "Snapdragon 8 Gen 2 for Galaxy", 8, 256, 6.6, "2340 x 1080", 120, 50, 4700, 105000),
        ("samsung", "Samsung Galaxy M15 5G", "MediaTek Dimensity 6100+", 4, 128, 6.5, "2340 x 1080", 90, 50, 6000, 24000),
        ("samsung", "Samsung Galaxy F14 5G", "Exynos 1330", 4, 128, 6.6, "2400 x 1080", 90, 50, 6000, 20000),
        ("samsung", "Samsung Galaxy A06", "MediaTek Helio G85", 4, 64, 6.7, "1600 x 720", 60, 50, 5000, 14000),
        ("apple", "iPhone 12", "Apple A14 Bionic", 4, 64, 6.1, "2532 x 1170", 60, 12, 2815, 72000),
        ("apple", "iPhone 11", "Apple A13 Bionic", 4, 64, 6.1, "1792 x 828", 60, 12, 3110, 55000),
        ("xiaomi", "Xiaomi Redmi 13C", "MediaTek Helio G85", 6, 128, 6.74, "1650 x 720", 90, 50, 5000, 15000),
        ("xiaomi", "Xiaomi Redmi 13", "MediaTek Helio G91 Ultra", 8, 128, 6.79, "2460 x 1080", 90, 108, 5030, 19000),
        ("xiaomi", "Xiaomi Redmi A3", "MediaTek Helio G36", 3, 64, 6.71, "1650 x 720", 90, 8, 5000, 11000),
        ("xiaomi", "Xiaomi 14T", "MediaTek Dimensity 8300 Ultra", 12, 256, 6.67, "2712 x 1220", 144, 50, 5000, 72000),
        ("xiaomi", "Poco M6 Plus", "Snapdragon 4 Gen 2", 6, 128, 6.79, "2460 x 1080", 90, 108, 5030, 18000),
        ("oneplus", "OnePlus Nord CE 3 Lite", "Snapdragon 695", 8, 128, 6.72, "2412 x 1080", 120, 108, 5000, 27000),
        ("oneplus", "OnePlus Nord N30 SE", "MediaTek Dimensity 6020", 4, 128, 6.56, "1612 x 720", 90, 13, 5000, 17000),
        ("google", "Google Pixel 7", "Google Tensor G2", 8, 128, 6.3, "2400 x 1080", 90, 50, 4355, 72000),
        ("realme", "realme C53", "Unisoc T612", 6, 128, 6.74, "1600 x 720", 90, 108, 5000, 16000),
        ("realme", "realme C55", "MediaTek Helio G88", 8, 128, 6.72, "2400 x 1080", 90, 64, 5000, 20000),
        ("realme", "realme Note 60", "Unisoc T612", 4, 64, 6.74, "1600 x 720", 90, 13, 5000, 13000),
        ("vivo", "vivo Y17s", "MediaTek Helio G85", 4, 128, 6.56, "1612 x 720", 90, 50, 5000, 16000),
        ("vivo", "vivo Y28 5G", "MediaTek Dimensity 6020", 6, 128, 6.56, "1612 x 720", 90, 50, 5000, 22000),
        ("vivo", "vivo V40 Pro", "MediaTek Dimensity 9200+", 12, 512, 6.78, "2800 x 1260", 120, 50, 5500, 85000),
        ("oppo", "Oppo A18", "MediaTek Helio G85", 4, 128, 6.56, "1612 x 720", 90, 8, 5000, 14000),
        ("oppo", "Oppo A38", "Snapdragon 680", 4, 128, 6.56, "1612 x 720", 90, 50, 5000, 17000),
        ("oppo", "Oppo Reno 11", "MediaTek Dimensity 7050", 12, 256, 6.7, "2412 x 1080", 120, 50, 4800, 48000),
        ("infinix", "Infinix Hot 40", "MediaTek Helio G88", 8, 128, 6.78, "2460 x 1080", 90, 108, 5000, 15000),
        ("infinix", "Infinix Note 40", "MediaTek Helio G99 Ultimate", 8, 256, 6.78, "2436 x 1080", 120, 108, 5000, 22000),
        ("infinix", "Infinix GT 20 Pro", "MediaTek Dimensity 8200 Ultimate", 12, 256, 6.78, "2400 x 1080", 144, 108, 5000, 32000),
        ("tecno", "Tecno Camon 30", "MediaTek Helio G99 Ultimate", 8, 256, 6.78, "2436 x 1080", 120, 50, 5000, 25000),
        ("tecno", "Tecno Spark 20 Pro", "MediaTek Helio G99", 8, 256, 6.78, "2460 x 1080", 120, 108, 5000, 18000),
        ("sony", "Sony Xperia 5 V", "Snapdragon 8 Gen 2", 8, 256, 6.1, "2520 x 1080", 120, 48, 5000, 115000),
        ("sony", "Sony Xperia 10 VI", "Snapdragon 6 Gen 1", 8, 128, 6.1, "2520 x 1080", 90, 48, 5000, 45000),
    ]
    out = []
    for brand, name, chip, ram, sto, size, res, hz, cam, mah, price in P:
        out.append({
            "name": name,
            "brand": brand,
            "price": price,
            "compare_at": None,
            "specs": {
                "chipset": chip, "ram_gb": str(ram), "storage_gb": str(sto),
                "display_size": str(size), "display_resolution": res,
                "refresh_rate": str(hz), "camera_mp": str(cam), "battery_mah": str(mah),
                "os": "iOS" if brand == "apple" else "Android",
            },
        })
    return out


def gen_monitors():
    """(brand, name, size, res, refresh, panel, response, hdr, price)"""
    M = [
        ("lg", "LG UltraGear 24GN60R", 24, "1920 x 1080", 144, "IPS", 1, "HDR10", 22000),
        ("lg", "LG UltraGear 24GS60F", 24, "1920 x 1080", 180, "Fast IPS", 1, "HDR10", 20000),
        ("lg", "LG UltraGear 27GP850-B", 27, "2560 x 1440", 165, "Nano IPS", 1, "HDR400", 42000),
        ("lg", "LG UltraGear 32GP850-B", 32, "2560 x 1440", 165, "Nano IPS", 1, "HDR400", 52000),
        ("lg", "LG UltraGear 27GR95QE", 27, "2560 x 1440", 240, "OLED", 0.03, "HDR10", 110000),
        ("lg", "LG UltraGear 32GS95UE", 32, "3840 x 2160", 240, "OLED", 0.03, "HDR10", 180000),
        ("lg", "LG UltraGear 27GR93U", 27, "3840 x 2160", 144, "Fast IPS", 1, "HDR400", 85000),
        ("lg", "LG UltraWide 34WP65C-B", 34, "3440 x 1440", 160, "VA", 5, "HDR10", 65000),
        ("lg", "LG 27UP650-W", 27, "3840 x 2160", 60, "IPS", 5, "HDR10", 48000),
        ("lg", "LG 24MP400-B", 24, "1920 x 1080", 75, "IPS", 5, "No HDR", 13000),
        ("lg", "LG 27MP400-B", 27, "1920 x 1080", 75, "IPS", 5, "No HDR", 15500),
        ("samsung", "Samsung Odyssey G3 24", 24, "1920 x 1080", 144, "VA", 1, "No HDR", 18000),
        ("samsung", "Samsung Odyssey G3 27", 27, "1920 x 1080", 165, "VA", 1, "No HDR", 21000),
        ("samsung", "Samsung Odyssey G5 27", 27, "2560 x 1440", 165, "VA Curved", 1, "No HDR", 30000),
        ("samsung", "Samsung Odyssey G5 32", 32, "2560 x 1440", 165, "VA Curved", 1, "No HDR", 35000),
        ("samsung", "Samsung Odyssey G7 27", 27, "2560 x 1440", 240, "VA QLED Curved", 1, "HDR600", 48000),
        ("samsung", "Samsung Odyssey OLED G8 34", 34, "3440 x 1440", 175, "OLED", 0.03, "HDR400", 130000),
        ("samsung", "Samsung Odyssey Neo G7 32", 32, "3840 x 2160", 165, "Mini LED", 1, "HDR2000", 110000),
        ("samsung", "Samsung Odyssey OLED G9 49", 49, "5120 x 1440", 240, "OLED", 0.03, "HDR400", 165000),
        ("samsung", "Samsung Odyssey OLED G6 27", 27, "2560 x 1440", 360, "OLED", 0.03, "HDR400", 135000),
        ("samsung", "Samsung S27C310", 27, "1920 x 1080", 75, "VA", 5, "No HDR", 15500),
        ("asus", "ASUS TUF Gaming VG249Q1A", 24, "1920 x 1080", 165, "IPS", 1, "No HDR", 20000),
        ("asus", "ASUS TUF Gaming VG249QM1A", 24, "1920 x 1080", 270, "Fast IPS", 1, "No HDR", 28000),
        ("asus", "ASUS TUF Gaming VG27AQ3A", 27, "2560 x 1440", 180, "Fast IPS", 1, "HDR400", 38000),
        ("asus", "ASUS TUF Gaming VG28UQL1A", 28, "3840 x 2160", 144, "Fast IPS", 1, "HDR400", 75000),
        ("asus", "ASUS ROG Strix XG27AQ", 27, "2560 x 1440", 170, "Fast IPS", 1, "HDR400", 52000),
        ("asus", "ASUS ROG Strix XG27ACS", 27, "2560 x 1440", 180, "Fast IPS", 1, "HDR400", 45000),
        ("asus", "ASUS ROG Swift PG27AQN", 27, "2560 x 1440", 360, "Fast IPS", 1, "HDR600", 210000),
        ("asus", "ASUS ProArt PA278CV", 27, "2560 x 1440", 75, "IPS", 5, "No HDR", 42000),
        ("asus", "ASUS ProArt PA329C", 32, "3840 x 2160", 60, "IPS", 5, "HDR600", 115000),
        ("asus", "ASUS VA24EHE", 24, "1920 x 1080", 75, "VA", 5, "No HDR", 11500),
        ("dell", "Dell S2421HN", 24, "1920 x 1080", 75, "VA", 4, "No HDR", 14000),
        ("dell", "Dell S2721DS", 27, "2560 x 1440", 75, "IPS", 4, "No HDR", 30000),
        ("dell", "Dell S2721HGF", 27, "1920 x 1080", 144, "VA Curved", 1, "No HDR", 26000),
        ("dell", "Dell G2422HS", 24, "1920 x 1080", 100, "Fast IPS", 1, "No HDR", 17000),
        ("dell", "Dell G2724D", 27, "2560 x 1440", 165, "Fast IPS", 1, "No HDR", 32000),
        ("dell", "Dell G3223Q", 32, "3840 x 2160", 144, "Fast IPS", 1, "HDR600", 95000),
        ("dell", "Dell U2723QE", 27, "3840 x 2160", 60, "IPS Black", 5, "HDR400", 85000),
        ("dell", "Dell U3421WE", 34, "3440 x 1440", 60, "IPS", 5, "No HDR", 105000),
        ("msi", "MSI G2412", 24, "1920 x 1080", 100, "Fast IPS", 1, "No HDR", 14500),
        ("msi", "MSI G2422", 24, "1920 x 1080", 180, "Fast IPS", 1, "No HDR", 19000),
        ("msi", "MSI G2722", 27, "1920 x 1080", 165, "Fast IPS", 1, "No HDR", 20500),
        ("msi", "MSI G273QPF", 27, "2560 x 1440", 170, "Fast IPS", 1, "No HDR", 36000),
        ("msi", "MSI MAG 274QRF QD", 27, "2560 x 1440", 170, "Fast IPS", 1, "HDR400", 42000),
        ("msi", "MSI MAG 325CQRF-QD", 32, "2560 x 1440", 170, "VA Curved", 1, "HDR400", 48000),
        ("msi", "MSI MPG 271QRX", 27, "2560 x 1440", 360, "OLED", 0.03, "HDR400", 160000),
        ("msi", "MSI MPG 321URX", 32, "3840 x 2160", 240, "OLED", 0.03, "HDR400", 185000),
        ("benq", "BenQ GW2283", 22, "1920 x 1080", 75, "IPS", 5, "No HDR", 9500),
        ("benq", "BenQ GW2480", 24, "1920 x 1080", 75, "IPS", 5, "No HDR", 11000),
        ("benq", "BenQ EX2510S", 25, "1920 x 1080", 165, "IPS", 1, "HDR400", 18000),
        ("benq", "BenQ EX2710S", 27, "1920 x 1080", 165, "IPS", 1, "HDR400", 22000),
        ("benq", "BenQ Mobiuz EX2710U", 27, "3840 x 2160", 144, "IPS", 1, "HDR600", 95000),
        ("benq", "BenQ Mobiuz EX3210U", 32, "3840 x 2160", 144, "IPS", 1, "HDR600", 125000),
        ("benq", "BenQ PD2705U", 27, "3840 x 2160", 60, "IPS", 5, "HDR400", 78000),
        ("benq", "BenQ PD3205U", 32, "3840 x 2160", 60, "IPS", 5, "No HDR", 95000),
        ("gigabyte", "Gigabyte M27Q", 27, "2560 x 1440", 170, "Fast IPS", 0.5, "HDR400", 38000),
        ("gigabyte", "Gigabyte M28U", 28, "3840 x 2160", 144, "Fast IPS", 1, "HDR400", 62000),
        ("gigabyte", "Gigabyte M32U", 32, "3840 x 2160", 144, "Fast IPS", 1, "HDR400", 78000),
        ("gigabyte", "Gigabyte AORUS FI27Q", 27, "2560 x 1440", 165, "IPS", 1, "HDR400", 42000),
        ("gigabyte", "Gigabyte AORUS FI32Q", 32, "2560 x 1440", 170, "Fast IPS", 1, "HDR400", 50000),
        ("gigabyte", "Gigabyte GS34QC", 34, "3440 x 1440", 100, "VA Curved", 2, "No HDR", 52000),
        ("hp", "HP M27f", 27, "1920 x 1080", 75, "IPS", 5, "No HDR", 15000),
        ("hp", "HP X27q", 27, "2560 x 1440", 165, "Fast IPS", 1, "No HDR", 30000),
        ("hp", "HP Omen 27q", 27, "2560 x 1440", 165, "Fast IPS", 1, "No HDR", 33000),
        ("hp", "HP Omen 27k", 27, "3840 x 2160", 144, "Fast IPS", 1, "HDR400", 60000),
        ("lenovo", "Lenovo G27q-30", 27, "2560 x 1440", 165, "Fast IPS", 1, "No HDR", 29000),
        ("lenovo", "Lenovo G24-20", 24, "1920 x 1080", 100, "VA", 4, "No HDR", 14000),
        ("lenovo", "Lenovo ThinkVision P27h-20", 27, "2560 x 1440", 60, "IPS", 4, "No HDR", 38000),
        ("lg", "LG UltraGear 27GS60Q", 27, "1920 x 1080", 180, "Fast IPS", 1, "HDR10", 24000),
        ("lg", "LG UltraGear 32GS75Q", 32, "2560 x 1440", 180, "Fast IPS", 1, "HDR10", 40000),
        ("lg", "LG 27MR400", 27, "1920 x 1080", 100, "IPS", 5, "No HDR", 17500),
        ("samsung", "Samsung Odyssey G55C 27", 27, "2560 x 1440", 165, "VA Curved", 1, "HDR10", 32000),
        ("samsung", "Samsung Odyssey G30A 24", 24, "1920 x 1080", 144, "Fast IPS", 1, "No HDR", 20000),
        ("asus", "ASUS ROG Strix XG27UQ", 27, "3840 x 2160", 144, "Fast IPS", 1, "HDR400", 95000),
        ("dell", "Dell S3222DGM", 32, "2560 x 1440", 165, "VA Curved", 1, "No HDR", 34000),
        ("msi", "MSI G274F", 27, "1920 x 1080", 180, "Fast IPS", 1, "No HDR", 22500),
        ("gigabyte", "Gigabyte G27F 2", 27, "1920 x 1080", 165, "Fast IPS", 1, "No HDR", 23000),
        ("benq", "BenQ Mobiuz EX240N", 24, "1920 x 1080", 165, "VA", 1, "No HDR", 16500),
        ("hp", "HP X24ih", 24, "1920 x 1080", 144, "IPS", 1, "No HDR", 18000),
        ("lenovo", "Lenovo G34w-30", 34, "3440 x 1440", 150, "VA Curved", 4, "No HDR", 45000),
    ]
    out = []
    for brand, name, size, res, hz, panel, ms, hdr, price in M:
        out.append({
            "name": name,
            "brand": brand,
            "price": price,
            "compare_at": None,
            "specs": {
                "display_size": str(size), "display_resolution": res, "refresh_rate": str(hz),
                "panel_type": panel, "response_time": str(ms), "hdr": hdr,
            },
        })
    return out


def gen_processors():
    """(brand, name, cores, threads, base, boost, tdp, socket, igpu, bench, price)"""
    C = [
        ("intel", "Intel Core i3-12100F", 4, 8, 3.3, 4.3, 58, "LGA 1700", None, 5900, 9500),
        ("intel", "Intel Core i3-12100", 4, 8, 3.3, 4.3, 60, "LGA 1700", "Intel UHD 730", 6100, 11500),
        ("intel", "Intel Core i3-13100F", 4, 8, 3.4, 4.5, 58, "LGA 1700", None, 6600, 11000),
        ("intel", "Intel Core i3-14100F", 4, 8, 3.5, 4.7, 58, "LGA 1700", None, 7100, 12000),
        ("intel", "Intel Core i3-14100", 4, 8, 3.5, 4.7, 60, "LGA 1700", "Intel UHD 730", 7300, 14000),
        ("intel", "Intel Core i5-12400F", 6, 12, 2.5, 4.4, 65, "LGA 1700", None, 9700, 16500),
        ("intel", "Intel Core i5-12400", 6, 12, 2.5, 4.4, 65, "LGA 1700", "Intel UHD 730", 9800, 18500),
        ("intel", "Intel Core i5-13400F", 10, 16, 2.5, 4.6, 65, "LGA 1700", None, 11800, 20000),
        ("intel", "Intel Core i5-14400F", 10, 16, 2.5, 4.7, 65, "LGA 1700", None, 12300, 21000),
        ("intel", "Intel Core i5-13500", 14, 20, 2.6, 4.8, 65, "LGA 1700", "Intel UHD 770", 13600, 25500),
        ("intel", "Intel Core i5-12600K", 10, 16, 3.7, 4.9, 125, "LGA 1700", "Intel UHD 770", 13100, 26000),
        ("intel", "Intel Core i5-13600K", 14, 20, 3.5, 5.1, 125, "LGA 1700", "Intel UHD 770", 16800, 32500),
        ("intel", "Intel Core i5-14600K", 14, 20, 3.5, 5.3, 125, "LGA 1700", "Intel UHD 770", 17500, 34000),
        ("intel", "Intel Core i5-14600KF", 14, 20, 3.5, 5.3, 125, "LGA 1700", None, 17600, 32500),
        ("intel", "Intel Core i7-12700K", 12, 20, 3.6, 5.0, 125, "LGA 1700", "Intel UHD 770", 17800, 33000),
        ("intel", "Intel Core i7-13700F", 16, 24, 2.1, 5.2, 65, "LGA 1700", None, 20800, 36000),
        ("intel", "Intel Core i7-13700K", 16, 24, 3.4, 5.4, 125, "LGA 1700", "Intel UHD 770", 21300, 44000),
        ("intel", "Intel Core i7-14700K", 20, 28, 3.4, 5.6, 125, "LGA 1700", "Intel UHD 770", 23500, 48000),
        ("intel", "Intel Core i7-14700KF", 20, 28, 3.4, 5.6, 125, "LGA 1700", None, 23600, 46500),
        ("intel", "Intel Core i9-12900K", 16, 24, 3.2, 5.2, 125, "LGA 1700", "Intel UHD 770", 21000, 38000),
        ("intel", "Intel Core i9-12900KS", 16, 24, 3.4, 5.5, 150, "LGA 1700", "Intel UHD 770", 22000, 42000),
        ("intel", "Intel Core i9-13900K", 24, 32, 3.0, 5.4, 125, "LGA 1700", "Intel UHD 770", 26000, 56000),
        ("intel", "Intel Core i9-13900KS", 24, 32, 3.2, 6.0, 150, "LGA 1700", "Intel UHD 770", 27000, 62000),
        ("intel", "Intel Core i9-14900KF", 24, 32, 3.2, 6.0, 125, "LGA 1700", None, 27600, 59500),
        ("amd", "AMD Ryzen 5 5500", 6, 12, 3.6, 4.2, 65, "AM4", None, 7500, 9500),
        ("amd", "AMD Ryzen 5 5600", 6, 12, 3.5, 4.4, 65, "AM4", None, 8500, 13000),
        ("amd", "AMD Ryzen 5 5600X", 6, 12, 3.7, 4.6, 65, "AM4", None, 9500, 15000),
        ("amd", "AMD Ryzen 5 5600G", 6, 12, 3.9, 4.4, 65, "AM4", "AMD Radeon Vega 7", 9200, 14500),
        ("amd", "AMD Ryzen 7 5700X", 8, 16, 3.4, 4.6, 65, "AM4", None, 12500, 19000),
        ("amd", "AMD Ryzen 7 5700X3D", 8, 16, 3.0, 4.1, 105, "AM4", None, 15500, 27000),
        ("amd", "AMD Ryzen 7 5800X", 8, 16, 3.8, 4.7, 105, "AM4", None, 13500, 22000),
        ("amd", "AMD Ryzen 7 5800X3D", 8, 16, 3.4, 4.5, 105, "AM4", None, 16500, 30000),
        ("amd", "AMD Ryzen 9 5900X", 12, 24, 3.7, 4.8, 105, "AM4", None, 17500, 28000),
        ("amd", "AMD Ryzen 9 5950X", 16, 32, 3.4, 4.9, 105, "AM4", None, 21000, 36000),
        ("amd", "AMD Ryzen 5 7500F", 6, 12, 3.7, 5.0, 65, "AM5", "AMD Radeon Graphics", 10500, 18500),
        ("amd", "AMD Ryzen 5 7600", 6, 12, 3.8, 5.1, 65, "AM5", "AMD Radeon Graphics", 11000, 21500),
        ("amd", "AMD Ryzen 5 7600X", 6, 12, 4.7, 5.3, 105, "AM5", "AMD Radeon Graphics", 11200, 22500),
        ("amd", "AMD Ryzen 7 7700", 8, 16, 3.8, 5.3, 65, "AM5", "AMD Radeon Graphics", 13500, 28000),
        ("amd", "AMD Ryzen 7 7700X", 8, 16, 4.5, 5.4, 105, "AM5", "AMD Radeon Graphics", 13800, 29000),
        ("amd", "AMD Ryzen 7 7800X3D", 8, 16, 4.2, 5.0, 120, "AM5", "AMD Radeon Graphics", 19500, 48000),
        ("amd", "AMD Ryzen 9 7900", 12, 24, 3.7, 5.4, 65, "AM5", "AMD Radeon Graphics", 17500, 34000),
        ("amd", "AMD Ryzen 9 7900X", 12, 24, 4.7, 5.6, 170, "AM5", "AMD Radeon Graphics", 19000, 36000),
        ("amd", "AMD Ryzen 9 7950X3D", 16, 32, 4.2, 5.7, 120, "AM5", "AMD Radeon Graphics", 25500, 58000),
        ("amd", "AMD Ryzen 5 8400F", 6, 12, 4.2, 4.7, 65, "AM5", None, 10000, 15500),
        ("amd", "AMD Ryzen 5 8500G", 6, 12, 4.1, 5.0, 65, "AM5", "AMD Radeon 740M", 10500, 17500),
        ("amd", "AMD Ryzen 5 8600G", 6, 12, 4.3, 5.0, 65, "AM5", "AMD Radeon 760M", 11500, 22000),
        ("amd", "AMD Ryzen 7 8700G", 8, 16, 4.2, 5.1, 65, "AM5", "AMD Radeon 780M", 13500, 30000),
        ("amd", "AMD Ryzen 5 9600X", 6, 12, 3.9, 5.4, 65, "AM5", "AMD Radeon Graphics", 13000, 25000),
        ("amd", "AMD Ryzen 7 9700X", 8, 16, 3.8, 5.5, 65, "AM5", "AMD Radeon Graphics", 15500, 32000),
        ("amd", "AMD Ryzen 7 9800X3D", 8, 16, 4.7, 5.2, 120, "AM5", "AMD Radeon Graphics", 21500, 56000),
        ("amd", "AMD Ryzen 9 9900X", 12, 24, 4.4, 5.5, 120, "AM5", "AMD Radeon Graphics", 18500, 40000),
        ("amd", "AMD Ryzen 9 9950X", 16, 32, 4.3, 5.7, 170, "AM5", "AMD Radeon Graphics", 23000, 62000),
    ]
    out = []
    for brand, name, cores, thr, base, boost, tdp, sock, igpu, bench, price in C:
        specs = {
            "cores": str(cores), "threads": str(thr),
            "base_clock_ghz": str(base), "boost_clock_ghz": str(boost),
            "tdp": str(tdp), "tdp_w": str(tdp), "socket": sock,
            "integrated_gpu": igpu or "None", "benchmark_score": str(bench),
            "warranty": "3 Years",
        }
        out.append({"name": name, "brand": brand, "price": price, "compare_at": None, "specs": specs})
    return out


def gen_graphics_cards():
    """Chip lines crossed with AIB partner coolers."""
    CHIPS = [
        # (chip, vram_gb, vram_type, core_mhz, boost_mhz, tdp_w, bench, base_price)
        ("GeForce RTX 4060", 8, "GDDR6", 1830, 2460, 115, 10800, 34000),
        ("GeForce RTX 4060 Ti", 8, "GDDR6", 2310, 2535, 160, 13500, 46000),
        ("GeForce RTX 4060 Ti 16GB", 16, "GDDR6", 2310, 2535, 165, 13800, 56000),
        ("GeForce RTX 4070", 12, "GDDR6X", 1920, 2475, 200, 17800, 66000),
        ("GeForce RTX 4070 Super", 12, "GDDR6X", 1980, 2475, 220, 20500, 75000),
        ("GeForce RTX 4070 Ti Super", 16, "GDDR6X", 2340, 2610, 285, 26000, 95000),
        ("GeForce RTX 4080 Super", 16, "GDDR6X", 2295, 2550, 320, 28000, 140000),
        ("GeForce RTX 4090", 24, "GDDR6X", 2235, 2520, 450, 35000, 215000),
        ("Radeon RX 7600", 8, "GDDR6", 1725, 2625, 165, 10800, 30000),
        ("Radeon RX 7600 XT", 16, "GDDR6", 1980, 2755, 190, 11800, 38000),
        ("Radeon RX 7700 XT", 12, "GDDR6", 1435, 2544, 245, 17000, 50000),
        ("Radeon RX 7800 XT", 16, "GDDR6", 1295, 2430, 263, 20000, 60000),
        ("Radeon RX 7900 XT", 20, "GDDR6", 1500, 2400, 315, 25500, 88000),
        ("Radeon RX 7900 XTX", 24, "GDDR6", 1855, 2500, 355, 29000, 115000),
    ]
    AIBS = [
        ("asus", [("TUF Gaming", 1.04, 320), ("Dual", 1.0, 230), ("ROG Strix", 1.12, 340), ("Prime", 0.98, 270)]),
        ("msi", [("Gaming X Trio", 1.08, 320), ("Ventus 2X", 0.99, 230), ("Ventus 3X", 1.02, 300), ("Suprim", 1.14, 340)]),
        ("gigabyte", [("Windforce", 1.0, 290), ("Gaming OC", 1.05, 320), ("Aorus Elite", 1.10, 330)]),
        ("zotac", [("Twin Edge", 0.98, 230), ("Trinity", 1.0, 300), ("AMP", 1.07, 320)]),
        ("asrock", [("Challenger", 0.98, 270), ("Phantom Gaming", 1.05, 300), ("Taichi", 1.13, 340)]),
    ]
    out = []
    for ci, (chip, vram, vtype, core, boost, tdp, bench, base_price) in enumerate(CHIPS):
        for bi, (aib_slug, series_list) in enumerate(AIBS):
            # Deterministic series spread — most chips get 1-2 series per AIB
            n_series = 2 if (ci + bi) % 3 == 0 else 1
            for k in range(n_series):
                series, price_mult, length = series_list[(ci + bi + k) % len(series_list)]
                name = f"{chip} {series} {vram}GB" if "Titan" not in chip else f"{chip} {series}"
                display = {
                    "asus": "ASUS", "msi": "MSI", "gigabyte": "Gigabyte",
                    "zotac": "Zotac", "asrock": "ASRock",
                }[aib_slug]
                full_name = f"{display} {series} {chip}"
                boost_adj = boost + (30 * k) + ((ci % 4) * 15)
                out.append({
                    "name": full_name,
                    "brand": aib_slug,
                    "price": bdt(base_price * price_mult),
                    "compare_at": None,
                    "specs": {
                        "memory_gb": str(vram), "memory_type": vtype,
                        "core_clock": str(core), "boost_clock": str(boost_adj),
                        "length_mm": str(length + (ci % 3) * 10),
                        "warranty": "3 Years" if aib_slug in ("asus", "msi", "gigabyte") else "2 Years",
                        "socket": "PCIe 4.0 x16", "tdp": str(tdp),
                        "benchmark_score": str(bench + k * 60),
                    },
                })
        # Reference / Founders editions for flagship chips
        if chip in ("GeForce RTX 4070 Super", "GeForce RTX 4080 Super", "GeForce RTX 4090"):
            out.append({
                "name": f"NVIDIA {chip} Founders Edition",
                "brand": "nvidia",
                "price": bdt(base_price * 1.06),
                "compare_at": None,
                "specs": {
                    "memory_gb": str(vram), "memory_type": vtype,
                    "core_clock": str(core), "boost_clock": str(boost),
                    "length_mm": "304", "warranty": "3 Years",
                    "socket": "PCIe 4.0 x16", "tdp": str(tdp),
                    "benchmark_score": str(bench),
                },
            })
        if chip == "Radeon RX 7900 XTX":
            out.append({
                "name": "AMD Radeon RX 7900 XTX Reference",
                "brand": "amd",
                "price": bdt(base_price * 1.02),
                "compare_at": None,
                "specs": {
                    "memory_gb": str(vram), "memory_type": vtype,
                    "core_clock": str(core), "boost_clock": str(boost),
                    "length_mm": "287", "warranty": "3 Years",
                    "socket": "PCIe 4.0 x16", "tdp": str(tdp),
                    "benchmark_score": str(bench),
                },
            })
    return out


def gen_ram():
    """(brand, series, ddr, [capacities], [speeds], per-8GB-module base price, rgb)"""
    FAMS = [
        ("corsair", "Vengeance LPX", 4, [8, 16, 32], [2666, 3000, 3200, 3600], 1550, False),
        ("corsair", "Vengeance RGB RS", 4, [16, 32], [3200, 3600], 1750, True),
        ("corsair", "Vengeance", 5, [16, 32, 48], [5200, 5600, 6000, 6400], 2100, False),
        ("corsair", "Dominator Titanium", 5, [32, 64], [6000, 6400, 6600], 3400, True),
        ("gskill", "Ripjaws V", 4, [8, 16, 32], [3200, 3600], 1500, False),
        ("gskill", "Trident Z Neo", 4, [16, 32], [3200, 3600], 1800, True),
        ("gskill", "Trident Z5 RGB", 5, [16, 32], [6000, 6400, 7200], 2400, True),
        ("gskill", "Flare X5", 5, [16, 32], [5200, 6000], 2000, False),
        ("kingston", "Fury Beast", 4, [8, 16, 32], [2666, 3200, 3600], 1450, False),
        ("kingston", "Fury Beast", 5, [16, 32], [5200, 5600, 6000], 2050, False),
        ("kingston", "Fury Renegade", 5, [16, 32], [6000, 6400], 2600, True),
        ("teamgroup", "T-Force Vulcan", 4, [8, 16, 32], [3000, 3200, 3600], 1350, False),
        ("teamgroup", "T-Force Delta RGB", 5, [16, 32], [5600, 6000], 2150, True),
        ("teamgroup", "T-Create Expert", 5, [32], [6000], 2300, False),
        ("adata", "XPG Lancer", 5, [16, 32], [5600, 6000], 2050, True),
        ("corsair", "Vengeance LPX", 4, [64], [3200], 1550, False),
        ("kingston", "Fury Renegade", 4, [16, 32], [3200, 3600], 1650, True),
        ("gskill", "Ripjaws S5", 5, [16, 32], [5200, 5600], 1950, False),
        ("gskill", "Trident Z5 Neo RGB", 5, [16, 32], [6000], 2350, True),
        ("teamgroup", "T-Force Vulcan", 5, [16, 32], [5200, 6000], 2000, False),
        ("adata", "XPG Lancer Blade RGB", 5, [16, 32], [6000, 6400], 2200, True),
        ("kingston", "Fury Impact", 4, [8, 16], [3200], 1400, False),
    ]
    out = []
    for brand, series, ddr, caps, speeds, base8, rgb in FAMS:
        for cap in caps:
            for spd in speeds:
                modules = 2 if cap >= 16 else 1
                per_mod = cap // modules
                price = round(base8 * (cap / 8) * (0.88 + spd / 9000) / 50) * 50
                name = f"{series} {cap}GB ({modules}x{per_mod}GB) DDR{ddr}-{spd}"
                out.append({
                    "name": name,
                    "brand": brand,
                    "price": price,
                    "compare_at": None,
                    "specs": {
                        "type": f"DDR{ddr}", "capacity_gb": str(cap), "speed_mhz": str(spd),
                        "modules": str(modules), "rgb": "Yes" if rgb else "No", "warranty": "Lifetime",
                    },
                })
    return out


def gen_storage():
    out = []
    # NVMe SSDs — (brand, series, interface, read, write_1tb, caps, base(1TB price))
    NVME = [
        ("samsung", "Samsung 970 EVO Plus", "PCIe 3.0 x4 NVMe", 3500, 3300, [250, 500, 1000, 2000], 9500),
        ("samsung", "Samsung 980", "PCIe 3.0 x4 NVMe", 3500, 3000, [250, 500, 1000], 7800),
        ("samsung", "Samsung 980 Pro", "PCIe 4.0 x4 NVMe", 7000, 5100, [500, 1000, 2000], 12800),
        ("samsung", "Samsung 990 Pro", "PCIe 4.0 x4 NVMe", 7450, 6900, [500, 1000, 2000, 4000], 14500),
        ("western-digital", "WD Blue SN570", "PCIe 3.0 x4 NVMe", 3500, 2300, [250, 500, 1000], 7800),
        ("western-digital", "WD Blue SN580", "PCIe 4.0 x4 NVMe", 4100, 3200, [500, 1000, 2000], 8500),
        ("western-digital", "WD Black SN770", "PCIe 4.0 x4 NVMe", 5150, 4900, [500, 1000, 2000], 10500),
        ("western-digital", "WD Black SN850X", "PCIe 4.0 x4 NVMe", 7300, 6600, [500, 1000, 2000, 4000], 14000),
        ("crucial", "Crucial P3", "PCIe 3.0 x4 NVMe", 3500, 3000, [500, 1000, 2000], 7300),
        ("crucial", "Crucial P3 Plus", "PCIe 4.0 x4 NVMe", 4800, 3600, [500, 1000, 2000], 8000),
        ("crucial", "Crucial P5 Plus", "PCIe 4.0 x4 NVMe", 6600, 5000, [500, 1000, 2000], 11500),
        ("crucial", "Crucial T500", "PCIe 4.0 x4 NVMe", 7000, 6400, [500, 1000, 2000], 12500),
        ("kingston", "Kingston NV2", "PCIe 4.0 x4 NVMe", 3500, 2800, [500, 1000, 2000], 7200),
        ("kingston", "Kingston KC3000", "PCIe 4.0 x4 NVMe", 7000, 7000, [512, 1024, 2048], 13000),
        ("adata", "ADATA Legend 800", "PCIe 3.0 x4 NVMe", 3500, 2600, [500, 1000], 7200),
        ("adata", "ADATA XPG Gammix S70 Blade", "PCIe 4.0 x4 NVMe", 7400, 5500, [512, 1024, 2048], 11800),
    ]
    capf = {250: 0.56, 500: 1.0, 512: 1.02, 1000: 1.8, 1024: 1.85, 2000: 3.4, 2048: 3.5, 4000: 6.6}
    for brand, series, iface, read, wr, caps, base1tb in NVME:
        for cap in caps:
            price = round(base1tb * capf[cap] / 100) * 100
            out.append({
                "name": f"{series} {cap}GB",
                "brand": brand,
                "price": price,
                "compare_at": None,
                "specs": {
                    "capacity_gb": str(cap), "interface": iface,
                    "read_mb_s": str(read), "write_mb_s": str(int(wr * (0.85 if cap < 1000 else 1.0))),
                    "form_factor": "M.2 2280", "warranty": "5 Years",
                },
            })
    # SATA SSDs
    for brand, series, caps, base in [
        ("samsung", "Samsung 870 EVO", [250, 500, 1000, 2000], 9800),
        ("crucial", "Crucial MX500", [250, 500, 1000, 2000], 7000),
        ("western-digital", "WD Blue SA510", [250, 500, 1000], 6400),
    ]:
        for cap in caps:
            price = round(base * capf[cap] / 100) * 100
            out.append({
                "name": f"{series} {cap}GB",
                "brand": brand,
                "price": price,
                "compare_at": None,
                "specs": {
                    "capacity_gb": str(cap), "interface": "SATA 6Gb/s",
                    "read_mb_s": "560", "write_mb_s": "530",
                    "form_factor": "2.5-inch", "warranty": "5 Years",
                },
            })
    # HDDs — (brand, series, caps, base(1TB), purpose read)
    for brand, series, caps, base in [
        ("seagate", "Seagate Barracuda", [1000, 2000, 4000], 4400),
        ("seagate", "Seagate IronWolf", [2000, 4000], 6500),
        ("western-digital", "WD Blue", [1000, 2000], 4600),
        ("western-digital", "WD Black", [1000, 2000], 5900),
        ("western-digital", "WD Red Plus", [2000, 4000], 6800),
        ("western-digital", "WD Purple", [1000, 2000, 4000], 5000),
    ]:
        hf = {1000: 1.0, 2000: 1.4, 4000: 2.35}
        for cap in caps:
            price = round(base * hf[cap] / 50) * 50
            out.append({
                "name": f"{series} {cap}GB HDD" if cap < 1000 else f"{series} {cap // 1000}TB HDD",
                "brand": brand,
                "price": price,
                "compare_at": None,
                "specs": {
                    "capacity_gb": str(cap), "interface": "SATA 6Gb/s",
                    "read_mb_s": "180", "write_mb_s": "160",
                    "form_factor": "3.5-inch", "warranty": "2 Years",
                },
            })
    # Portable SSDs
    for brand, name, read, cap, price in [
        ("samsung", "Samsung T7 Portable SSD 1TB", 1050, 1000, 12500),
        ("samsung", "Samsung T7 Shield 2TB", 1050, 2000, 19500),
        ("samsung", "Samsung T9 Portable SSD 2TB", 2000, 2000, 24000),
        ("western-digital", "WD My Passport SSD 1TB", 1050, 1000, 11000),
        ("western-digital", "WD Elements SE 1TB HDD", 130, 1000, 6500),
    ]:
        out.append({
            "name": name,
            "brand": brand,
            "price": price,
            "compare_at": None,
            "specs": {
                "capacity_gb": str(cap), "interface": "USB 3.2 Gen 2",
                "read_mb_s": str(read), "write_mb_s": str(int(read * 0.9)),
                "form_factor": "Portable", "warranty": "3 Years",
            },
        })
    return out


def gen_motherboards():
    """(brand, name, socket, chipset, form, mem, m2_slots, price)"""
    MB = [
        ("asus", "ASUS Prime H610M-K D4", "LGA 1700", "H610", "Micro-ATX", "DDR4", 1, 9200),
        ("asus", "ASUS Prime H610M-A D4", "LGA 1700", "H610", "Micro-ATX", "DDR4", 1, 10500),
        ("asus", "ASUS TUF Gaming B660M-Plus D4", "LGA 1700", "B660", "Micro-ATX", "DDR4", 2, 16500),
        ("asus", "ASUS Prime B760M-A DDR5", "LGA 1700", "B760", "Micro-ATX", "DDR5", 3, 18000),
        ("asus", "ASUS TUF Gaming B760-Plus D4", "LGA 1700", "B760", "ATX", "DDR4", 3, 19000),
        ("asus", "ASUS TUF Gaming Z790-Plus", "LGA 1700", "Z790", "ATX", "DDR5", 4, 32000),
        ("asus", "ASUS Prime Z790-P", "LGA 1700", "Z790", "ATX", "DDR5", 4, 28500),
        ("asus", "ASUS ROG Strix B760-F", "LGA 1700", "B760", "ATX", "DDR5", 3, 27000),
        ("asus", "ASUS ROG Strix Z790-A", "LGA 1700", "Z790", "ATX", "DDR5", 4, 38000),
        ("asus", "ASUS Prime B650M-A", "AM5", "B650", "Micro-ATX", "DDR5", 3, 17500),
        ("asus", "ASUS TUF Gaming B650M-Plus", "AM5", "B650", "Micro-ATX", "DDR5", 3, 19500),
        ("asus", "ASUS ROG Strix B650E-F", "AM5", "B650E", "ATX", "DDR5", 3, 26500),
        ("asus", "ASUS TUF Gaming X670E-Plus", "AM5", "X670E", "ATX", "DDR5", 4, 32000),
        ("asus", "ASUS ROG Strix X670E-E", "AM5", "X670E", "ATX", "DDR5", 4, 42000),
        ("asus", "ASUS TUF Gaming B550M-Plus", "AM4", "B550", "Micro-ATX", "DDR4", 2, 13000),
        ("asus", "ASUS Prime B550-Plus", "AM4", "B550", "ATX", "DDR4", 2, 14500),
        ("msi", "MSI PRO H610M-E DDR4", "LGA 1700", "H610", "Micro-ATX", "DDR4", 1, 8800),
        ("msi", "MSI PRO B760M-E DDR4", "LGA 1700", "B760", "Micro-ATX", "DDR4", 1, 12500),
        ("msi", "MSI PRO B650M-P", "AM5", "B650", "Micro-ATX", "DDR5", 2, 15500),
        ("msi", "MSI MAG B650M Mortar", "AM5", "B650", "Micro-ATX", "DDR5", 3, 20500),
        ("msi", "MSI MAG B650 Tomahawk", "AM5", "B650", "ATX", "DDR5", 3, 24500),
        ("msi", "MSI MAG B760M Mortar DDR4", "LGA 1700", "B760", "Micro-ATX", "DDR4", 2, 17500),
        ("msi", "MSI MAG B760 Tomahawk", "LGA 1700", "B760", "ATX", "DDR5", 3, 24000),
        ("msi", "MSI MPG Z790 Edge", "LGA 1700", "Z790", "ATX", "DDR5", 4, 36000),
        ("msi", "MSI PRO Z790-P", "LGA 1700", "Z790", "ATX", "DDR5", 4, 29500),
        ("msi", "MSI MPG X670E Carbon", "AM5", "X670E", "ATX", "DDR5", 4, 45000),
        ("msi", "MSI B550M Pro-VDH", "AM4", "B550", "Micro-ATX", "DDR4", 2, 10500),
        ("msi", "MSI MAG B550 Tomahawk", "AM4", "B550", "ATX", "DDR4", 2, 16500),
        ("gigabyte", "Gigabyte H610M H DDR4", "LGA 1700", "H610", "Micro-ATX", "DDR4", 1, 8500),
        ("gigabyte", "Gigabyte B760M DS3H", "LGA 1700", "B760", "Micro-ATX", "DDR4", 2, 14000),
        ("gigabyte", "Gigabyte B760M DS3H DDR5", "LGA 1700", "B760", "Micro-ATX", "DDR5", 2, 15500),
        ("gigabyte", "Gigabyte B760M Aorus Elite", "LGA 1700", "B760", "Micro-ATX", "DDR5", 3, 22500),
        ("gigabyte", "Gigabyte B650M DS3H", "AM5", "B650", "Micro-ATX", "DDR5", 2, 16000),
        ("gigabyte", "Gigabyte B650 Aorus Elite AX", "AM5", "B650", "ATX", "DDR5", 3, 25000),
        ("gigabyte", "Gigabyte X670 Aorus Elite AX", "AM5", "X670", "ATX", "DDR5", 4, 34000),
        ("gigabyte", "Gigabyte Z790 Aorus Elite AX", "LGA 1700", "Z790", "ATX", "DDR5", 4, 34500),
        ("gigabyte", "Gigabyte Z790 D DDR4", "LGA 1700", "Z790", "ATX", "DDR4", 3, 25000),
        ("gigabyte", "Gigabyte B550M DS3H", "AM4", "B550", "Micro-ATX", "DDR4", 1, 9800),
        ("gigabyte", "Gigabyte B550 Aorus Elite", "AM4", "B550", "ATX", "DDR4", 2, 16000),
        ("asrock", "ASRock H610M-HDV/M.2", "LGA 1700", "H610", "Micro-ATX", "DDR4", 1, 8200),
        ("asrock", "ASRock B760M-HDV/M.2", "LGA 1700", "B760", "Micro-ATX", "DDR4", 1, 11800),
        ("asrock", "ASRock B760M Steel Legend", "LGA 1700", "B760", "Micro-ATX", "DDR5", 3, 21000),
        ("asrock", "ASRock B650M Pro RS", "AM5", "B650", "Micro-ATX", "DDR5", 2, 16000),
        ("asrock", "ASRock B650E Steel Legend", "AM5", "B650E", "ATX", "DDR5", 3, 25000),
        ("asrock", "ASRock X670E Steel Legend", "AM5", "X670E", "ATX", "DDR5", 4, 33000),
        ("asrock", "ASRock Z790 Taichi", "LGA 1700", "Z790", "ATX", "DDR5", 5, 52000),
        ("asrock", "ASRock B550M Steel Legend", "AM4", "B550", "Micro-ATX", "DDR4", 2, 12500),
        ("asus", "ASUS Prime A620M-K", "AM5", "A620", "Micro-ATX", "DDR5", 2, 13500),
        ("asus", "ASUS TUF Gaming B650-Plus", "AM5", "B650", "ATX", "DDR5", 3, 22500),
        ("asus", "ASUS ProArt B760-Creator", "LGA 1700", "B760", "ATX", "DDR5", 3, 30000),
        ("msi", "MSI PRO A620M-E", "AM5", "A620", "Micro-ATX", "DDR5", 1, 12500),
        ("msi", "MSI MAG B650M Mortar WiFi", "AM5", "B650", "Micro-ATX", "DDR5", 3, 22500),
        ("msi", "MSI PRO B650M-A WiFi", "AM5", "B650", "Micro-ATX", "DDR5", 3, 19500),
        ("gigabyte", "Gigabyte B760M Gaming X", "LGA 1700", "B760", "Micro-ATX", "DDR5", 3, 19500),
        ("gigabyte", "Gigabyte B650E Aorus Elite X AX", "AM5", "B650E", "ATX", "DDR5", 4, 28000),
        ("gigabyte", "Gigabyte H610M S2H", "LGA 1700", "H610", "Micro-ATX", "DDR4", 1, 8000),
        ("asrock", "ASRock B760 Pro RS", "LGA 1700", "B760", "ATX", "DDR5", 3, 20500),
        ("asrock", "ASRock A620M-HDV/M.2", "AM5", "A620", "Micro-ATX", "DDR5", 1, 11500),
        ("asrock", "ASRock Z790 Pro RS", "LGA 1700", "Z790", "ATX", "DDR5", 4, 27500),
    ]
    out = []
    for brand, name, sock, chipset, form, mem, m2, price in MB:
        out.append({
            "name": name,
            "brand": brand,
            "price": price,
            "compare_at": None,
            "specs": {
                "socket": sock, "chipset": chipset, "form_factor": form,
                "memory_type": mem, "m2_slots": str(m2),
                "warranty": "3 Years" if brand != "asrock" else "2 Years",
            },
        })
    return out


def gen_power_supplies():
    """(brand, series, [wattages], efficiency, modular, base-per-watt BDT)"""
    LINES = [
        ("corsair", "Corsair CV", [450, 550, 650], "80+ Bronze", "Non-Modular", 9.0),
        ("corsair", "Corsair CX", [550, 650, 750], "80+ Bronze", "Non-Modular", 9.6),
        ("corsair", "Corsair RM-e", [650, 750, 850], "80+ Gold", "Fully Modular", 13.5),
        ("corsair", "Corsair RMx", [750, 850, 1000], "80+ Gold", "Fully Modular", 14.5),
        ("corsair", "Corsair HXi", [1000, 1200], "80+ Platinum", "Fully Modular", 18.0),
        ("cooler-master", "Cooler Master MWE Bronze V2", [450, 550, 650], "80+ Bronze", "Non-Modular", 8.8),
        ("cooler-master", "Cooler Master MWE White V2", [550, 650], "80+ Standard", "Non-Modular", 8.0),
        ("cooler-master", "Cooler Master MWE Gold V2", [650, 750, 850], "80+ Gold", "Fully Modular", 13.0),
        ("cooler-master", "Cooler Master V Gold V2", [750, 850], "80+ Gold", "Fully Modular", 15.0),
        ("seasonic", "Seasonic S12III", [550, 650], "80+ Bronze", "Non-Modular", 9.2),
        ("seasonic", "Seasonic Focus GX", [550, 650, 750, 850], "80+ Gold", "Fully Modular", 14.0),
        ("seasonic", "Seasonic Focus PX", [750, 850], "80+ Platinum", "Fully Modular", 17.0),
        ("seasonic", "Seasonic Prime TX", [850, 1000], "80+ Titanium", "Fully Modular", 20.0),
        ("thermaltake", "Thermaltake Smart", [500, 600, 700], "80+ Standard", "Non-Modular", 7.5),
        ("thermaltake", "Thermaltake Toughpower GX2", [600, 700, 800], "80+ Gold", "Semi-Modular", 12.0),
        ("thermaltake", "Thermaltake Toughpower PF1", [650, 750], "80+ Platinum", "Fully Modular", 17.5),
        ("nzxt", "NZXT C Series", [650, 750, 850, 1000], "80+ Gold", "Fully Modular", 13.8),
        ("seasonic", "Seasonic Core GX", [550, 650], "80+ Gold", "Fully Modular", 13.2),
        ("thermaltake", "Thermaltake Toughpower SX1", [550, 650], "80+ Gold", "Non-Modular", 11.5),
        ("corsair", "Corsair CX-R", [650, 750], "80+ Bronze", "Non-Modular", 9.4),
        ("cooler-master", "Cooler Master V SFX Gold", [650, 750], "80+ Gold", "Fully Modular", 16.0),
        ("deepcool", "DeepCool PN-M", [650, 750, 850], "80+ Gold", "Fully Modular", 12.8),
        ("lian-li", "Lian Li SP", [750, 850], "80+ Gold", "Fully Modular", 13.5),
    ]
    out = []
    for brand, series, watts, eff, modular, per_watt in LINES:
        for w in watts:
            price = round(w * per_watt / 50) * 50
            out.append({
                "name": f"{series} {w}W",
                "brand": brand,
                "price": price,
                "compare_at": None,
                "specs": {
                    "wattage": str(w), "efficiency": eff, "modular": modular,
                    "warranty": "10 Years" if brand == "seasonic" else "5 Years",
                },
            })
    return out


def gen_cases():
    """(brand, name, form support, side panel, fans, price)"""
    C = [
        ("nzxt", "NZXT H510 Flow", "ATX", "Tempered Glass", 2, 9500),
        ("nzxt", "NZXT H510i", "ATX", "Tempered Glass", 2, 12500),
        ("nzxt", "NZXT H6 Flow", "Mid-Tower", "Tempered Glass", 3, 14500),
        ("nzxt", "NZXT H7 Flow", "Mid-Tower", "Tempered Glass", 2, 13500),
        ("nzxt", "NZXT H9 Flow", "Mid-Tower", "Tempered Glass", 4, 19500),
        ("corsair", "Corsair 275R Airflow", "ATX", "Tempered Glass", 3, 8500),
        ("corsair", "Corsair 4000D", "ATX", "Tempered Glass", 2, 9000),
        ("corsair", "Corsair 4000D Airflow", "ATX", "Tempered Glass", 2, 10500),
        ("corsair", "Corsair 5000D Airflow", "ATX", "Tempered Glass", 2, 15000),
        ("corsair", "Corsair iCUE 220T RGB", "ATX", "Tempered Glass", 3, 9500),
        ("corsair", "Corsair 5000X RGB", "Mid-Tower", "Tempered Glass", 4, 18000),
        ("corsair", "Corsair 2000D Airflow", "Mini-ITX", "Tempered Glass", 2, 12000),
        ("cooler-master", "Cooler Master MasterBox Q300L", "Micro-ATX", "Acrylic", 1, 4500),
        ("cooler-master", "Cooler Master MasterBox MB311L", "Micro-ATX", "Tempered Glass", 1, 5800),
        ("cooler-master", "Cooler Master MasterBox MB520", "ATX", "Tempered Glass", 1, 6500),
        ("cooler-master", "Cooler Master MasterBox MB530P", "ATX", "Tempered Glass", 3, 10500),
        ("cooler-master", "Cooler Master TD500 Mesh", "ATX", "Tempered Glass", 3, 9800),
        ("cooler-master", "Cooler Master HAF 500", "ATX", "Tempered Glass", 3, 11500),
        ("cooler-master", "Cooler Master MasterBox NR200P", "Mini-ITX", "Tempered Glass", 0, 9500),
        ("thermaltake", "Thermaltake Versa H18", "Micro-ATX", "Acrylic", 1, 3800),
        ("thermaltake", "Thermaltake S100", "Micro-ATX", "Tempered Glass", 1, 4200),
        ("thermaltake", "Thermaltake V200", "ATX", "Tempered Glass", 3, 5500),
        ("thermaltake", "Thermaltake View 51", "Mid-Tower", "Tempered Glass", 4, 12000),
        ("thermaltake", "Thermaltake Divider 300", "Mid-Tower", "Tempered Glass", 4, 9800),
        ("lian-li", "Lian Li Lancool 216", "ATX", "Tempered Glass", 2, 12500),
        ("lian-li", "Lian Li Lancool 205 Mesh", "ATX", "Tempered Glass", 3, 11000),
        ("lian-li", "Lian Li O11 Dynamic EVO", "Mid-Tower", "Tempered Glass", 0, 18500),
        ("deepcool", "DeepCool CH510 Mesh", "ATX", "Tempered Glass", 4, 8800),
        ("deepcool", "DeepCool CC560", "ATX", "Tempered Glass", 4, 7200),
        ("deepcool", "DeepCool CH160", "Mini-ITX", "Tempered Glass", 1, 5500),
        ("deepcool", "DeepCool Matrexx 40", "Micro-ATX", "Tempered Glass", 1, 4800),
        ("asus", "ASUS TUF Gaming GT301", "ATX", "Tempered Glass", 3, 10500),
        ("msi", "MSI MAG Forge 100M", "ATX", "Tempered Glass", 4, 7500),
        ("gigabyte", "Gigabyte C200 Glass", "ATX", "Tempered Glass", 3, 6800),
        ("nzxt", "NZXT H5 Elite", "Mid-Tower", "Tempered Glass", 2, 16500),
        ("nzxt", "NZXT H7 Elite", "Mid-Tower", "Tempered Glass", 3, 17500),
        ("corsair", "Corsair Air 540", "ATX", "Tempered Glass", 2, 12500),
        ("corsair", "Corsair 6500X", "Mid-Tower", "Tempered Glass", 3, 19500),
        ("cooler-master", "Cooler Master MasterBox 600", "ATX", "Tempered Glass", 4, 8500),
        ("lian-li", "Lian Li Lancool 207", "ATX", "Tempered Glass", 3, 10500),
        ("lian-li", "Lian Li O11 Air Mini", "Mid-Tower", "Tempered Glass", 0, 14500),
        ("deepcool", "DeepCool CH560", "ATX", "Tempered Glass", 3, 10500),
        ("deepcool", "DeepCool CC360", "ATX", "Tempered Glass", 4, 5500),
        ("thermaltake", "Thermaltake Ceres 300", "Mid-Tower", "Tempered Glass", 3, 11500),
    ]
    out = []
    for brand, name, form, panel, fans, price in C:
        out.append({
            "name": name,
            "brand": brand,
            "price": price,
            "compare_at": None,
            "specs": {
                "form_factor": form, "side_panel": panel,
                "preinstalled_fans": str(fans), "warranty": "2 Years",
            },
        })
    return out


def gen_keyboards():
    """(brand, name, switch, layout, connectivity, rgb, price, has_switch_variants)"""
    K = [
        ("logitech", "Logitech K120", "Membrane", "Full-Size", "Wired", False, 1800, False),
        ("logitech", "Logitech G213 Prodigy", "Membrane", "Full-Size", "Wired", True, 5200, False),
        ("logitech", "Logitech G413 SE", "Mechanical Tactile", "Full-Size", "Wired", False, 7200, False),
        ("logitech", "Logitech G512 Carbon", "GX Blue", "TKL", "Wired", True, 11500, True),
        ("logitech", "Logitech G915 TKL", "Low-Profile GL Tactile", "TKL", "Wireless", True, 23500, False),
        ("logitech", "Logitech MX Mechanical", "Low-Profile Tactile", "Full-Size", "Wireless", True, 18500, False),
        ("razer", "Razer Cynosa V2", "Membrane", "Full-Size", "Wired", True, 4500, False),
        ("razer", "Razer Ornata V3", "Mecha-Membrane", "TKL", "Wired", True, 6800, False),
        ("razer", "Razer BlackWidow V3", "Razer Green", "Full-Size", "Wired", True, 12800, True),
        ("razer", "Razer BlackWidow V4", "Razer Green", "Full-Size", "Wired", True, 15500, True),
        ("razer", "Razer Huntsman Mini", "Razer Red Linear", "60%", "Wired", True, 9800, True),
        ("razer", "Razer Huntsman V2", "Razer Red Linear", "Full-Size", "Wired", True, 14500, False),
        ("steelseries", "SteelSeries Apex 3", "Membrane", "Full-Size", "Wired", True, 5500, False),
        ("steelseries", "SteelSeries Apex 5", "Hybrid Mechanical", "TKL", "Wired", True, 9500, False),
        ("steelseries", "SteelSeries Apex 7 TKL", "Red Linear", "TKL", "Wired", True, 14500, True),
        ("steelseries", "SteelSeries Apex 9 TKL", "OptiPoint Linear", "TKL", "Wired", True, 16500, False),
        ("steelseries", "SteelSeries Apex Pro TKL", "OmniPoint Adjustable", "TKL", "Wired", True, 25000, False),
        ("redragon", "Redragon K552 Kumara", "Red Linear", "TKL", "Wired", False, 2900, True),
        ("redragon", "Redragon K617 Fizz", "Red Linear", "60%", "Wired", True, 2400, False),
        ("redragon", "Redragon K630 Dragonborn", "Red Linear", "60%", "Wired", True, 2600, False),
        ("redragon", "Redragon K556", "Red Linear", "Full-Size", "Wired", True, 3600, False),
        ("corsair", "Corsair K55 Core", "Membrane", "Full-Size", "Wired", True, 4200, False),
        ("corsair", "Corsair K60 Pro", "Cherry Viola", "TKL", "Wired", False, 8500, False),
        ("corsair", "Corsair K70 Core", "Mechanical Red", "TKL", "Wired", True, 10500, False),
        ("corsair", "Corsair K70 RGB Pro", "Cherry MX Red", "Full-Size", "Wired", True, 16500, True),
        ("corsair", "Corsair K100 RGB", "Corsair OPX Optical", "Full-Size", "Wired", True, 24500, False),
        ("logitech", "Logitech G915 X", "Low-Profile GL Linear", "Full-Size", "Wireless", True, 21000, False),
        ("logitech", "Logitech K380", "Scissor", "Compact", "Wireless", False, 3200, False),
        ("logitech", "Logitech POP Keys", "Mechanical Tactile", "Compact", "Wireless", True, 6800, False),
        ("razer", "Razer BlackWidow V4 75%", "Razer Orange", "75%", "Wired", True, 17500, False),
        ("razer", "Razer DeathStalker V2", "Low-Profile Optical", "Full-Size", "Wired", True, 13500, False),
        ("steelseries", "SteelSeries Apex 3 TKL", "Membrane", "TKL", "Wired", True, 4800, False),
        ("steelseries", "SteelSeries Apex 9 Mini", "OptiPoint Linear", "60%", "Wired", True, 13500, False),
        ("redragon", "Redragon K512 Shiva", "Membrane", "Full-Size", "Wired", True, 2800, False),
        ("redragon", "Redragon K628 Pro", "Red Linear", "75%", "Wireless", True, 4200, False),
        ("redragon", "Redragon K644", "Red Linear", "60%", "Wired", True, 2600, True),
        ("corsair", "Corsair K55 RGB Pro", "Membrane", "Full-Size", "Wired", True, 5600, False),
        ("corsair", "Corsair K65 Plus", "Mechanical Red", "75%", "Wireless", True, 12500, False),
        ("hyperx", "HyperX Alloy Origins Core", "Aqua Tactile", "TKL", "Wired", True, 9800, True),
        ("hyperx", "HyperX Alloy Origins 60", "Aqua Linear", "60%", "Wired", True, 10500, False),
        ("asus", "ASUS ROG Strix Scope II", "NX Snow Linear", "Full-Size", "Wired", True, 12500, False),
        ("asus", "ASUS TUF Gaming K1", "Membrane", "Full-Size", "Wired", True, 3500, False),
        ("msi", "MSI Vigor GK30 Combo", "Membrane", "Full-Size", "Wired", True, 4200, False),
        ("msi", "MSI Vigor GK71 Sonic", "Sonic Red Linear", "TKL", "Wired", True, 8500, False),
        ("gigabyte", "Gigabyte AORUS K9", "Cherry MX Red", "Full-Size", "Wired", True, 11500, False),
        ("hp", "HP GK320", "Membrane", "Full-Size", "Wired", True, 2500, False),
    ]
    out = []
    switches = [("Red Linear", 0), ("Blue Clicky", 300), ("Brown Tactile", 300)]
    for brand, name, sw, layout, conn, rgb, price, variants in K:
        entries = [(sw, price)]
        if variants:
            base = name.rsplit(" ", 1)[0]
            entries = [(s, price + d) for s, d in switches]
        for i, (switch, p) in enumerate(entries):
            full = name if i == 0 or not variants else f"{name} ({switch.split()[0]})"
            out.append({
                "name": full,
                "brand": brand,
                "price": p,
                "compare_at": None,
                "specs": {
                    "switch_type": switch, "layout": layout, "connectivity": conn,
                    "rgb": "Yes" if rgb else "No", "warranty": "2 Years",
                },
            })
    return out


def gen_mice():
    """(brand, name, dpi, connectivity, weight, rgb, price)"""
    M = [
        ("logitech", "Logitech B100", 800, "Wired", 90, False, 700),
        ("logitech", "Logitech G102", 8000, "Wired", 85, True, 2100),
        ("logitech", "Logitech G304 Lightspeed", 12000, "Wireless", 99, False, 3900),
        ("logitech", "Logitech G502 Hero", 25600, "Wired", 121, True, 6200),
        ("logitech", "Logitech G502 X", 25600, "Wired", 106, True, 9800),
        ("logitech", "Logitech G502 X Plus", 25600, "Wireless", 106, True, 16500),
        ("logitech", "Logitech G Pro X Superlight 2", 32000, "Wireless", 60, False, 18500),
        ("logitech", "Logitech MX Master 3S", 8000, "Wireless", 141, False, 13500),
        ("razer", "Razer DeathAdder Essential", 6400, "Wired", 96, False, 1800),
        ("razer", "Razer DeathAdder V2", 20000, "Wired", 82, True, 4200),
        ("razer", "Razer DeathAdder V3", 30000, "Wired", 59, False, 9200),
        ("razer", "Razer Viper Mini", 8500, "Wired", 61, True, 3100),
        ("razer", "Razer Viper V2 Pro", 30000, "Wireless", 58, False, 16500),
        ("razer", "Razer Basilisk V3", 26000, "Wired", 101, True, 5800),
        ("razer", "Razer Basilisk V3 Pro", 26000, "Wireless", 106, True, 14500),
        ("steelseries", "SteelSeries Rival 3", 8500, "Wired", 77, True, 2200),
        ("steelseries", "SteelSeries Rival 3 Wireless", 18000, "Wireless", 85, True, 4500),
        ("steelseries", "SteelSeries Rival 5", 18000, "Wired", 85, True, 5200),
        ("steelseries", "SteelSeries Sensei Ten", 18000, "Wired", 92, True, 6200),
        ("steelseries", "SteelSeries Aerox 3", 8500, "Wired", 57, True, 4200),
        ("steelseries", "SteelSeries Aerox 5 Wireless", 18000, "Wireless", 66, True, 9800),
        ("steelseries", "SteelSeries Prime Wireless", 18000, "Wireless", 80, False, 10500),
        ("redragon", "Redragon M711 Cobra", 10000, "Wired", 88, True, 1700),
        ("redragon", "Redragon M612 Predator", 8000, "Wired", 110, True, 1900),
        ("redragon", "Redragon M908 Impact", 12400, "Wired", 140, True, 2800),
        ("redragon", "Redragon M801 Mammoth", 16000, "Wired", 120, True, 2200),
        ("corsair", "Corsair Harpoon RGB Pro", 12000, "Wired", 85, True, 2400),
        ("corsair", "Corsair Katar Pro XT", 18000, "Wired", 73, True, 3200),
        ("corsair", "Corsair Ironclaw RGB", 18000, "Wired", 105, True, 4500),
        ("corsair", "Corsair Scimitar Elite", 18000, "Wired", 122, True, 7200),
        ("corsair", "Corsair Dark Core RGB Pro", 18000, "Wireless", 108, True, 9800),
        ("logitech", "Logitech G203 Lightsync", 8000, "Wired", 85, True, 2400),
        ("logitech", "Logitech M330 Silent Plus", 1000, "Wireless", 105, False, 2500),
        ("logitech", "Logitech Signature M650", 4000, "Wireless", 91, False, 3200),
        ("razer", "Razer Cobra", 8500, "Wired", 71, True, 3800),
        ("razer", "Razer Cobra Pro", 30000, "Wireless", 74, True, 12800),
        ("razer", "Razer Orochi V2", 18000, "Wireless", 60, False, 8200),
        ("steelseries", "SteelSeries Rival 650 Wireless", 12000, "Wireless", 121, True, 9800),
        ("steelseries", "SteelSeries Sensei 310", 12000, "Wired", 92, True, 5500),
        ("redragon", "Redragon M602 Griffin", 7200, "Wired", 100, True, 1500),
        ("redragon", "Redragon M913 Impact Elite", 16000, "Wireless", 118, True, 4200),
        ("corsair", "Corsair M55 RGB Pro", 12400, "Wired", 86, True, 3600),
        ("corsair", "Corsair Sabre RGB Pro", 18000, "Wired", 69, False, 5200),
        ("corsair", "Corsair Darkstar Wireless", 26000, "Wireless", 118, True, 11500),
        ("hp", "HP M260", 3200, "Wired", 95, False, 900),
        ("samsung", "Samsung Slim Optical Mouse", 1000, "Wired", 75, False, 800),
    ]
    out = []
    for brand, name, dpi, conn, wt, rgb, price in M:
        out.append({
            "name": name,
            "brand": brand,
            "price": price,
            "compare_at": None,
            "specs": {
                "dpi_max": str(dpi), "connectivity": conn, "weight_g": str(wt),
                "rgb": "Yes" if rgb else "No", "warranty": "2 Years",
            },
        })
    return out


def gen_headsets():
    """(brand, name, type, connectivity, driver, surround, price)"""
    H = [
        ("logitech", "Logitech G331", "Over-Ear", "Wired", 50, False, 3200),
        ("logitech", "Logitech G332", "Over-Ear", "Wired", 50, False, 3800),
        ("logitech", "Logitech G431", "Over-Ear", "Wired", 50, True, 5800),
        ("logitech", "Logitech G435 Lightspeed", "Over-Ear", "Wireless", 40, False, 7800),
        ("logitech", "Logitech G733", "Over-Ear", "Wireless", 40, True, 13500),
        ("logitech", "Logitech G Pro X 2", "Over-Ear", "Wired", 50, True, 17500),
        ("razer", "Razer Kraken X", "Over-Ear", "Wired", 40, False, 3500),
        ("razer", "Razer Kraken V3 X", "Over-Ear", "Wired", 40, True, 5200),
        ("razer", "Razer BlackShark V2 X", "Over-Ear", "Wired", 50, True, 4800),
        ("razer", "Razer BlackShark V2", "Over-Ear", "Wired", 50, True, 9500),
        ("razer", "Razer BlackShark V2 Pro", "Over-Ear", "Wireless", 50, True, 18500),
        ("razer", "Razer Barracuda X", "Over-Ear", "Wireless", 40, False, 11800),
        ("steelseries", "SteelSeries Arctis Nova 1", "Over-Ear", "Wired", 40, True, 5500),
        ("steelseries", "SteelSeries Arctis Nova 3", "Over-Ear", "Wired", 40, True, 7200),
        ("steelseries", "SteelSeries Arctis Nova 5", "Over-Ear", "Wireless", 40, True, 13500),
        ("steelseries", "SteelSeries Arctis Nova 7", "Over-Ear", "Wireless", 40, True, 16500),
        ("steelseries", "SteelSeries Arctis 1 Wireless", "Over-Ear", "Wireless", 40, False, 7800),
        ("steelseries", "SteelSeries Arctis Nova Pro", "Over-Ear", "Wired", 40, True, 24500),
        ("corsair", "Corsair HS35", "Over-Ear", "Wired", 50, False, 2800),
        ("corsair", "Corsair HS45", "Over-Ear", "Wired", 50, True, 3900),
        ("corsair", "Corsair HS55 Wireless", "Over-Ear", "Wireless", 50, False, 8200),
        ("corsair", "Corsair HS65 Surround", "Over-Ear", "Wired", 50, True, 6500),
        ("corsair", "Corsair HS80 Max", "Over-Ear", "Wireless", 50, True, 15500),
        ("corsair", "Corsair Void RGB Elite", "Over-Ear", "Wireless", 50, True, 7500),
        ("hyperx", "HyperX Cloud Stinger 2", "Over-Ear", "Wired", 50, False, 4200),
        ("hyperx", "HyperX Cloud III", "Over-Ear", "Wired", 53, True, 9500),
        ("hyperx", "HyperX Cloud Alpha", "Over-Ear", "Wired", 50, False, 11800),
        ("hyperx", "HyperX Cloud II Wireless", "Over-Ear", "Wireless", 53, True, 14500),
        ("logitech", "Logitech G335 Wired", "Over-Ear", "Wired", 40, False, 5600),
        ("razer", "Razer Kraken Kitty V2", "Over-Ear", "Wired", 50, True, 9800),
        ("razer", "Razer Kaira Pro", "Over-Ear", "Wireless", 50, True, 12800),
        ("steelseries", "SteelSeries Arctis Nova 4", "Over-Ear", "Wired", 40, True, 9200),
        ("steelseries", "SteelSeries Arctis 9", "Over-Ear", "Wireless", 40, True, 15500),
        ("corsair", "Corsair HS35 Stereo", "Over-Ear", "Wired", 50, False, 2600),
        ("corsair", "Corsair Void Pro RGB", "Over-Ear", "Wireless", 50, True, 8500),
        ("hyperx", "HyperX Cloud Stinger", "Over-Ear", "Wired", 50, False, 3800),
        ("hyperx", "HyperX Cloud Mix", "Over-Ear", "Wired", 40, False, 16500),
        ("hyperx", "HyperX Cloud III Wireless", "Over-Ear", "Wireless", 53, True, 16500),
        ("asus", "ASUS ROG Delta S", "Over-Ear", "Wired", 50, True, 16500),
        ("asus", "ASUS TUF Gaming H3", "Over-Ear", "Wired", 50, False, 4200),
        ("msi", "MSI Immerse GH50", "Over-Ear", "Wired", 40, True, 6500),
        ("msi", "MSI Immerse GH61", "Over-Ear", "Wireless", 40, True, 11500),
        ("sony", "Sony INZONE H5", "Over-Ear", "Wireless", 40, True, 12500),
    ]
    out = []
    for brand, name, typ, conn, driver, surround, price in H:
        out.append({
            "name": name,
            "brand": brand,
            "price": price,
            "compare_at": None,
            "specs": {
                "type": typ, "connectivity": conn, "driver_mm": str(driver),
                "surround": "Yes" if surround else "No", "warranty": "2 Years",
            },
        })
    return out


def gen_tablets():
    """(brand, name, size, chipset, ram, storage, battery, os, price)"""
    T = [
        ("apple", "Apple iPad 9th Gen", 10.2, "Apple A13 Bionic", 3, 64, 8686, "iPadOS 17", 35000),
        ("apple", "Apple iPad 9th Gen", 10.2, "Apple A13 Bionic", 3, 256, 8686, "iPadOS 17", 49000),
        ("apple", "Apple iPad 10th Gen", 10.9, "Apple A14 Bionic", 4, 64, 7606, "iPadOS 17", 45000),
        ("apple", "Apple iPad 10th Gen", 10.9, "Apple A14 Bionic", 4, 256, 7606, "iPadOS 17", 59000),
        ("apple", "Apple iPad Air M1 11", 10.9, "Apple M1", 8, 64, 7606, "iPadOS 17", 75000),
        ("apple", "Apple iPad Air M2 11", 11.0, "Apple M2", 8, 128, 7606, "iPadOS 18", 89000),
        ("apple", "Apple iPad Air M2 13", 13.0, "Apple M2", 8, 128, 7606, "iPadOS 18", 115000),
        ("apple", "Apple iPad Pro 11 M2", 11.0, "Apple M2", 8, 128, 7538, "iPadOS 17", 135000),
        ("apple", "Apple iPad Pro 13 M4", 13.0, "Apple M4", 8, 256, 8160, "iPadOS 18", 195000),
        ("apple", "Apple iPad mini 6", 8.3, "Apple A15 Bionic", 4, 64, 5193, "iPadOS 17", 68000),
        ("samsung", "Samsung Galaxy Tab A8", 10.5, "Unisoc Tiger T618", 3, 32, 7040, "Android 13", 21000),
        ("samsung", "Samsung Galaxy Tab A9", 8.7, "MediaTek Helio G99", 4, 64, 5100, "Android 14", 19000),
        ("samsung", "Samsung Galaxy Tab A9+", 11.0, "Snapdragon 695", 8, 128, 7040, "Android 14", 32000),
        ("samsung", "Samsung Galaxy Tab S6 Lite", 10.4, "Exynos 1280", 4, 64, 7040, "Android 14", 34000),
        ("samsung", "Samsung Galaxy Tab S8", 11.0, "Snapdragon 8 Gen 1", 8, 128, 8000, "Android 14", 82000),
        ("samsung", "Samsung Galaxy Tab S9", 11.0, "Snapdragon 8 Gen 2", 8, 128, 8400, "Android 14", 98000),
        ("samsung", "Samsung Galaxy Tab S9 FE", 10.9, "Exynos 1380", 6, 128, 8000, "Android 14", 58000),
        ("samsung", "Samsung Galaxy Tab S9 FE+", 12.4, "Exynos 1380", 8, 256, 10090, "Android 14", 72000),
        ("samsung", "Samsung Galaxy Tab S9 Ultra", 14.6, "Snapdragon 8 Gen 2", 12, 256, 11200, "Android 14", 145000),
        ("xiaomi", "Xiaomi Pad 5", 11.0, "Snapdragon 860", 6, 128, 8720, "Android 13", 38000),
        ("xiaomi", "Xiaomi Pad 6", 11.0, "Snapdragon 870", 6, 128, 8840, "Android 13", 45000),
        ("xiaomi", "Redmi Pad SE", 11.0, "Snapdragon 680", 4, 128, 8000, "Android 13", 22000),
        ("xiaomi", "Redmi Pad Pro", 12.1, "Snapdragon 7s Gen 2", 6, 128, 10000, "Android 14", 35000),
        ("lenovo", "Lenovo Tab M10 3rd Gen", 10.1, "Unisoc T610", 4, 64, 5000, "Android 12", 18000),
        ("lenovo", "Lenovo Tab M11", 11.0, "MediaTek Helio G88", 4, 128, 7040, "Android 13", 25000),
        ("lenovo", "Lenovo Tab P12", 12.7, "MediaTek Dimensity 7050", 8, 128, 10200, "Android 13", 45000),
        ("apple", "Apple iPad Air M1 11", 10.9, "Apple M1", 8, 256, 7606, "iPadOS 17", 88000),
        ("apple", "Apple iPad 10th Gen", 10.9, "Apple A14 Bionic", 4, 512, 7606, "iPadOS 18", 72000),
        ("apple", "Apple iPad Pro 11 M4", 11.0, "Apple M4", 8, 256, 8160, "iPadOS 18", 155000),
        ("samsung", "Samsung Galaxy Tab S6 Lite", 10.4, "Exynos 1280", 4, 128, 7040, "Android 14", 38000),
        ("samsung", "Samsung Galaxy Tab S8 Plus", 12.4, "Snapdragon 8 Gen 1", 8, 128, 10090, "Android 14", 108000),
        ("samsung", "Samsung Galaxy Tab S9 Plus", 12.4, "Snapdragon 8 Gen 2", 12, 256, 10090, "Android 14", 118000),
        ("samsung", "Samsung Galaxy Tab S9 Ultra 512GB", 14.6, "Snapdragon 8 Gen 2", 12, 512, 11200, "Android 14", 158000),
        ("xiaomi", "Xiaomi Pad 6s Pro", 12.4, "Snapdragon 8 Gen 2", 8, 256, 10000, "Android 14", 65000),
        ("xiaomi", "Xiaomi Redmi Pad", 10.6, "MediaTek Helio G99", 6, 128, 8000, "Android 13", 26000),
        ("lenovo", "Lenovo Tab M10 Plus 3rd Gen", 10.6, "MediaTek Helio G80", 4, 64, 7700, "Android 12", 22000),
        ("lenovo", "Lenovo Tab P12 Pro", 12.6, "Snapdragon 870", 8, 256, 10200, "Android 13", 72000),
        ("lenovo", "Lenovo Tab Extreme", 14.5, "MediaTek Dimensity 9000", 12, 256, 12300, "Android 13", 115000),
        ("realme", "realme Pad 2", 11.5, "MediaTek Helio G99", 6, 128, 8360, "Android 13", 28000),
        ("oppo", "Oppo Pad Air", 10.36, "Snapdragon 680", 4, 64, 7100, "Android 12", 22000),
    ]
    out = []
    for brand, name, size, chip, ram, sto, mah, os_, price in T:
        suffix = f" ({sto}GB)" if name.split()[-1].isdigit() else ""
        out.append({
            "name": f"{name}{suffix}",
            "brand": brand,
            "price": price,
            "compare_at": None,
            "specs": {
                "display_size": str(size), "chipset": chip, "ram_gb": str(ram),
                "storage_gb": str(sto), "battery_mah": str(mah), "os": os_,
            },
        })
    return out


def gen_accessories():
    """(brand, name, acc type, compatibility/warranty spec, price)"""
    A = [
        # Air coolers
        ("deepcool", "DeepCool AK400 CPU Cooler", "CPU Cooler", "120mm tower, up to 220W TDP", 3500),
        ("deepcool", "DeepCool AK500 CPU Cooler", "CPU Cooler", "120mm tower, up to 250W TDP", 4900),
        ("deepcool", "DeepCool AG400 CPU Cooler", "CPU Cooler", "120mm tower, up to 220W TDP", 2900),
        ("deepcool", "DeepCool Gammaxx GT BK", "CPU Cooler", "120mm RGB tower", 2700),
        ("cooler-master", "Cooler Master Hyper 212 Black", "CPU Cooler", "120mm tower", 3200),
        ("cooler-master", "Cooler Master Hyper 620S", "CPU Cooler", "Dual-tower, up to 245W TDP", 5600),
        ("thermaltake", "Thermaltake TOUGHAIR 510", "CPU Cooler", "Dual 120mm tower", 4200),
        ("nzxt", "NZXT T120 RGB CPU Cooler", "CPU Cooler", "120mm RGB tower", 4500),
        ("noctua", "Noctua NH-U12S", "CPU Cooler", "120mm tower, NF-F12 fan", 8500),
        ("noctua", "Noctua NH-D15 chromax.black", "CPU Cooler", "Dual-tower flagship", 16500),
        # AIO liquid coolers
        ("nzxt", "NZXT Kraken 240 RGB AIO", "Liquid Cooler", "240mm radiator", 13500),
        ("nzxt", "NZXT Kraken 280 RGB AIO", "Liquid Cooler", "280mm radiator", 15500),
        ("nzxt", "NZXT Kraken 360 RGB AIO", "Liquid Cooler", "360mm radiator", 18500),
        ("corsair", "Corsair H60 AIO", "Liquid Cooler", "120mm radiator", 7500),
        ("corsair", "Corsair H100x RGB AIO", "Liquid Cooler", "240mm radiator", 11500),
        ("corsair", "Corsair H150i Elite LCD AIO", "Liquid Cooler", "360mm radiator", 26500),
        ("cooler-master", "Cooler Master MasterLiquid 240L Core", "Liquid Cooler", "240mm radiator", 9800),
        ("cooler-master", "Cooler Master MasterLiquid 360L Core", "Liquid Cooler", "360mm radiator", 12800),
        ("deepcool", "DeepCool LE520 AIO", "Liquid Cooler", "240mm radiator", 8500),
        # Thermal paste
        ("arctic", "Arctic MX-4 Thermal Paste (4g)", "Thermal Paste", "All CPUs and GPUs", 750),
        ("noctua", "Noctua NT-H1 Thermal Paste (3.5g)", "Thermal Paste", "All CPUs", 1100),
        ("thermal-grizzly", "Thermal Grizzly Kryonaut (1g)", "Thermal Paste", "High-performance paste", 950),
        ("cooler-master", "Cooler Master MasterGel Maker", "Thermal Paste", "High conductivity", 1250),
        ("deepcool", "DeepCool EX750 Thermal Paste (4g)", "Thermal Paste", "All CPUs", 550),
        # Cables & hubs
        ("ugreen", "Ugreen USB-C 6-in-1 Hub", "USB Hub", "USB-C laptops, 4K HDMI + PD 100W", 3200),
        ("ugreen", "Ugreen USB-C 9-in-1 Hub", "USB Hub", "USB-C laptops, dual 4K HDMI", 5800),
        ("ugreen", "Ugreen HDMI 2.1 Cable 2m 8K", "Cable", "8K60 / 4K120 displays", 1100),
        ("ugreen", "Ugreen DisplayPort 1.4 Cable 2m", "Cable", "8K60 / 4K144 displays", 950),
        ("baseus", "Baseus USB-C to USB-C 100W Cable", "Cable", "100W PD charging, 2m", 850),
        ("baseus", "Baseus USB-C to HDMI 4K Adapter", "Adapter", "USB-C laptops to 4K displays", 1800),
        ("apple", "Apple Thunderbolt 4 Pro Cable 1m", "Cable", "Thunderbolt 4 / USB4 devices", 6500),
        # Chargers & power banks
        ("baseus", "Baseus 65W GaN Fast Charger", "Charger", "USB-C PD 3.0, dual-port", 3200),
        ("baseus", "Baseus 100W GaN Pro Charger", "Charger", "4-port GaN II desktop", 5200),
        ("baseus", "Baseus 20W PD Mini Charger", "Charger", "iPhone fast charging", 1200),
        ("anker", "Anker 511 Charger 30W", "Charger", "USB-C PD, Nano design", 2200),
        ("anker", "Anker 737 Power Bank 24000mAh 140W", "Power Bank", "Laptops and phones", 14500),
        ("anker", "Anker 323 Power Bank 10000mAh", "Power Bank", "22.5W fast charge", 3500),
        ("xiaomi", "Xiaomi 33W Wall Charger", "Charger", "Xiaomi/Redmi phones", 1500),
        ("samsung", "Samsung 25W PD Charger", "Charger", "Galaxy Super Fast Charging", 1800),
        # Networking
        ("tp-link", "TP-Link Archer C6 AC1200 Router", "Wi-Fi Router", "Dual-band AC1200", 3600),
        ("tp-link", "TP-Link Archer C24 AC750 Router", "Wi-Fi Router", "Dual-band AC750", 2500),
        ("tp-link", "TP-Link Archer AX23 AX1800 Router", "Wi-Fi Router", "Wi-Fi 6 AX1800", 5200),
        ("tp-link", "TP-Link Archer AX55 AX3000 Router", "Wi-Fi Router", "Wi-Fi 6 AX3000", 7500),
        ("tp-link", "TP-Link Deco X20 (2-pack)", "Mesh Wi-Fi", "AX1800 mesh system", 13500),
        # Webcams
        ("logitech", "Logitech C270 HD Webcam", "Webcam", "720p30, built-in mic", 2200),
        ("logitech", "Logitech C505 HD Webcam", "Webcam", "720p30, long-range mic", 2600),
        ("logitech", "Logitech C920 HD Pro Webcam", "Webcam", "1080p30 autofocus", 6500),
        ("logitech", "Logitech Brio 500 Webcam", "Webcam", "1080p60, RightLight 4", 13500),
        ("logitech", "Logitech StreamCam", "Webcam", "1080p60 USB-C", 12500),
        # Mousepads
        ("steelseries", "SteelSeries QcK Heavy Mousepad", "Mousepad", "6mm thick cloth, Medium", 1500),
        ("steelseries", "SteelSeries QcK Prism Cloth 3XL", "Mousepad", "RGB 2-zone lighting", 4500),
        ("razer", "Razer Goliathus Speed Medium", "Mousepad", "Soft cloth, speed surface", 1800),
        ("razer", "Razer Strider Chroma", "Mousepad", "RGB hybrid hard-soft", 5200),
        ("logitech", "Logitech Desk Mat Studio Series", "Mousepad", "Full desk, anti-slip", 2800),
        # Storage cards
        ("samsung", "Samsung EVO Plus microSD 128GB", "microSD Card", "130MB/s, U3", 1300),
        ("samsung", "Samsung EVO Plus microSD 256GB", "microSD Card", "130MB/s, U3", 2400),
        ("samsung", "Samsung EVO Plus microSD 512GB", "microSD Card", "130MB/s, U3", 4800),
        ("sandisk", "SanDisk Ultra microSD 128GB", "microSD Card", "120MB/s, A1", 1200),
        ("sandisk", "SanDisk Extreme Pro microSD 256GB", "microSD Card", "200MB/s, A2", 4200),
        ("kingston", "Kingston Canvas Go Plus 128GB", "microSD Card", "170MB/s, A2", 1500),
        # Misc
        ("ugreen", "Ugreen Laptop Stand Aluminum", "Laptop Stand", "Adjustable 10-15 inch laptops", 2400),
        ("baseus", "Baseus Laptop Stand Foldable", "Laptop Stand", "Up to 17 inch laptops", 1900),
        ("logitech", "Logitech Z120 2.0 Speakers", "Speakers", "USB powered stereo", 1500),
        ("corsair", "Corsair iCUE SP120 RGB Fan (3-pack)", "Case Fan", "120mm PWM RGB fans", 4200),
        ("deepcool", "DeepCool FC120 Fan (3-pack)", "Case Fan", "120mm ARGB fans", 2800),
        ("nzxt", "NZXT F120 RGB Duo Fan", "Case Fan", "120mm dual-sided RGB", 1900),
        ("ugreen", "Ugreen USB-C 4-in-1 Hub", "USB Hub", "USB-C laptops, HDMI + 3x USB 3.0", 2400),
        ("ugreen", "Ugreen USB-C SD Card Reader", "Card Reader", "USB-C, UHS-II SD/microSD", 1200),
        ("baseus", "Baseus USB-C 8-in-1 Docking Station", "USB Hub", "USB-C laptops, dual display", 6500),
        ("anker", "Anker 555 USB-C Hub 8-in-1", "USB Hub", "4K HDMI, 100W PD passthrough", 7500),
        ("tp-link", "TP-Link RE305 AC1200 Extender", "Wi-Fi Extender", "Dual-band AC1200", 3200),
        ("tp-link", "TP-Link UE306 USB 3.0 Ethernet Adapter", "Network Adapter", "Gigabit USB adapter", 1100),
        ("logitech", "Logitech Z313 2.1 Speakers", "Speakers", "25W 2.1 channel", 4200),
        ("logitech", "Logitech C310 HD Webcam", "Webcam", "720p30 built-in mic", 2000),
        ("cooler-master", "Cooler Master SickleFlow 120 Fan", "Case Fan", "120mm PWM fan", 950),
        ("corsair", "Corsair AF120 LED Fan (3-pack)", "Case Fan", "120mm LED fans", 2800),
        ("thermal-grizzly", "Thermal Grizzly Kryonaut (5.5g)", "Thermal Paste", "High-performance paste", 4200),
        ("arctic", "Arctic MX-6 Thermal Paste (4g)", "Thermal Paste", "All CPUs and GPUs", 950),
        ("deepcool", "DeepCool P14 Fan", "Case Fan", "140mm PWM fan", 850),
        ("noctua", "Noctua NF-A12x25 PWM Fan", "Case Fan", "120mm premium fan", 3800),
        ("baseus", "Baseus Metal Gleam II Wireless Mouse Pad", "Mousepad", "Wireless charging pad", 3500),
        ("ugreen", "Ugreen Laptop Cooling Pad", "Cooling Pad", "5-fan, up to 17 inch laptops", 2200),
        ("samsung", "Samsung 45W PD Charger", "Charger", "Galaxy Super Fast Charging 2.0", 2500),
        ("anker", "Anker PowerPort III 65W Pod", "Charger", "USB-C PD 3.0 GaN", 4500),
        ("baseus", "Baseus Power Bank 20000mAh 22.5W", "Power Bank", "Triple output fast charge", 4200),
        ("xiaomi", "Xiaomi Power Bank 3 20000mAh", "Power Bank", "18W fast charge", 3300),
        ("ugreen", "Ugreen 4K HDMI Switch 3-in-1 Out", "HDMI Switch", "3 sources to 1 display, 4K60", 1900),
        ("baseus", "Baseus USB-C Car Charger 65W", "Charger", "Dual USB-C car charging", 2100),
        ("sandisk", "SanDisk Ultra Dual Drive Go USB-C 128GB", "Flash Drive", "USB-C + USB-A OTG", 1400),
        ("kingston", "Kingston DataTraveler Exodia 128GB", "Flash Drive", "USB 3.2 Gen 1", 950),
        ("apple", "Apple 20W USB-C Power Adapter", "Charger", "iPhone/iPad fast charging", 2900),
    ]
    out = []
    for brand, name, typ, compat, price in A:
        out.append({
            "name": name,
            "brand": brand,
            "price": price,
            "compare_at": None,
            "specs": {"type": typ, "compatibility": compat, "warranty": "1 Year"},
        })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Descriptions (1-3 sentences, per category)
# ─────────────────────────────────────────────────────────────────────────────

def make_description(cat_slug, name, specs):
    s = specs
    if cat_slug == "laptops":
        return (
            f"{name} powered by {s['cpu']} with {s['ram_gb']}GB RAM and {s['storage_gb']}GB SSD storage. "
            f"Features a {s['display_size']}-inch display, {s['gpu']} graphics and a {s['battery_wh']}Wh battery — "
            f"great for work, study and everyday multitasking."
        )
    if cat_slug == "phones":
        return (
            f"{name} with {s['chipset']}, {s['ram_gb']}GB RAM and {s['storage_gb']}GB storage. "
            f"{s['display_size']}-inch {s['refresh_rate']}Hz display, {s['camera_mp']}MP main camera and a {s['battery_mah']}mAh battery."
        )
    if cat_slug == "monitors":
        hdr = "" if s["hdr"] == "No HDR" else f" {s['hdr']} supported."
        return (
            f"{name}: {s['display_size']}-inch {s['display_resolution']} {s['panel_type']} monitor "
            f"at {s['refresh_rate']}Hz with {s['response_time']}ms response time.{hdr}"
        )
    if cat_slug == "processors":
        igpu = f" Integrated {s['integrated_gpu']} graphics." if s["integrated_gpu"] != "None" else " Discrete graphics required."
        return (
            f"{name} — {s['cores']} cores / {s['threads']} threads, up to {s['boost_clock_ghz']}GHz "
            f"on the {s['socket']} socket.{igpu}"
        )
    if cat_slug == "graphics-cards":
        return (
            f"{name} with {s['memory_gb']}GB {s['memory_type']} memory and boost clock up to {s['boost_clock']}MHz. "
            f"{s['length_mm']}mm card with a {s['tdp']}W TDP — ready for high-refresh 1080p and 1440p gaming."
        )
    if cat_slug == "ram":
        rgb = " with RGB lighting" if s["rgb"] == "Yes" else ""
        return (
            f"{name} memory kit ({s['modules']} module{'s' if s['modules'] != '1' else ''}){rgb}. "
            f"Runs at {s['speed_mhz']}MHz for stable overclocked performance."
        )
    if cat_slug == "storage":
        return (
            f"{name} — {s['capacity_gb']}GB {s['form_factor']} drive on {s['interface']}. "
            f"Sequential read up to {s['read_mb_s']}MB/s and write up to {s['write_mb_s']}MB/s."
        )
    if cat_slug == "motherboards":
        return (
            f"{name} — {s['form_factor']} board for the {s['socket']} socket with the {s['chipset']} chipset. "
            f"Supports {s['memory_type']} memory and includes {s['m2_slots']} M.2 slot(s)."
        )
    if cat_slug == "power-supplies":
        return (
            f"{name} power supply with {s['efficiency']} certification and {s['modular'].lower()} cabling. "
            f"Reliable {s['warranty']} warranty coverage."
        )
    if cat_slug == "cases":
        return (
            f"{name} chassis supporting {s['form_factor']} motherboards with a {s['side_panel'].lower()} side panel. "
            f"Comes with {s['preinstalled_fans']} pre-installed fan(s)."
        )
    if cat_slug == "keyboards":
        return (
            f"{name} keyboard with {s['switch_type']} switches, {s['layout']} layout and {s['connectivity'].lower()} connection."
            + (" Per-key RGB lighting included." if s["rgb"] == "Yes" else "")
        )
    if cat_slug == "mice":
        return (
            f"{name} gaming mouse with up to {s['dpi_max']} DPI, {s['connectivity'].lower()} connection and {s['weight_g']}g weight."
            + (" RGB lighting included." if s["rgb"] == "Yes" else "")
        )
    if cat_slug == "headsets":
        return (
            f"{name} {s['type'].lower()} gaming headset with {s['driver_mm']}mm drivers and {s['connectivity'].lower()} connection."
            + (" Virtual surround sound supported." if s["surround"] == "Yes" else "")
        )
    if cat_slug == "tablets":
        return (
            f"{name} with a {s['display_size']}-inch display, {s['chipset']}, {s['ram_gb']}GB RAM and {s['storage_gb']}GB storage. "
            f"Runs {s['os']} with a {s['battery_mah']}mAh battery for all-day use."
        )
    # accessories
    return f"{name} — {s['compatibility']}. Backed by a {s['warranty']} warranty."


# ─────────────────────────────────────────────────────────────────────────────
# Reviews / Coupons / Orders data
# ─────────────────────────────────────────────────────────────────────────────

REVIEWER_NAMES = [
    "Rahim Uddin", "Tanvir Hasan", "Nusrat Jahan", "Sabbir Ahmed", "Mehedi Hasan",
    "Farhana Akter", "Arif Chowdhury", "Sadia Islam", "Rakib Hossain", "Imran Kabir",
    "Shahriar Alam", "Tanjina Rahman", "Mahmudul Karim", "Jannatul Ferdous", "Hasibul Islam",
    "Rashed Khan", "Sumaiya Akter", "Fahim Rahman", "Nazmul Huda", "Ayesha Siddika",
    "Shafin Ahmed", "Rumana Parvin", "Touhid Anwar", "Mizanur Rahman",
]

REVIEW_COMMENTS = {
    5: [
        "Excellent product, fully satisfied. Delivered fast and packaging was perfect.",
        "Best value for money at this price. Highly recommended for anyone in Bangladesh.",
        "Genuine product with official warranty. Performance is exactly as advertised.",
        "Works flawlessly. Been using it for a month with zero issues.",
        "Top quality. Customer support from the shop was also very helpful.",
        "Exceeded my expectations. Bought a second one for my brother.",
    ],
    4: [
        "Very good product overall, just wish the price was a bit lower.",
        "Great performance, though the box was slightly damaged on arrival. Product fine.",
        "Solid build quality. Delivery took 4 days but worth the wait.",
        "Good value. Does everything I need without any complaints.",
        "Happy with the purchase. Would have given 5 stars if the bundle included more accessories.",
    ],
    3: [
        "Decent product but it runs a bit warm under heavy load.",
        "Average experience. Does the job but nothing special.",
        "Okay for the price. Check benchmarks before buying at this budget.",
        "Product is fine but delivery was slow in my area.",
    ],
    2: [
        "Expected better quality at this price point.",
        "Had to replace the unit once. Shop support was responsive at least.",
    ],
    1: [
        "Not recommended. Received a used unit and had to return it.",
    ],
}

COUPONS = [
    # (code, description, percent, amount, min_order, max_discount, usage_limit, days_valid)
    ("TECH10", "10% off on all tech products", 10.0, 0, 0, None, 500, 90),
    ("WELCOME500", "Flat ৳500 off for first orders above ৳5,000", 0.0, 500, 5000, None, 1000, 120),
    ("GAMING15", "15% off gaming gear, up to ৳3,000", 15.0, 0, 2000, 3000, 300, 60),
    ("FREESHIP", "Free shipping up to ৳120 on orders above ৳1,500", 0.0, 120, 1500, None, 2000, 90),
    ("FESTIVE20", "Festive deal: 20% off up to ৳5,000 on big purchases", 20.0, 0, 10000, 5000, 200, 30),
]

BD_GUEST_NAMES = REVIEWER_NAMES + [
    "Kamrul Islam", "Shirin Akter", "Jubayer Ahmed", "Maliha Chowdhury", "Raihan Kabir",
    "Sharmin Sultana", "Ashraf Ali", "Nadia Haque", "Zahid Hasan", "Priya Das",
]

BD_AREAS = {
    "Dhaka Metro": ["Dhanmondi", "Mirpur", "Uttara", "Banani", "Bashundhara R/A", "Mohammadpur", "Gulshan"],
    "Dhaka District": ["Savar", "Keraniganj", "Narayanganj", "Gazipur"],
    "Chittagong": ["Agrabad", "Khulshi", "Panchlaish", "Halishahar"],
    "Sylhet": ["Zindabazar", "Shibganj", "Amberkhana"],
    "Rajshahi": ["Shaheb Bazar", "Uposhohor", "Kazla"],
    "Khulna": ["Sonadanga", "Khan Jahan Ali", "Boyra"],
    "Rangpur": ["Jahaj Company More", "Dhap", "Shapla Chattar"],
    "Barisal": ["Nathullabad", "Rupatoli", "Band Road"],
    "Mymensingh": ["Chorpara", "Ganginarpar", "Maskanda"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Main seeding
# ─────────────────────────────────────────────────────────────────────────────

GENERATORS = {
    "laptops": gen_laptops,
    "phones": gen_phones,
    "monitors": gen_monitors,
    "processors": gen_processors,
    "graphics-cards": gen_graphics_cards,
    "ram": gen_ram,
    "storage": gen_storage,
    "motherboards": gen_motherboards,
    "power-supplies": gen_power_supplies,
    "cases": gen_cases,
    "keyboards": gen_keyboards,
    "mice": gen_mice,
    "headsets": gen_headsets,
    "tablets": gen_tablets,
    "accessories": gen_accessories,
}


def _ensure_brands(db):
    created = 0
    for name, slug in EXTRA_BRANDS:
        if not db.query(Brand).filter(Brand.slug == slug).first():
            db.add(Brand(name=name, slug=slug, is_active=True))
            created += 1
    db.commit()
    if created:
        print(f"[OK] Created {created} supplementary brands")
    return {b.slug: b for b in db.query(Brand).all()}


def _ensure_templates(db, cats):
    """Create/merge spec templates for ALL 15 categories (keeps existing keys)."""
    for slug, tmpl in TEMPLATES.items():
        cat = cats.get(slug)
        if not cat:
            continue
        existing = db.query(SpecificationTemplate).filter(
            SpecificationTemplate.category_id == cat.id
        ).first()
        if not existing:
            db.add(SpecificationTemplate(category_id=cat.id, template=dict(tmpl)))
        else:
            merged = dict(existing.template or {})
            changed = False
            for k, v in tmpl.items():
                if k not in merged:
                    merged[k] = v
                    changed = True
            if changed:
                existing.template = merged
    db.commit()
    print(f"[OK] Spec templates ensured for all {len(TEMPLATES)} categories")


def _numeric_keys(template: dict) -> set:
    return {k for k, v in (template or {}).items() if isinstance(v, dict) and v.get("type") == "number"}


def _seed_spec_options(db, cats):
    """Populate SpecificationOption rows for enum specs from curated value lists."""
    curated = {
        "processors": {
            "socket": ["LGA 1700", "AM4", "AM5"],
            "integrated_gpu": ["None", "Intel UHD 730", "Intel UHD 770", "AMD Radeon Graphics",
                               "AMD Radeon Vega 7", "AMD Radeon 740M", "AMD Radeon 760M", "AMD Radeon 780M"],
        },
        "graphics-cards": {
            "memory_type": ["GDDR6", "GDDR6X"],
            "socket": ["PCIe 4.0 x16"],
        },
        "ram": {"type": ["DDR4", "DDR5"]},
        "storage": {
            "interface": ["PCIe 3.0 x4 NVMe", "PCIe 4.0 x4 NVMe", "SATA 6Gb/s", "USB 3.2 Gen 2"],
            "form_factor": ["M.2 2280", "2.5-inch", "3.5-inch", "Portable"],
        },
        "motherboards": {
            "socket": ["LGA 1700", "AM4", "AM5"],
            "form_factor": ["ATX", "Micro-ATX", "Mini-ITX"],
            "memory_type": ["DDR4", "DDR5"],
        },
        "power-supplies": {
            "efficiency": ["80+ Standard", "80+ Bronze", "80+ Gold", "80+ Platinum", "80+ Titanium"],
            "modular": ["Non-Modular", "Semi-Modular", "Fully Modular"],
        },
        "cases": {
            "form_factor": ["ATX", "Micro-ATX", "Mini-ITX", "Mid-Tower"],
            "side_panel": ["Tempered Glass", "Acrylic"],
        },
        "keyboards": {
            "connectivity": ["Wired", "Wireless"],
            "layout": ["Full-Size", "TKL", "60%"],
        },
        "mice": {"connectivity": ["Wired", "Wireless"]},
        "headsets": {
            "connectivity": ["Wired", "Wireless"],
            "type": ["Over-Ear"],
        },
        "laptops": {"os": ["Windows 11", "macOS"], "storage_type": ["SSD"]},
        "phones": {"os": ["Android", "iOS"]},
        "tablets": {"os": ["iPadOS 17", "iPadOS 18", "Android 12", "Android 13", "Android 14"]},
        "monitors": {},
        "accessories": {},
    }
    created = 0
    for slug, by_key in curated.items():
        cat = cats.get(slug)
        if not cat:
            continue
        tmpl = db.query(SpecificationTemplate).filter(
            SpecificationTemplate.category_id == cat.id
        ).first()
        if not tmpl:
            continue
        existing_pairs = {
            (o.spec_key, o.value)
            for o in db.query(SpecificationOption).filter(SpecificationOption.template_id == tmpl.id).all()
        }
        for key, values in by_key.items():
            for i, val in enumerate(values):
                if (key, val) in existing_pairs:
                    continue
                db.add(SpecificationOption(
                    template_id=tmpl.id, spec_key=key, value=val,
                    display_name=val, sort_order=i, is_active=True,
                ))
                created += 1
    db.commit()
    if created:
        print(f"[OK] Created {created} specification options")


def _seed_products(db, cats, brands):
    """Generate and insert all products with primary images and full specs."""
    slug_set = {s for (s,) in db.query(Product.slug).all()}
    sku_set = {s for (s,) in db.query(Product.sku).all()}
    seq = len(slug_set)  # deterministic, continues after existing products

    templates = {
        slug: t for slug, t in (
            (c.slug, db.query(SpecificationTemplate)
                .filter(SpecificationTemplate.category_id == c.id).first())
            for c in cats.values()
        ) if t
    }
    numeric_by_cat = {slug: _numeric_keys(t.template) for slug, t in templates.items()}

    total_created = 0
    per_category = {}
    new_products = []  # Product ORM objects created here (with .id after flush)

    for cat_slug, gen in GENERATORS.items():
        cat = cats.get(cat_slug)
        if not cat:
            continue
        cat_code = CAT3[cat_slug]
        specs_list = gen()
        created_in_cat = 0
        pending = []

        for p in specs_list:
            brand = brands.get(p["brand"])
            if not brand:
                continue
            base_slug = slugify(p["name"])
            if base_slug in slug_set:
                continue  # already seeded — idempotency
            slug = base_slug
            sku = f"TC-{cat_code}-{sku_code(p['brand'])}-{seq + 1:05d}"
            while sku in sku_set:
                seq += 1
                sku = f"TC-{cat_code}-{sku_code(p['brand'])}-{seq + 1:05d}"
            seq += 1
            slug_set.add(slug)
            sku_set.add(sku)

            price, compare_at = p["price"], p.get("compare_at")
            if compare_at is None and RNG.random() < 0.35:
                compare_at = int(round(price * RNG.uniform(1.05, 1.15) / 100.0) * 100)
                if compare_at <= price:
                    compare_at = None

            stock = RNG.choice([0, 2, 3, 5, 8, 10, 12, 15, 18, 20, 25, 30, 35, 40, 45, 50, 60])
            featured = RNG.random() < 0.07
            popularity = round(RNG.uniform(0, 40) + (25 if featured else 0), 2)
            product = Product(
                name=p["name"], slug=slug, sku=sku,
                description=make_description(cat_slug, p["name"], p["specs"]),
                price=float(price), compare_at_price=float(compare_at) if compare_at else None,
                stock_quantity=stock,
                brand_id=brand.id, category_id=cat.id,
                is_active=True, is_featured=featured,
                popularity_score=popularity,
                view_count=int(RNG.uniform(80, 4200) * (1 + popularity / 60)),
            )
            pending.append((product, p["specs"]))
            created_in_cat += 1

        # Batch insert: flush products to get ids, then specs + images in bulk
        CHUNK = 150
        for i in range(0, len(pending), CHUNK):
            chunk = pending[i:i + CHUNK]
            db.add_all([prod for prod, _ in chunk])
            db.flush()
            new_products.extend([prod for prod, _ in chunk])
            num_keys = numeric_by_cat.get(cat_slug, set())
            spec_rows = []
            for prod, specs in chunk:
                for key, value in specs.items():
                    if value is None or value == "":
                        continue
                    nv = None
                    if key in num_keys:
                        try:
                            nv = float(str(value).split()[0].replace(",", ""))
                        except (ValueError, IndexError):
                            nv = None
                    spec_rows.append(ProductSpecification(
                        product_id=prod.id, spec_key=key, value=str(value), numeric_value=nv,
                    ))
            db.add_all(spec_rows)
            db.add_all([
                ProductImage(
                    product_id=prod.id, url=image_url(cat_slug),
                    alt_text=prod.name, sort_order=0, is_primary=True,
                )
                for prod, _ in chunk
            ])
        db.commit()
        per_category[cat_slug] = created_in_cat
        total_created += created_in_cat
        print(f"[OK] {cat_slug}: {created_in_cat} products")

    return total_created, per_category, new_products


def _backfill_existing_products(db, cats):
    """Give older products (from base seed) a primary image + numeric spec values if missing."""
    image_url_by_cat = {c.id: image_url(c.slug) for c in cats.values()}
    templates = {
        t.category_id: _numeric_keys(t.template)
        for t in db.query(SpecificationTemplate).all()
    }
    fixed_img = 0
    for product in db.query(Product).all():
        has_image = db.query(ProductImage.id).filter(ProductImage.product_id == product.id).first()
        if not has_image:
            url = image_url_by_cat.get(product.category_id)
            if url:
                db.add(ProductImage(
                    product_id=product.id, url=url, alt_text=product.name,
                    sort_order=0, is_primary=True,
                ))
                fixed_img += 1
    fixed_num = 0
    for spec in db.query(ProductSpecification).filter(ProductSpecification.numeric_value.is_(None)).all():
        keys = templates.get(spec.product.category_id, set()) if spec.product else set()
        if spec.spec_key in keys:
            try:
                spec.numeric_value = float(str(spec.value).split()[0].replace(",", ""))
                fixed_num += 1
            except (ValueError, IndexError):
                pass
    db.commit()
    if fixed_img or fixed_num:
        print(f"[OK] Backfilled {fixed_img} primary images, {fixed_num} numeric spec values on existing products")


def _seed_reviews(db, products):
    """Reviews for ~55% of products, 3-8 each, ratings skewed 4-5."""
    already = {pid for (pid,) in db.query(ProductReview.product_id).distinct().all()}
    targets = [p for p in products if p.id not in already and RNG.random() < 0.55]
    rows = []
    for p in targets:
        n = RNG.randint(3, 8)
        emails_used = set()
        for _ in range(n):
            reviewer = RNG.choice(REVIEWER_NAMES)
            email_key = reviewer
            if email_key in emails_used:
                continue
            emails_used.add(email_key)
            rating = RNG.choices([5, 4, 3, 2, 1], weights=[45, 30, 15, 7, 3])[0]
            first, last = reviewer.split(" ", 1)
            domain = RNG.choice(["gmail.com", "gmail.com", "gmail.com", "yahoo.com"])
            rows.append(ProductReview(
                product_id=p.id,
                reviewer_name=reviewer,
                reviewer_email=f"{first.lower()}.{last.lower().replace(' ', '.')}@{domain}",
                rating=rating,
                comment=RNG.choice(REVIEW_COMMENTS[rating]),
                is_verified=RNG.random() < 0.7,
                is_active=True,
                created_at=NOW - timedelta(days=RNG.uniform(0, 180)),
            ))
    CHUNK = 500
    for i in range(0, len(rows), CHUNK):
        db.add_all(rows[i:i + CHUNK])
        db.commit()
    print(f"[OK] Created {len(rows)} reviews across {len(targets)} products")
    return len(rows)


def _seed_coupons(db):
    existing = {c.code for c in db.query(Coupon).all()}
    created = 0
    for code, desc, percent, amount, min_order, max_disc, limit, days in COUPONS:
        if code in existing:
            continue
        db.add(Coupon(
            code=code, description=desc,
            discount_percent=percent, discount_amount=amount,
            min_order_amount=min_order, max_discount_amount=max_disc,
            usage_limit=limit, used_count=0, is_active=True,
            starts_at=NOW - timedelta(days=1),
            expires_at=NOW + timedelta(days=days),
        ))
        created += 1
    db.commit()
    print(f"[OK] Created {created} coupons")
    return created


def _seed_orders(db, products, zones):
    """40-60 guest orders over the last 60 days with consistent totals."""
    existing = {o for (o,) in db.query(Order.order_number).all()}
    if existing:
        print(f"[--] {len(existing)} orders already exist, skipping sample orders")
        return 0
    year = NOW.year
    prefix = f"TC{year}"
    used_nums = {o for o in existing if o.startswith(prefix)}
    next_num = max((int(o.replace(prefix, "")) for o in used_nums), default=0) + 1

    coupons = {c.code: c for c in db.query(Coupon).filter(Coupon.is_active == True).all()}  # noqa: E712
    eligible = [p for p in products if 1000 <= p.price <= 250000]
    if not eligible:
        print("[--] No eligible products for orders, skipping")
        return 0

    order_count = RNG.randint(48, 55)
    status_weights = [
        (OrderStatus.DELIVERED, 40), (OrderStatus.SHIPPED, 20),
        (OrderStatus.PROCESSING, 15), (OrderStatus.PAID, 8),
        (OrderStatus.PENDING, 9), (OrderStatus.CANCELLED, 8),
    ]
    statuses = [s for s, _ in status_weights]
    weights = [w for _, w in status_weights]
    zones_list = list(zones)
    coupon_uses = {code: 0 for code in coupons}

    created = 0
    for idx in range(order_count):
        created_at = NOW - timedelta(days=RNG.uniform(0, 60), hours=RNG.uniform(0, 20))
        status = RNG.choices(statuses, weights=weights)[0]

        # 1-3 items from seeded products
        n_items = RNG.choices([1, 2, 3], weights=[55, 30, 15])[0]
        chosen = RNG.sample(eligible, n_items)
        items = []
        subtotal = 0.0
        for prod in chosen:
            qty = RNG.choices([1, 2], weights=[85, 15])[0]
            unit = float(prod.price)
            line = round(unit * qty, 2)
            subtotal += line
            items.append((prod, qty, unit, line))

        # Optional coupon discount
        discount = 0.0
        discount_code = None
        if coupons and subtotal >= 5000 and RNG.random() < 0.22:
            code = RNG.choice(["TECH10", "WELCOME500", "GAMING15"])
            if code not in coupons:
                continue
            coupon = coupons[code]
            if subtotal >= float(coupon.min_order_amount or 0):
                if coupon.discount_percent:
                    discount = subtotal * coupon.discount_percent / 100
                    if coupon.max_discount_amount:
                        discount = min(discount, float(coupon.max_discount_amount))
                else:
                    discount = float(coupon.discount_amount or 0)
                discount = min(discount, subtotal)
                discount_code = code
                coupon_uses[code] = coupon_uses.get(code, 0) + 1

        zone = RNG.choice(zones_list)
        delivery_charge = float(zone.charge)
        total = round(subtotal - discount + delivery_charge, 2)

        guest_name = RNG.choice(BD_GUEST_NAMES)
        first, last = guest_name.split(" ", 1)
        guest_email = f"{first.lower()}.{last.lower().replace(' ', '.')}@{RNG.choice(['gmail.com', 'gmail.com', 'yahoo.com', 'outlook.com'])}"
        guest_phone = "01" + str(RNG.randint(3, 9)) + "".join(str(RNG.randint(0, 9)) for _ in range(8))
        area = RNG.choice(BD_AREAS.get(zone.city, ["Central"]))
        house = RNG.randint(1, 120)
        road = RNG.randint(1, 30)
        address = f"House {house}, Road {road}, {area}"

        if status == OrderStatus.PENDING:
            pay_status = RNG.choice([PaymentStatus.UNPAID, PaymentStatus.INITIATED])
        elif status == OrderStatus.CANCELLED:
            pay_status = PaymentStatus.FAILED if RNG.random() < 0.7 else PaymentStatus.REFUNDED
        else:
            pay_status = PaymentStatus.PAID

        method = RNG.choice([PaymentMethod.BKASH, PaymentMethod.NAGAD, PaymentMethod.SSLCOMMERZ])
        order_number = f"{prefix}{next_num:06d}"
        next_num += 1

        order = Order(
            order_number=order_number,
            guest_email=guest_email, guest_name=guest_name, guest_phone=guest_phone,
            subtotal=round(subtotal, 2), discount=round(discount, 2),
            delivery_charge=delivery_charge, total_amount=total,
            payment_method=method, payment_status=pay_status, order_status=status,
            shipping_address=address, shipping_city=zone.city, shipping_area=area,
            shipping_postal_code=str(RNG.randint(1000, 9999)),
            discount_code=discount_code,
            created_at=created_at, updated_at=created_at,
        )
        db.add(order)
        db.flush()

        for prod, qty, unit, line in items:
            db.add(OrderItem(
                order_id=order.id, product_id=prod.id,
                product_name=prod.name, product_sku=prod.sku,
                quantity=qty, unit_price=unit, subtotal=line,
            ))
        db.add(Payment(
            order_id=order.id, gateway=method,
            transaction_id=f"{method.value.upper()[:3]}{idx + 1:09d}",
            amount=total, currency="BDT", status=pay_status,
            paid_at=created_at if pay_status == PaymentStatus.PAID else None,
            created_at=created_at,
        ))
        created += 1
        if created % 10 == 0:
            db.commit()

    # Sync coupon usage counters
    for code, uses in coupon_uses.items():
        if uses and code in coupons:
            coupons[code].used_count = uses
    db.commit()
    print(f"[OK] Created {created} sample orders with items and payments")
    return created


def seed_catalog(db=None):
    """Entry point — call after scripts/seed.py base seeding (or standalone)."""
    owns_db = db is None
    if owns_db:
        db = SessionLocal()
    try:
        print("\n=== Catalog seeding: products, reviews, coupons, orders ===")
        brands = _ensure_brands(db)
        cats = {c.slug: c for c in db.query(Category).all()}
        if not cats:
            print("[!!] No categories found — run base seed first")
            return
        _ensure_templates(db, cats)
        svg_count = write_placeholder_svgs()
        print(f"[OK] {svg_count} category placeholder SVGs written to uploads/products/")
        _seed_spec_options(db, cats)

        total, per_category, new_products = _seed_products(db, cats, brands)
        _backfill_existing_products(db, cats)

        zones = db.query(DeliveryZone).filter(DeliveryZone.is_active == True).all()  # noqa: E712
        _seed_reviews(db, new_products)
        _seed_coupons(db)
        _seed_orders(db, new_products, zones)

        print(f"[DONE] Catalog seeding complete — {total} products added")
    finally:
        if owns_db:
            db.close()


if __name__ == "__main__":
    seed_catalog()
