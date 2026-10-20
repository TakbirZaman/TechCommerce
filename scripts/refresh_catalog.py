"""Capture a reproducible retailer catalog snapshot with locally verified photos.

Run manually to refresh; normal database seeding never requires network access.
"""
import argparse
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image
from scripts.scrape_bd import PoliteFetcher, STARTECH_CATEGORIES, scrape_startech

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data" / "catalog.json"
PHOTO_DIR = ROOT / "uploads" / "products" / "catalog"


def refresh(per_category=6):
    fetcher = PoliteFetcher(use_cache=False)
    categories = dict(STARTECH_CATEGORIES)
    categories.pop("headset", None)
    categories["accessories/headphone"] = "headsets"
    categories["hub-and-dock"] = "accessories"
    records = []
    seen = set()
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    for path, category in categories.items():
        if category in seen:
            continue
        stats = {"parsed": 0, "errors": 0}
        count = 0
        for item in scrape_startech(fetcher, {path: category}, 1, False, stats):
            if not item.get("image") or not item.get("specs"):
                continue
            # Request the same model's larger OpenCart thumbnail, never search by category.
            original = item["image"]
            url = re.sub(r"-\d+x\d+(\.[a-zA-Z]+)$", r"-500x500\1", original)
            key = hashlib.sha256(item["url"].encode()).hexdigest()[:20]
            target = PHOTO_DIR / f"{key}.webp"
            try:
                if target.exists():
                    photo = Image.open(target)
                    photo.load()
                else:
                    response = fetcher.get(url)
                    if response is None or response.status_code != 200:
                        continue
                    photo = Image.open(io.BytesIO(response.content))
                    photo.load()
                    if min(photo.size) < 300:
                        continue
                    photo = photo.convert("RGB")
                    photo.thumbnail((800, 800))
                    photo.save(target, "WEBP", quality=90, method=6)
            except (OSError, ValueError):
                continue
            item["source_image"] = original
            item["image"] = "/" + str(target.relative_to(ROOT))
            item["image_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            item["observed_at"] = datetime.now(timezone.utc).isoformat()
            records.append(item)
            count += 1
            if count >= per_category:
                break
        if count:
            seen.add(category)
        print(f"{category}: {count} verified product photos", flush=True)
    missing = set(categories.values()) - seen
    if missing:
        raise RuntimeError(f"Incomplete capture; previous snapshot preserved. Missing: {missing}")
    payload = {"schema_version": 1, "currency": "BDT", "source": "Star Tech", "products": records}
    temp = SNAPSHOT.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    temp.replace(SNAPSHOT)
    fetcher.client.close()
    print(f"Saved {len(records)} source-linked records to {SNAPSHOT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-category", type=int, default=6)
    args = parser.parse_args()
    if not 1 <= args.per_category <= 24:
        parser.error("--per-category must be between 1 and 24")
    refresh(args.per_category)
