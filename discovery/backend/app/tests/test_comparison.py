import pytest
from fastapi import HTTPException

from app.services.comparison import build_comparison, validate_comparable


def test_same_category_comparison_succeeds(sample_data):
    result = build_comparison([sample_data["p1"], sample_data["p2"]])
    assert result.category.slug == "laptops"
    assert len(result.products) == 2
    # cpu differs between the two laptops
    cpu_row = next(r for r in result.rows if r.spec_key == "cpu")
    assert cpu_row.differs is True


def test_cross_category_comparison_rejected(sample_data):
    with pytest.raises(HTTPException) as exc:
        validate_comparable([sample_data["p1"], sample_data["p3"]])
    assert exc.value.status_code == 400


def test_single_product_rejected(sample_data):
    with pytest.raises(HTTPException):
        validate_comparable([sample_data["p1"]])


def test_shared_spec_value_does_not_differ(sample_data):
    result = build_comparison([sample_data["p1"], sample_data["p2"]])
    ram_row = next(r for r in result.rows if r.spec_key == "ram_gb")
    assert ram_row.differs is False
