"""Install the checked-in catalog snapshot without network or invented stock."""
import hashlib
import json
from pathlib import Path

from core.models.catalog import Brand, Category
from core.models.specification import Product, ProductImage, ProductSpecification
from scripts.scrape_bd import deterministic_sku, slugify

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data" / "catalog.json"


def load_snapshot(path=SNAPSHOT):
    data = json.loads(Path(path).read_text())
    if data.get("currency") != "BDT" or data.get("schema_version") != 1:
        raise ValueError("Unsupported catalog snapshot")
    seen = set()
    for item in data["products"]:
        if item["url"] in seen or not item["url"].startswith("https://www.startech.com.bd/"):
            raise ValueError("Duplicate or invalid product source")
        seen.add(item["url"])
        if item["price"] <= 0 or not item["specs"] or not item["observed_at"]:
            raise ValueError("Incomplete product record")
        image = item["image"]
        if not image.startswith("/uploads/products/catalog/") or ".." in image:
            raise ValueError("Invalid product photo path")
        photo = ROOT / image.lstrip("/")
        if hashlib.sha256(photo.read_bytes()).hexdigest() != item["image_sha256"]:
            raise ValueError(f"Photo integrity failure: {photo}")
    if not data["products"]:
        raise ValueError("Empty catalog snapshot")
    return data["products"]


def seed_real_catalog(db):
    # Validate every record and asset before making database changes.
    records = load_snapshot()
    cats = {c.slug: c for c in db.query(Category).all()}
    if set(r["cat_slug"] for r in records) - set(cats):
        raise ValueError("Seed categories before installing the catalog")
    brands = {b.slug: b for b in db.query(Brand).all()}
    legacy_skus = set(json.loads((ROOT / "data/legacy_demo_skus.json").read_text()))
    for product in db.query(Product).all():
        # Retire only recognizable seeded placeholders. Keep rows, order history,
        # and any products whose photos have already been replaced by an operator.
        demo_identity = product.sku.startswith("TC-") or product.sku in legacy_skus
        placeholder_only = not product.images or all(
            im.url.startswith("/uploads/products/cat-") and im.url.endswith(".svg")
            for im in product.images
        )
        if demo_identity and placeholder_only:
            product.is_active = False
            product.is_featured = False
    for index, item in enumerate(records):
        brand_slug = slugify(item["brand"])
        if brand_slug not in brands:
            brand = Brand(name=item["brand"], slug=brand_slug, is_active=True)
            db.add(brand)
            db.flush()
            brands[brand_slug] = brand
        sku = deterministic_sku("startech", slugify(item["name"]))
        product = db.query(Product).filter(Product.sku == sku).first()
        if product is None:
            slug = slugify(item["name"])
            if db.query(Product.id).filter(Product.slug == slug).first():
                slug = f"{slug[:250]}-sourced-{hashlib.sha256(item['url'].encode()).hexdigest()[:8]}"
            product = Product(
                name=item["name"], slug=slug, sku=sku,
                brand_id=brands[brand_slug].id, category_id=cats[item["cat_slug"]].id,
                price=item["price"], compare_at_price=item.get("compare_price"),
                # A retailer listing does not establish our own warehouse stock.
                stock_quantity=0, is_active=True, is_featured=index % 6 == 0,
                description=f"{item['name']}. " + "; ".join(
                    f"{k.replace('_', ' ')}: {v}" for k, v in item["specs"].items()
                ) + f". Reference price in BDT observed {item['observed_at'][:10]}; inventory is managed separately.",
            )
            db.add(product)
            db.flush()
            for key, value in item["specs"].items():
                db.add(ProductSpecification(product_id=product.id, spec_key=key, value=value))
        # Preserve operator prices, stock, descriptions, status, and uploaded galleries.
        if not product.images or all(im.url.startswith("/uploads/products/cat-") for im in product.images):
            for old in list(product.images):
                db.delete(old)
            db.add(ProductImage(product_id=product.id, url=item["image"],
                                alt_text=item["name"], is_primary=True, sort_order=0))
    db.commit()
    return len(records)
