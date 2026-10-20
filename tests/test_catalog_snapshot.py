"""Catalog provenance, photo integrity, and non-destructive seed integration."""
import os
import sqlite3
import subprocess
import sys
from PIL import Image
from scripts.seed_real_catalog import ROOT, load_snapshot


def test_snapshot_has_real_photos_in_every_category():
    records = load_snapshot()
    expected = {"laptops", "phones", "tablets", "monitors", "processors",
                "graphics-cards", "ram", "storage", "motherboards", "power-supplies",
                "cases", "keyboards", "mice", "headsets", "accessories"}
    assert {r["cat_slug"] for r in records} == expected
    assert len({r["image"] for r in records}) == len(records)
    for row in records:
        with Image.open(ROOT / row["image"].lstrip("/")) as photo:
            photo.verify()
        with Image.open(ROOT / row["image"].lstrip("/")) as photo:
            assert min(photo.size) >= 300
        assert row["source_image"].startswith("https://www.startech.com.bd/")
        assert row["compare_price"] is None or row["compare_price"] >= row["price"]


def test_seed_is_repeatable_and_preserves_operator_data(tmp_path):
    db_path = tmp_path / "catalog.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}"}
    def seed():
        subprocess.run([sys.executable, "scripts/seed.py"], cwd=ROOT, env=env,
                       check=True, capture_output=True, text=True)
    seed()
    with sqlite3.connect(db_path) as db:
        count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        assert count == len(load_snapshot())
        product_id = db.execute("SELECT id FROM products LIMIT 1").fetchone()[0]
        db.execute("UPDATE products SET price=12345, stock_quantity=7 WHERE id=?", (product_id,))
        db.execute("""INSERT INTO products
            (name,slug,sku,brand_id,category_id,price,stock_quantity,reserved_stock,
             is_active,is_featured,popularity_score,view_count)
            SELECT 'Shop special','shop-special','SHOP-001',brand_id,category_id,
                1000,3,0,1,0,0,0 FROM products LIMIT 1""")
        db.execute("""INSERT INTO products
            (name,slug,sku,brand_id,category_id,price,stock_quantity,reserved_stock,
             is_active,is_featured,popularity_score,view_count)
            SELECT 'Legacy demo','legacy-demo','TC-TST-DMO-99999',brand_id,category_id,
                1000,3,0,1,0,0,0 FROM products LIMIT 1""")
    seed()
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == count + 2
        assert db.execute("SELECT price,stock_quantity FROM products WHERE id=?", (product_id,)).fetchone() == (12345,7)
        assert db.execute("SELECT is_active FROM products WHERE sku='SHOP-001'").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM product_images").fetchone()[0] == count
        assert db.execute("SELECT COUNT(*) FROM product_reviews").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
        assert db.execute("SELECT is_active FROM products WHERE sku='TC-TST-DMO-99999'").fetchone()[0] == 0
