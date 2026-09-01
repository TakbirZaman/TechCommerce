#!/usr/bin/env python3
"""
scrape_bd.py - Polite scraper importing real products from Bangladeshi
PC-hardware e-commerce sites into the TechCommerce catalog.

Sites / adapters:
  startech      www.startech.com.bd      HTML listing adapter (p-item cards)
  ryans         www.ryans.com            HTML adapter (data-item JSON attrs)
  mcsolution    www.mcsolution.com.bd    WooCommerce Store API (JSON)
  sumashtech    www.sumashtech.com.bd    (JS-rendered Nuxt SPA - auto-skip)
  computermania www.computermania.com.bd (Cloudflare-protected - auto-skip)

Politeness:
  - >= --delay (default 1.2s) between requests to the same host
  - single sequential worker, normal browser User-Agent
  - 429/503 -> exponential backoff (max 3 retries)
  - raw responses cached on disk in scripts/.scrape_cache/{host}/{sha1}
    so re-runs never re-fetch
  - only factual data is stored; descriptions are generated locally

Usage:
  python scripts/scrape_bd.py --site startech --limit-pages 2
  DATABASE_URL=sqlite:////tmp/scrape_test.db python scripts/scrape_bd.py

NOTE: DATABASE_URL must be set in the environment BEFORE this script runs
(it is read at core.database import time). If unset, the default
sqlite:///./techcommerce.db is used.
"""
from __future__ import annotations

import argparse
import hashlib
import html as html_mod
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin

import httpx

# Make repo root importable and read DATABASE_URL before core import
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.database import SessionLocal, init_db  # noqa: E402
from core.models.catalog import Brand, Category  # noqa: E402
from core.models.specification import (  # noqa: E402
    Product,
    ProductImage,
    ProductSpecification,
)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 is required: pip install beautifulsoup4")
    sys.exit(1)

CACHE_DIR = Path(__file__).resolve().parent / ".scrape_cache"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
DEFAULT_DELAY = 1.2
MAX_RETRIES = 3
STOCK_DEFAULT = 10
PRICE_MIN = 100.0          # BDT sanity floor
PRICE_MAX = 5_000_000.0    # BDT sanity ceiling

SITE3 = {
    "startech": "STA",
    "ryans": "RYA",
    "mcsolution": "MCS",
    "sumashtech": "SUM",
    "computermania": "CMA",
}

# Known brand tokens (longest-first matching on the product name prefix)
KNOWN_BRANDS = [
    "Western Digital", "Cooler Master", "ViewSonic", "A4 Tech", "G.SKILL",
    "ASUS", "MSI", "Gigabyte", "Zotac", "ZOTAC", "AMD", "Intel", "NVIDIA",
    "Corsair", "Kingston", "ADATA", "Adata", "Team", "Seagate", "Samsung",
    "LG", "Dell", "HP", "Lenovo", "Acer", "Apple", "Logitech", "Razer",
    "Fantech", "Havit", "Galax", "GALAX", "Colorful", "AFOX", "Maxsun",
    "Sapphire", "PowerColor", "XFX", "Deepcool", "DeepCool", "Thermaltake",
    "Antec", "Cougar", "TP-Link", "Xiaomi", "Redmi", "Realme", "Infinix",
    "Walton", "Microsoft", "BenQ", "AOC", "Philips", "Arzopa", "Dahua",
    "Hikvision", "Energizer", "Asus", "GIGABYTE", "Lexar", "Netac",
    "Klevv", "KLEVV", "Patriot", "Transcend", "Toshiba", "Epson",
    "Canon", "OnePlus", "OPPO", "Nubia", "Honor", "Huawei", "Tecno",
    "WOW", "Rebune", "Baseus", "Joyroom", "E-YOOSO", "Aigo", "WiWU",
    "Furious", "Imilab", "Marvo", "Rapoo", "Ugreen", "Oraimo",
]

