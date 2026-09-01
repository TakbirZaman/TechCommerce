"""
Dynamic filter derivation (Section 6).

Filters are NOT hard-coded per category in Python. Instead each Category
row carries `filterable_spec_schema`, a small JSON schema describing which
specification keys are filterable and how (enum vs numeric range vs
boolean), e.g.:

    {
      "cpu":            {"label": "CPU",          "type": "enum"},
      "gpu":             {"label": "GPU",          "type": "enum"},
      "ram_gb":          {"label": "RAM",          "type": "enum", "unit": "GB"},
      "storage_gb":      {"label": "Storage",      "type": "enum", "unit": "GB"},
      "display_size_in": {"label": "Display size", "type": "range", "unit": "in"},
      "refresh_rate_hz": {"label": "Refresh rate", "type": "enum", "unit": "Hz"},
      "has_5g":          {"label": "5G",           "type": "boolean"}
    }

Admins configure this per category (Section 31 — "manage category
metadata"), so adding a new product type's filters is a data change, not
a code change. Common filters (price/brand/availability/status) are
always added on top, independent of category.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.stubs import Brand, Category, Product, ProductStatus
from app.schemas.filters import FilterDefinition, FilterOption


def build_common_filters(db: Session, base_query) -> list[FilterDefinition]:
    """Filters that apply regardless of category: price, brand, availability, status."""
    filters: list[FilterDefinition] = []

    price_bounds = base_query.with_entities(
        func.min(Product.price), func.max(Product.price)
    ).one()
    filters.append(
        FilterDefinition(
            key="price",
            label="Price",
            type="range",
            min=price_bounds[0],
            max=price_bounds[1],
        )
    )

    brand_counts = (
        base_query.with_entities(Brand.id, Brand.name, func.count(Product.id))
        .join(Brand, Product.brand_id == Brand.id)
        .group_by(Brand.id, Brand.name)
        .all()
    )
    filters.append(
        FilterDefinition(
            key="brand_id",
            label="Brand",
            type="enum",
            options=[
                FilterOption(value=bid, label=name, count=count)
                for bid, name, count in brand_counts
            ],
        )
    )

    status_counts = (
        base_query.with_entities(Product.status, func.count(Product.id))
        .group_by(Product.status)
        .all()
    )
    filters.append(
        FilterDefinition(
            key="status",
            label="Availability",
            type="enum",
            options=[
                FilterOption(value=status.value, label=status.value.replace("_", " ").title(), count=count)
                for status, count in status_counts
            ],
        )
    )

    return filters


def build_spec_filters(db: Session, category: Category, base_query) -> list[FilterDefinition]:
    """
    Derives spec-based filters (Section 6: CPU/GPU/RAM for laptops, chipset/
    battery for phones, panel/response time for monitors, etc.) from the
    category's `filterable_spec_schema` plus the actual distinct values
    present among matching products — so options never show 0-result choices
    that no product actually has.
    """
    schema = category.filterable_spec_schema or {}
    products = base_query.all()

    definitions: list[FilterDefinition] = []
    for spec_key, meta in schema.items():
        spec_type = meta.get("type", "enum")
        label = meta.get("label", spec_key.replace("_", " ").title())
        unit = meta.get("unit")

        values = [p.specifications.get(spec_key) for p in products if p.specifications.get(spec_key) is not None]

        if spec_type == "range" and values:
            definitions.append(
                FilterDefinition(key=spec_key, label=label, type="range", unit=unit, min=min(values), max=max(values))
            )
        elif spec_type == "boolean":
            true_count = sum(1 for v in values if v is True)
            false_count = sum(1 for v in values if v is False)
            definitions.append(
                FilterDefinition(
                    key=spec_key,
                    label=label,
                    type="boolean",
                    options=[
                        FilterOption(value=True, label="Yes", count=true_count),
                        FilterOption(value=False, label="No", count=false_count),
                    ],
                )
            )
        else:  # enum
            from collections import Counter

            counts = Counter(values)
            definitions.append(
                FilterDefinition(
                    key=spec_key,
                    label=label,
                    type="enum",
                    unit=unit,
                    options=[
                        FilterOption(value=val, label=str(val), count=cnt)
                        for val, cnt in sorted(counts.items(), key=lambda kv: -kv[1])
                    ],
                )
            )
    return definitions


def apply_filters_to_query(query, filters: dict):
    """
    Applies a parsed filter dict (from query params, see api/v1/search.py)
    onto a Product query. Common filters use real columns; anything else
    is assumed to be a specification key and filtered via the JSON column.
    """
    if "min_price" in filters:
        query = query.filter(Product.price >= filters["min_price"])
    if "max_price" in filters:
        query = query.filter(Product.price <= filters["max_price"])
    if "brand" in filters:
        query = query.join(Brand, Product.brand_id == Brand.id).filter(Brand.slug.in_(filters["brand"]))
    if "status" in filters:
        query = query.filter(Product.status.in_([ProductStatus(s) for s in filters["status"]]))

    reserved = {"min_price", "max_price", "brand", "status", "q", "sort", "page", "page_size", "category"}
    for key, value in filters.items():
        if key in reserved:
            continue
        # Spec filter — supports either exact match or "min,max" range syntax.
        if isinstance(value, str) and "," in value:
            lo, hi = value.split(",", 1)
            query = query.filter(
                func.cast(Product.specifications[key].astext, func.numeric()) >= float(lo),
                func.cast(Product.specifications[key].astext, func.numeric()) <= float(hi),
            )
        else:
            query = query.filter(Product.specifications[key].astext == str(value))
    return query
