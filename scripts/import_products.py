"""
Import Products from phones.md and laptops.md files.

Run: python -m scripts.import_products
"""
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal, init_db
from core.models.catalog import Brand, Category
from core.models.specification import Product, ProductSpecification


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:280]


def parse_price_clean(price_str: str) -> tuple[float, float | None]:
    """Parse price string and return (price, compare_at_price)."""
    # Remove BOM and clean
    price_str = price_str.replace('\ufeff', '').replace('৳', '').replace(',', '').strip()
    
    # Handle "To Be Announced" or "TBA"
    if 'to be announced' in price_str.lower() or price_str.lower() == 'tba':
        return 0.0, None
    
    # Remove markdown bold markers
    price_str = price_str.replace('**', '')
    
    # Extract main price (first number)
    price_match = re.match(r'^\s*(\d+(?:\.\d+)?)', price_str)
    if not price_match:
        return 0.0, None
    
    price = float(price_match.group(1))
    
    # Check for compare_at_price (strikethrough with ~~)
    compare_match = re.search(r'~~\s*(\d+(?:\.\d+)?)\s*~~', price_str)
    compare_at = float(compare_match.group(1)) if compare_match else None
    
    return price, compare_at


def parse_phones(file_path: str) -> list[dict]:
    """Parse phones.md file and extract products."""
    products = []
    current_brand = None
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # Split by lines
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect brand headers (## Brand)
        if line.startswith('## ') and not line.startswith('### '):
            brand_match = re.match(r'^##\s+(.+)', line)
            if brand_match:
                brand_name = brand_match.group(1).strip()
                # Skip non-brand headers
                if brand_name not in ['Not yet pulled', 'Extra models (from homepage featured section)']:
                    current_brand = brand_name
            i += 1
            continue
        
        # Detect product entries (### N. Product Name)
        product_match = re.match(r'^###\s+\d+\.\s+(.+)', line)
        if product_match and current_brand:
            product_name = product_match.group(1).strip()
            
            # Look ahead for price and specs
            price = 0.0
            compare_at_price = None
            specs = {}
            description = ""
            image_url = None
            link = None
            
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                
                # Stop at next product or brand
                if next_line.startswith('### ') or next_line.startswith('## '):
                    break
                
                # Extract price
                if next_line.startswith('- Price:') or next_line.startswith('- **Price**:'):
                    price_str = next_line.replace('- Price:', '').replace('- **Price**:', '').strip()
                    price, compare_at_price = parse_price_clean(price_str)
                
                # Extract image
                elif next_line.startswith('![img]'):
                    img_match = re.search(r'!\[img\]\((.+?)\)', next_line)
                    if img_match:
                        image_url = img_match.group(1)
                
                # Extract specs (lines starting with - and containing : )
                elif next_line.startswith('-') and ':' in next_line:
                    spec_match = re.match(r'^-\s+(.+?):\s+(.+)', next_line)
                    if spec_match:
                        spec_key = spec_match.group(1).strip()
                        spec_value = spec_match.group(2).strip()
                        # Skip link lines
                        if spec_key != 'Link':
                            specs[spec_key] = spec_value
                            description += f"{spec_key}: {spec_value}. "
                
                # Extract link
                elif next_line.startswith('- Link:'):
                    link = next_line.replace('- Link:', '').strip()
                
                j += 1
            
            # Clean product name (remove markdown formatting)
            product_name = re.sub(r'\*\*(.+?)\*\*', r'\1', product_name)
            
            if price > 0:  # Only add products with prices
                products.append({
                    'name': product_name,
                    'brand': current_brand,
                    'price': price,
                    'compare_at_price': compare_at_price,
                    'description': description.strip() or f"{product_name} from {current_brand}",
                    'specs': specs,
                    'image_url': image_url,
                    'link': link,
                    'category': 'phones'
                })
            
            i = j
            continue
        
        i += 1
    
    return products


def parse_laptops(file_path: str) -> list[dict]:
    """Parse laptops.md file and extract products."""
    products = []
    current_brand = None
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # Split by lines
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect brand headers (## Brand Laptops)
        if line.startswith('## '):
            # Extract brand from headers like "## Dell Laptops", "## MSI Laptops"
            brand_match = re.match(r'^##\s+(\w+)\s+Laptop', line)
            if brand_match:
                current_brand = brand_match.group(1).strip()
            else:
                # Check for other brand headers
                for brand in ['Lenovo', 'HP', 'MSI', 'Dell', 'Asus', 'Acer', 'Apple', 'MacBook']:
                    if brand.lower() in line.lower():
                        current_brand = brand
                        break
            i += 1
            continue
        
        # Detect product entries (### N. Product Name)
        product_match = re.match(r'^###\s+\d+\.\s+(.+)', line)
        if product_match:
            product_name = product_match.group(1).strip()
            
            # Try to extract brand from product name if not set
            if not current_brand:
                brand_keywords = ['Lenovo', 'HP', 'MSI', 'Dell', 'Asus', 'Acer', 'Apple', 'MacBook', 'Chuwi']
                for kw in brand_keywords:
                    if kw.lower() in product_name.lower():
                        current_brand = kw
                        break
            
            # Look ahead for price and specs
            price = 0.0
            compare_at_price = None
            specs = {}
            description = ""
            image_url = None
            link = None
            
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                
                # Stop at next product or brand
                if next_line.startswith('### ') or next_line.startswith('## '):
                    break
                
                # Extract price
                if next_line.startswith('- Price:') or next_line.startswith('- **Price**:'):
                    price_str = next_line.replace('- Price:', '').replace('- **Price**:', '').strip()
                    price, compare_at_price = parse_price_clean(price_str)
                
                # Extract image
                elif next_line.startswith('![img]'):
                    img_match = re.search(r'!\[img\]\((.+?)\)', next_line)
                    if img_match:
                        image_url = img_match.group(1)
                
                # Extract specs (lines starting with - and containing : )
                elif next_line.startswith('-') and ':' in next_line:
                    spec_match = re.match(r'^-\s+(.+?):\s+(.+)', next_line)
                    if spec_match:
                        spec_key = spec_match.group(1).strip()
                        spec_value = spec_match.group(2).strip()
                        # Skip link lines
                        if spec_key != 'Link':
                            specs[spec_key] = spec_value
                            description += f"{spec_key}: {spec_value}. "
                
                # Extract link
                elif next_line.startswith('- Link:'):
                    link = next_line.replace('- Link:', '').strip()
                
                j += 1
            
            # Clean product name (remove markdown formatting)
            product_name = re.sub(r'\*\*(.+?)\*\*', r'\1', product_name)
            
            if price > 0:  # Only add products with prices
                products.append({
                    'name': product_name,
                    'brand': current_brand or 'Unknown',
                    'price': price,
                    'compare_at_price': compare_at_price,
                    'description': description.strip() or f"{product_name}",
                    'specs': specs,
                    'image_url': image_url,
                    'link': link,
                    'category': 'laptops'
                })
            
            i = j
            continue
        
        i += 1
    
    return products


def import_products():
    """Main function to import all products."""
    init_db()
    db = SessionLocal()
    
    try:
        # Get or create brands
        brands = {}
        existing_brands = db.query(Brand).all()
        for b in existing_brands:
            brands[b.name.lower()] = b
        
        # Get categories
        cats = {}
        existing_cats = db.query(Category).all()
        for c in existing_cats:
            cats[c.slug] = c
        
        # Parse phones
        phones_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'phones.md')
        if os.path.exists(phones_file):
            phones = parse_phones(phones_file)
            print(f"[OK] Parsed {len(phones)} phones from phones.md")
        else:
            phones = []
            print("[--] phones.md not found")
        
        # Parse laptops
        laptops_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'laptops .md')
        if os.path.exists(laptops_file):
            laptops = parse_laptops(laptops_file)
            print(f"[OK] Parsed {len(laptops)} laptops from laptops.md")
        else:
            laptops = []
            print("[--] laptops.md not found")
        
        all_products = phones + laptops
        
        # Import products
        created = 0
        skipped = 0
        
        for p in all_products:
            # Skip products with price 0 (TBA)
            if p['price'] == 0:
                skipped += 1
                continue
            
            # Generate slug
            slug = slugify(p['name'])
            
            # Check if product already exists
            existing = db.query(Product).filter(Product.slug == slug).first()
            if existing:
                skipped += 1
                continue
            
            # Get or create brand
            brand_name = p['brand']
            brand = brands.get(brand_name.lower())
            if not brand:
                brand = Brand(
                    name=brand_name,
                    slug=slugify(brand_name),
                    is_active=True
                )
                db.add(brand)
                db.flush()
                brands[brand_name.lower()] = brand
            
            # Get category
            cat_slug = p['category']
            cat = cats.get(cat_slug)
            if not cat:
                print(f"[WARN] Category '{cat_slug}' not found, skipping {p['name']}")
                skipped += 1
                continue
            
            # Generate unique SKU
            base_sku = f"{brand.name[:3].upper()}-{slug[:20].upper()}"
            sku = base_sku
            counter = 1
            while db.query(Product).filter(Product.sku == sku).first():
                sku = f"{base_sku[:18]}-{counter:02d}"
                counter += 1
            
            # Create product
            product = Product(
                name=p['name'],
                slug=slug,
                sku=sku,
                description=p['description'],
                price=p['price'],
                compare_at_price=p.get('compare_at_price'),
                stock_quantity=10,  # Default stock
                brand_id=brand.id,
                category_id=cat.id,
                is_active=True,
            )
            db.add(product)
            db.flush()
            
            # Add specifications
            for key, value in p.get('specs', {}).items():
                spec = ProductSpecification(
                    product_id=product.id,
                    spec_key=slugify(key),
                    value=str(value),
                )
                db.add(spec)
            
            created += 1
        
        db.commit()
        print(f"\n[DONE] Import complete!")
        print(f"  - Created: {created} products")
        print(f"  - Skipped: {skipped} products (existing or TBA)")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import_products()