# site category path (or WooCommerce category slug) -> our category slug
STARTECH_CATEGORIES = {
    "laptop-notebook": "laptops",
    "tablet-pc": "tablets",
    "mobile-phone": "phones",
    "monitor": "monitors",
    "component/processor": "processors",
    "component/graphics-card": "graphics-cards",
    "component/ram": "ram",
    "ssd": "storage",
    "component/hard-disk-drive": "storage",
    "component/motherboard": "motherboards",
    "component/power-supply": "power-supplies",
    "component/casing": "cases",
    "gaming-keyboard": "keyboards",
    "gaming-mouse": "mice",
    "headset": "headsets",
}
RYANS_CATEGORIES = {
    "laptop-all-laptop": "laptops",
    "tablet-all-tablet": "tablets",
    "monitor-all-monitor": "monitors",
    "desktop-component-processor": "processors",
    "desktop-component-graphics-card": "graphics-cards",
    "desktop-component-motherboard": "motherboards",
    "desktop-component-power-supply": "power-supplies",
    "desktop-component-ram": "ram",
}
# WooCommerce Store API category slugs (verified for graphics-card)
MCSOLUTION_CATEGORIES = {
    "laptop": "laptops",
    "tablet": "tablets",
    "mobile-phone": "phones",
    "monitor": "monitors",
    "processor": "processors",
    "graphics-card": "graphics-cards",
    "ram": "ram",
    "ssd": "storage",
    "hard-disk-drive": "storage",
    "motherboard": "motherboards",
    "power-supply": "power-supplies",
    "casing": "cases",
    "keyboard": "keyboards",
    "mouse": "mice",
    "headset": "headsets",
}


# ────────────────────────── helpers ──────────────────────────

def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)[:280] or "item"


