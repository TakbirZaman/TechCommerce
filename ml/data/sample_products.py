"""
Sample laptop catalog used by tests and by the API's placeholder
InMemoryProductRepository (api/dependencies.py) so the system is runnable
end-to-end without a live Postgres connection. This is demo data, not a
claim about any real product's specs or pricing.
"""

from ml.data.schemas import Category, Product

SAMPLE_LAPTOPS: list[Product] = [
    Product(
        product_id="lap-1",
        name="ProBook Gaming X",
        brand="Asus",
        category=Category.LAPTOP,
        price=95000,
        in_stock=True,
        rating=4.5,
        review_count=120,
        raw_specs={
            "cpu": "Intel Core i7-13700H",
            "gpu": "RTX 4060",
            "ram": "16GB",
            "storage": "1TB",
            "display_size": "15.6\"",
            "refresh_rate": "144Hz",
            "battery": "70Wh",
            "weight": "2.3kg",
        },
    ),
    Product(
        product_id="lap-2",
        name="UltraLight Slim 14",
        brand="Lenovo",
        category=Category.LAPTOP,
        price=78000,
        in_stock=True,
        rating=4.2,
        review_count=80,
        raw_specs={
            "cpu": "Intel Core i5-1240P",
            "gpu": "Iris Xe integrated",
            "ram": "16GB",
            "storage": "512GB",
            "display_size": "14 inch",
            "battery": "60Wh",
            "weight": "1.2kg",
        },
    ),
    Product(
        product_id="lap-3",
        name="BudgetBook 15",
        brand="HP",
        category=Category.LAPTOP,
        price=55000,
        in_stock=True,
        rating=3.8,
        review_count=45,
        raw_specs={
            "cpu": "Intel Core i3-1215U",
            "ram": "8GB",
            "storage": "256GB",
            "display_size": "15.6\"",
            "weight": "1.8kg",
        },
    ),
    Product(
        product_id="lap-4",
        name="StudioWorks 16 ML Edition",
        brand="Dell",
        category=Category.LAPTOP,
        price=140000,
        in_stock=True,
        rating=4.7,
        review_count=30,
        raw_specs={
            "cpu": "Intel Core i9-13900H",
            "gpu": "RTX 4070",
            "ram": "32GB",
            "storage": "1TB",
            "display_size": "16 inch",
            "battery": "80Wh",
            "weight": "2.1kg",
        },
    ),
    Product(
        product_id="lap-5",
        name="OutOfStock Elite",
        brand="Asus",
        category=Category.LAPTOP,
        price=90000,
        in_stock=False,
        rating=4.6,
        review_count=15,
        raw_specs={
            "cpu": "Ryzen 9 7940HS",
            "gpu": "RTX 4060",
            "ram": "32GB",
            "storage": "1TB",
        },
    ),
]
