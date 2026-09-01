"""
Comparison compatibility + row-building logic (Sections 9-11).
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.stubs import Product
from app.schemas.comparison import ComparisonProductColumn, ComparisonResponse, ComparisonRow
from app.schemas.product import BrandBrief, CategoryBrief

MIN_COMPARE = 2
MAX_COMPARE = 4


def validate_comparable(products: list[Product]) -> None:
    """
    Comparison rule (Section 10): all products must belong to the same
    category. This is deliberately simple and explicit rather than a
    fuzzy "compatible category group" — laptop vs laptop, phone vs phone,
    GPU vs GPU, monitor vs monitor are literally the same `category_id`
    in this schema (subcategories, if needed, should still roll up to a
    shared comparable root — see Category.parent_id).
    """
    if len(products) < MIN_COMPARE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "At least 2 products are required to compare.")
    if len(products) > MAX_COMPARE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"At most {MAX_COMPARE} products can be compared at once.")

    category_ids = {p.category_id for p in products}
    if len(category_ids) > 1:
        names = ", ".join(sorted({p.category.name for p in products}))
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot compare products from different categories: {names}. "
            "Comparison is only supported within the same product type.",
        )


def build_comparison(products: list[Product]) -> ComparisonResponse:
    validate_comparable(products)
    category = products[0].category

    columns = [
        ComparisonProductColumn(
            id=p.id,
            name=p.name,
            slug=p.slug,
            price=p.price,
            status=p.status.value if hasattr(p.status, "value") else p.status,
            brand=BrandBrief.model_validate(p.brand),
        )
        for p in products
    ]

    # Union of all spec keys across the compared products, in a stable order
    # (first-seen order), driven purely by data — no per-category hard-coding.
    all_keys: list[str] = []
    seen = set()
    for p in products:
        for key in (p.specifications or {}).keys():
            if key not in seen:
                seen.add(key)
                all_keys.append(key)

    rows: list[ComparisonRow] = []
    for key in all_keys:
        values = [str((p.specifications or {}).get(key, "—")) for p in products]
        rows.append(
            ComparisonRow(
                spec_key=key,
                spec_label=key.replace("_", " ").title(),
                values=values,
                differs=len(set(values)) > 1,
            )
        )

    return ComparisonResponse(
        category=CategoryBrief.model_validate(category),
        products=columns,
        rows=rows,
    )
