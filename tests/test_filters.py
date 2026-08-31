from ml.data.schemas import Category, RequiredSpecs, UserRequirement
from ml.inference.filters import filter_candidates
from tests.fixtures import SAMPLE_LAPTOPS


def test_category_filter():
    req = UserRequirement(category=Category.LAPTOP)
    result = filter_candidates(SAMPLE_LAPTOPS, req)
    assert all(p.category == Category.LAPTOP for p in result)


def test_budget_max_excludes_over_budget():
    req = UserRequirement(category=Category.LAPTOP, budget_max=100000)
    result = filter_candidates(SAMPLE_LAPTOPS, req)
    ids = {p.product_id for p in result}
    assert "lap-4" not in ids  # 140,000 — over budget
    assert "lap-1" in ids  # 95,000 — within budget


def test_budget_min_excludes_under_budget():
    req = UserRequirement(category=Category.LAPTOP, budget_min=80000)
    result = filter_candidates(SAMPLE_LAPTOPS, req)
    ids = {p.product_id for p in result}
    assert "lap-3" not in ids  # 55,000
    assert "lap-2" not in ids  # 78,000


def test_out_of_stock_excluded_by_default():
    req = UserRequirement(category=Category.LAPTOP)
    result = filter_candidates(SAMPLE_LAPTOPS, req)
    ids = {p.product_id for p in result}
    assert "lap-5" not in ids


def test_in_stock_only_false_includes_out_of_stock():
    req = UserRequirement(category=Category.LAPTOP, required_specs=RequiredSpecs(in_stock_only=False))
    result = filter_candidates(SAMPLE_LAPTOPS, req)
    ids = {p.product_id for p in result}
    assert "lap-5" in ids


def test_required_ram_excludes_insufficient():
    req = UserRequirement(category=Category.LAPTOP, required_specs=RequiredSpecs(min_ram_gb=16))
    result = filter_candidates(SAMPLE_LAPTOPS, req)
    ids = {p.product_id for p in result}
    assert "lap-3" not in ids  # only 8GB


def test_required_brand_filters_strictly():
    req = UserRequirement(category=Category.LAPTOP, required_specs=RequiredSpecs(required_brand="Asus"))
    result = filter_candidates(SAMPLE_LAPTOPS, req)
    assert all(p.brand == "Asus" for p in result)


def test_no_candidates_when_budget_impossible():
    req = UserRequirement(category=Category.LAPTOP, budget_max=1000)
    result = filter_candidates(SAMPLE_LAPTOPS, req)
    assert result == []