def parse_price_bdt(text: str) -> float | None:
    """Parse '৳ 5,000', '5,000৳', 'Tk 5,000', 'BDT 5,000' etc."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    if not cleaned:
        return None
    try:
        val = float(cleaned)
    except ValueError:
        return None
    if not (PRICE_MIN <= val <= PRICE_MAX):
        return None
    return val


def extract_brand(name: str) -> str:
    for brand in KNOWN_BRANDS:
        if name.lower().startswith(brand.lower()):
            return brand
    first = name.split()[0] if name.split() else "Unknown"
    return first.strip("-#,")


def spec_key_from(label: str) -> str:
    return slugify(label).replace("-", "_")[:50]


def generate_description(name: str, specs: dict[str, str]) -> str:
    """Our own factual 1-2 sentence description (never source marketing text)."""
    if not specs:
        return f"{name}, available at TechCommerce."
    pairs = [f"{k.replace('_', ' ')}: {v}" for k, v in list(specs.items())[:4]]
    return f"{name} with {', '.join(pairs)}."


class PoliteFetcher:
    """Sequential fetcher: per-host delay, backoff on 429/503, disk cache."""

    def __init__(self, delay: float = DEFAULT_DELAY, use_cache: bool = True):
        self.delay = delay
        self.use_cache = use_cache
        self.last_hit: dict[str, float] = {}
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
            follow_redirects=True,
            timeout=30.0,
        )
        self.fetched = 0

    def get(self, url: str) -> httpx.Response | None:
        host = urlparse(url).netloc
        cache_path = CACHE_DIR / host / hashlib.sha1(url.encode()).hexdigest()

        if self.use_cache and cache_path.exists():
            return httpx.Response(
                200, content=cache_path.read_bytes(),
                headers={"content-type": "application/octet-stream"},
                request=httpx.Request("GET", url),
            )

        # per-host politeness delay
        elapsed = time.time() - self.last_hit.get(host, 0.0)
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self.client.get(url)
            except httpx.HTTPError as exc:
                print(f"    [net] {type(exc).__name__} on {url}")
                return None
            self.last_hit[host] = time.time()
            self.fetched += 1

            if resp.status_code == 200:
                if self.use_cache:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_bytes(resp.content)
                return resp
            if resp.status_code in (429, 503) and attempt < MAX_RETRIES:
                wait = (2 ** attempt) * 2.0
                print(f"    [backoff] {resp.status_code} on {host}, sleeping {wait:.0f}s")
                time.sleep(wait)
                continue
            return resp  # caller decides what to do with non-200
        return None


# ────────────────────────── adapters ──────────────────────────
# Each adapter yields dicts:
#   {name, brand, url, price, compare_price, image, specs: dict, site, cat_slug}

def scrape_startech(fetcher: PoliteFetcher, cat_map: dict, limit_pages: int,
                    deep: bool, stats: dict):
    """HTML adapter: OpenCart-style listing pages with p-item cards."""
    base = "https://www.startech.com.bd/"
    for site_cat, our_cat in cat_map.items():
        for page in range(1, limit_pages + 1):
            url = urljoin(base, f"{site_cat}?page={page}") if page > 1 \
                else urljoin(base, site_cat)
            resp = fetcher.get(url)
            if resp is None or resp.status_code != 200:
                print(f"  [startech] skip {url} (status {resp.status_code if resp else 'net-err'})")
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("div.p-item")
            if not cards:
                break  # ran past the last page
            for card in cards:
                try:
                    name_a = card.select_one("h4.p-item-name a")
                    if not name_a:
                        continue
                    name = name_a.get_text(strip=True)
                    price_spans = [
                        s.get_text(strip=True)
                        for s in card.select("div.p-item-price span")
                    ]
                    prices = [parse_price_bdt(p) for p in price_spans]
                    prices = [p for p in prices if p]
                    price = min(prices) if prices else None
                    compare = max(prices) if len(prices) > 1 else None
                    if price is None:
                        stats["errors"] += 1
                        continue
                    img_tag = card.select_one("div.p-item-img img")
                    image = urljoin(base, str(img_tag["src"])) \
                        if img_tag and img_tag.get("src") else None

                    specs: dict[str, str] = {}
                    li_tags = card.select("div.short-description ul li")
                    for li in li_tags:
                        txt = li.get_text(" ", strip=True)
                        if ":" in txt:
                            k, _, v = txt.partition(":")
                            specs[spec_key_from(k)] = v.strip()[:500]

                    yield {
                        "name": name,
                        "brand": extract_brand(name),
                        "url": urljoin(base, str(name_a.get("href", ""))),
                        "price": price,
                        "compare_price": compare,
                        "image": image,
                        "specs": specs,
                        "site": "startech",
                        "cat_slug": our_cat,
                    }
                    stats["parsed"] += 1
                except Exception as exc:
                    print(f"    [startech] parse error: {exc}")
                    stats["errors"] += 1


def scrape_ryans(fetcher: PoliteFetcher, cat_map: dict, limit_pages: int,
                 deep: bool, stats: dict):
    """HTML adapter: Laravel listing pages embed product JSON in data-item /
    data-attributes attributes on preview buttons."""
    base = "https://www.ryans.com/"
    for site_cat, our_cat in cat_map.items():
        for page in range(1, limit_pages + 1):
            url = urljoin(base, f"category/{site_cat}?page={page}")
            resp = fetcher.get(url)
            if resp is None or resp.status_code != 200:
                print(f"  [ryans] skip {url} (status {resp.status_code if resp else 'net-err'})")
                break
            html_text = resp.text
            found = 0
            seen_ids: set[int] = set()
            for m in re.finditer(r'data-item="([^"]+)"', html_text):
                try:
                    item = json.loads(html_mod.unescape(m.group(1)))
                except (json.JSONDecodeError, ValueError):
                    continue
                pid = item.get("product_id")
                if pid and pid in seen_ids:
                    continue  # same card rendered in grid + list view
                if pid:
                    seen_ids.add(pid)
                try:
                    name = (item.get("product_name") or "").strip()
                    price = float(item.get("product_price2") or 0) or \
                        float(item.get("product_price1") or 0)
                    price1 = float(item.get("product_price1") or 0)
                    price2 = float(item.get("product_price2") or 0)
                    price = price2 if price2 > 0 else price1
                    compare = price1 if price2 > 0 and price1 > price2 else None
                    if not name or price <= 0:
                        continue
                    price = price if PRICE_MIN <= price <= PRICE_MAX else None
                    if price is None:
                        continue

                    image_name = item.get("product_image_name")
                    image = urljoin(
                        base, f"storage/products/small/{image_name}"
                    ) if image_name else None  # noqa: see str() below
                    image = str(image) if image else None
                    product_url = slugify(name)
                    # derive detail URL from the card's product link when present
                    link_zone = html_text[max(0, m.start() - 4000):m.start()]
                    links = re.findall(r'href="(https://www\.ryans\.com/[a-z0-9-]+)"',
                                       link_zone)
                    product_url = links[-1] if links else None

                    specs: dict[str, str] = {}
                    attr_m = re.search(
                        r'data-attributes="([^"]+)"',
                        html_text[m.end():m.end() + 8000],
                    )
                    if attr_m:
                        attrs = json.loads(html_mod.unescape(attr_m.group(1)))
                        for k, v in (attrs.get("data") or {}).items():
                            if isinstance(v, str) and v.strip():
                                specs[spec_key_from(k)] = v.strip()[:500]

                    yield {
                        "name": name,
                        "brand": extract_brand(name),
                        "url": product_url or base,
                        "price": price,
                        "compare_price": compare,
                        "image": image,
                        "specs": specs,
                        "site": "ryans",
                        "cat_slug": our_cat,
                    }
                    stats["parsed"] += 1
                    found += 1
                except Exception as exc:
                    print(f"    [ryans] parse error: {exc}")
                    stats["errors"] += 1
            if found == 0:
                break


def scrape_mcsolution(fetcher: PoliteFetcher, cat_map: dict, limit_pages: int,
                      deep: bool, stats: dict):
    """WooCommerce Store API adapter (JSON, paginated)."""
    base = "https://www.mcsolution.com.bd"
    for site_cat, our_cat in cat_map.items():
        for page in range(1, limit_pages + 1):
            url = (f"{base}/wp-json/wc/store/v1/products"
                   f"?per_page=50&page={page}&category={site_cat}")
            resp = fetcher.get(url)
            if resp is None or resp.status_code != 200:
                print(f"  [mcsolution] skip {url} "
                      f"(status {resp.status_code if resp else 'net-err'})")
                break
            try:
                items = json.loads(resp.text)
            except json.JSONDecodeError:
                print(f"  [mcsolution] bad JSON at {url}")
                break
            if not items:
                break
            for p in items:
                try:
                    name = (p.get("name") or "").strip()
                    prices = p.get("prices", {})
                    minor = int(prices.get("currency_minor_unit") or 0)
                    div = 10 ** minor

                    def to_bdt(raw):
                        try:
                            return float(raw) / div
                        except (TypeError, ValueError):
                            return 0.0

                    price = to_bdt(prices.get("price"))
                    regular = to_bdt(prices.get("regular_price"))
                    if price <= 0:
                        continue  # variable products often show 0
                    compare = regular if regular > price else None
                    if not (PRICE_MIN <= price <= PRICE_MAX):
                        stats["errors"] += 1
                        continue

                    images = p.get("images") or []
                    image = images[0].get("src") if images else None
                    permalink = p.get("permalink") or url

                    specs: dict[str, str] = {}
                    for attr in p.get("attributes") or []:
                        label = attr.get("name") or attr.get("taxonomy") or ""
                        terms = attr.get("terms") or []
                        default = next(
                            (t["name"] for t in terms if t.get("default")), None)
                        val = default or (terms[0]["name"] if terms else None)
                        if label and val:
                            specs[spec_key_from(label)] = str(val)[:500]

                    yield {
                        "name": name,
                        "brand": extract_brand(name),
                        "url": permalink,
                        "price": price,
                        "compare_price": compare,
                        "image": image,
                        "specs": specs,
                        "site": "mcsolution",
                        "cat_slug": our_cat,
                    }
                    stats["parsed"] += 1
                except Exception as exc:
                    print(f"    [mcsolution] parse error: {exc}")
                    stats["errors"] += 1


def make_unsupported_adapter(url: str, reason: str):
    """Build an adapter that probes a site and reports why it is skipped."""
    def adapter(fetcher: PoliteFetcher, cat_map: dict, limit_pages: int,
                deep: bool, stats: dict):
        resp = fetcher.get(url)
        status = resp.status_code if resp is not None else "network-error"
        print(f"  SKIPPED: {reason} (probe status: {status})")
        stats["skipped_site"] = True
        return
        yield  # pragma: no cover - makes this a generator
    return adapter


ADAPTERS = {
    "startech": ("https://www.startech.com.bd/laptop-notebook",
                 scrape_startech, STARTECH_CATEGORIES),
    "ryans": ("https://www.ryans.com/category/laptop-all-laptop",
              scrape_ryans, RYANS_CATEGORIES),
    "mcsolution": ("https://www.mcsolution.com.bd/wp-json/wc/store/v1/products?per_page=1",
                   scrape_mcsolution, MCSOLUTION_CATEGORIES),
    "sumashtech": ("https://www.sumashtech.com/graphics-cards",
                   make_unsupported_adapter(
                       "https://www.sumashtech.com/graphics-cards",
                       "JS-rendered Nuxt SPA - product cards are not present in "
                       "the server HTML and the internal /api/ endpoints are "
                       "disallowed by robots.txt"),
                   {}),
    "computermania": ("https://www.computermania.com.bd",
                      make_unsupported_adapter(
                          "https://www.computermania.com.bd",
                          "Cloudflare bot protection (403 'Just a moment...' "
                          "challenge on every request)"),
                      {}),
}


# ────────────────────────── DB upsert ──────────────────────────

def deterministic_sku(site: str, identity: str) -> str:
    digest = hashlib.md5(identity.encode()).hexdigest()[:8]
    return f"SRC-{SITE3[site]}-{digest.upper()}"


def get_or_create_brand(db, name: str) -> Brand:
    slug = slugify(name)
    brand = db.query(Brand).filter(Brand.slug == slug).first()
    if brand:
        return brand
    brand = Brand(name=name.strip()[:120], slug=slug, is_active=True)
    db.add(brand)
    db.flush()
    print(f"    [brand] created: {name}")
    return brand


def unique_slug(db, base_slug: str, site3: str, sku: str) -> str:
    slug = base_slug[:280]
    if db.query(Product).filter(Product.slug == slug).first() is None:
        return slug
    slug = f"{base_slug[:270]}-{site3.lower()}"
    if db.query(Product).filter(Product.slug == slug).first() is None:
        return slug
    n = 2
    while True:
        candidate = f"{base_slug[:270]}-{site3.lower()}-{n}"
        if db.query(Product).filter(Product.slug == candidate).first() is None:
            return candidate
        n += 1


def upsert_product(db, item: dict, report: dict) -> None:
    identity = slugify(item["name"])  # lowercase brand + model tokens
    sku = deterministic_sku(item["site"], identity)

    existing = db.query(Product).filter(Product.sku == sku).first()
    brand = get_or_create_brand(db, item["brand"])
    category = db.query(Category).filter(
        Category.slug == item["cat_slug"]).first()
    if category is None:
        print(f"    [cat] missing category {item['cat_slug']}, skipping "
              f"'{item['name'][:50]}'")
        report["errors"] += 1
        return

    if existing:
        changed = False
        if abs(existing.price - item["price"]) > 0.01:
            existing.price = item["price"]
            changed = True
        if item.get("compare_price") and \
                (not existing.compare_at_price or
                 abs((existing.compare_at_price or 0) - item["compare_price"]) > 0.01):
            existing.compare_at_price = item["compare_price"]
            changed = True
        existing_spec_keys = {s.spec_key for s in existing.specifications}
        for k, v in item["specs"].items():
            if k not in existing_spec_keys:
                db.add(ProductSpecification(
                    product_id=existing.id, spec_key=k,
                    value=v[:500],
                    numeric_value=float(v) if re.fullmatch(r"\d+(\.\d+)?", v) else None,
                ))
                changed = True
        if item.get("image") and not existing.images:
            db.add(ProductImage(
                product_id=existing.id, url=item["image"][:500],
                alt_text=item["name"][:255], is_primary=True, sort_order=0,
            ))
            changed = True
        if changed:
            report["updated"] += 1
        else:
            report["skipped"] += 1
        db.commit()
        return

    # insert new product
    slug = unique_slug(db, slugify(item["name"]), SITE3[item["site"]], sku)
    product = Product(
        name=item["name"][:255],
        slug=slug,
        sku=sku,
        description=generate_description(item["name"], item["specs"]),
        brand_id=brand.id,
        category_id=category.id,
        price=item["price"],
        compare_at_price=item.get("compare_price"),
        stock_quantity=STOCK_DEFAULT,
        is_active=True,
        meta_title=item["name"][:255],
        meta_description=f"Buy {item['name']} in Bangladesh."[:500],
    )
    db.add(product)
    db.flush()

    for k, v in item["specs"].items():
        db.add(ProductSpecification(
            product_id=product.id, spec_key=k, value=v[:500],
            numeric_value=float(v) if re.fullmatch(r"\d+(\.\d+)?", v) else None,
        ))

    if item.get("image"):
        db.add(ProductImage(
            product_id=product.id, url=item["image"][:500],
            alt_text=item["name"][:255], is_primary=True, sort_order=0,
        ))

    db.commit()
    report["inserted"] += 1


# ────────────────────────── main ──────────────────────────

_FETCH_STATE = {"prev": 0}


def run_site(site: str, fetcher: PoliteFetcher, limit_pages: int, deep: bool):
    print(f"\n=== {site} ===")
    report = {"fetched": 0, "parsed": 0, "inserted": 0, "updated": 0,
              "skipped": 0, "errors": 0}
    probe_url, adapter, cat_map = ADAPTERS[site]

    db = SessionLocal()
    try:
        for item in adapter(fetcher, cat_map, limit_pages, deep, report):
            try:
                upsert_product(db, item, report)
            except Exception as exc:
                db.rollback()
                print(f"    [db] error on '{item.get('name', '?')[:50]}': {exc}")
                report["errors"] += 1
    finally:
        db.close()

    report["fetched"] = fetcher.fetched - _FETCH_STATE["prev"]
    _FETCH_STATE["prev"] = fetcher.fetched
    return report


def main():
    parser = argparse.ArgumentParser(description="Scrape BD retailers into catalog")
    parser.add_argument("--site", default="all",
                        choices=["all"] + list(ADAPTERS),
                        help="site to scrape (default: all)")
    parser.add_argument("--limit-pages", type=int, default=2,
                        help="max pages per category (default: 2)")
    parser.add_argument("--deep", action="store_true",
                        help="also fetch product detail pages for specs "
                             "(strictly rate-limited; off by default)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help="min delay between same-host requests (default 1.2s)")
    parser.add_argument("--fresh", action="store_true",
                        help="ignore the on-disk response cache")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    cat_slugs = {c.slug for c in db.query(Category).all()}
    db.close()

    sites = list(ADAPTERS) if args.site == "all" else [args.site]
    fetcher = PoliteFetcher(delay=args.delay, use_cache=not args.fresh)

    results = {}
    for site in sites:
        cat_map = ADAPTERS[site][2]
        missing = set(cat_map.values()) - cat_slugs
        if missing:
            print(f"[{site}] WARNING: unknown DB categories {missing} "
                  f"(those items will be skipped)")
        results[site] = run_site(site, fetcher, args.limit_pages, args.deep)

    print("\n" + "=" * 62)
    print("SUMMARY REPORT")
    print("=" * 62)
    print(f"{'site':<15}{'fetched':>8}{'parsed':>8}{'inserted':>10}"
          f"{'updated':>9}{'skipped':>9}{'errors':>8}")
    for site, r in results.items():
        print(f"{site:<15}{r['fetched']:>8}{r['parsed']:>8}{r['inserted']:>10}"
              f"{r['updated']:>9}{r['skipped']:>9}{r['errors']:>8}")


if __name__ == "__main__":
    main()
