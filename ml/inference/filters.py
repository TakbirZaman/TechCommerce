"""
Hard filtering (spec section 11 / 23).

Runs before any scoring. A product that violates a hard requirement is
removed outright — it must never appear in the ranked output, regardless of
how well it might otherwise score. This keeps the recommendation engine from
ever "explaining away" an incompatible product.

Order matches spec section 23's candidate-generation pipeline: category ->
budget -> availability -> specification filters.
"""

from __future__ import annotations

from ml.data.schemas import Product, UserRequirement
from ml.preprocessing import normalization as norm


def filter_candidates(products: list[Product], requirement: UserRequirement) -> list[Product]:
    candidates = [p for p in products if p.category == requirement.category]
    candidates = _filter_budget(candidates, requirement)
    candidates = _filter_availability(candidates, requirement)
    candidates = _filter_required_specs(candidates, requirement)
    candidates = _filter_brand(candidates, requirement)
    return candidates


def _filter_budget(products: list[Product], requirement: UserRequirement) -> list[Product]:
    out = products
    if requirement.budget_max is not None:
        out = [p for p in out if p.price <= requirement.budget_max]
    if requirement.budget_min is not None:
        out = [p for p in out if p.price >= requirement.budget_min]
    return out


def _filter_availability(products: list[Product], requirement: UserRequirement) -> list[Product]:
    if not requirement.required_specs.in_stock_only:
        return products
    return [p for p in products if p.in_stock]


def _filter_required_specs(products: list[Product], requirement: UserRequirement) -> list[Product]:
    specs = requirement.required_specs
    out = []
    for p in products:
        if specs.min_ram_gb is not None:
            ram = norm.normalize_ram_gb(p.raw_specs.get("ram") or p.raw_specs.get("memory"))
            if ram is None or ram < specs.min_ram_gb:
                continue
        if specs.min_storage_gb is not None:
            storage = norm.normalize_storage_gb(p.raw_specs.get("storage") or p.raw_specs.get("ssd"))
            if storage is None or storage < specs.min_storage_gb:
                continue
        if specs.min_battery_mah is not None:
            battery = norm.normalize_battery_mah(p.raw_specs.get("battery") or p.raw_specs.get("battery_capacity"))
            if battery is None or battery < specs.min_battery_mah:
                continue
        if specs.max_weight_kg is not None:
            weight = norm.normalize_weight_kg(p.raw_specs.get("weight"))
            if weight is None or weight > specs.max_weight_kg:
                continue
        if specs.required_brand and p.brand.lower() != specs.required_brand.lower():
            continue
        out.append(p)
    return out


def _filter_brand(products: list[Product], requirement: UserRequirement) -> list[Product]:
    # preferred_brands is a soft signal (used later for ranking/explanation),
    # never a hard filter — do not exclude here.
    return products
