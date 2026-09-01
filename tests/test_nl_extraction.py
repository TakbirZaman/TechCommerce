from ml.data.schemas import Category, UseCase
from ml.inference.llm_validation import LLMOutputValidationError, validate_llm_output
from ml.inference.nl_extraction import extract_requirement


def test_extract_laptop_programming_ml_gaming_query():
    req, missing = extract_requirement(
        "I need a laptop under 100,000 BDT for programming, machine learning and gaming."
    )
    assert req is not None
    assert req.category == Category.LAPTOP
    assert req.budget_max == 100000
    assert UseCase.PROGRAMMING in req.use_cases
    assert UseCase.MACHINE_LEARNING in req.use_cases
    assert UseCase.GAMING in req.use_cases
    assert missing == []


def test_extract_phone_under_50k_with_camera():
    req, missing = extract_requirement("I need a phone under 50k with a good camera.")
    assert req.category == Category.SMARTPHONE
    assert req.budget_max == 50000
    assert req.priorities.camera is not None
    assert "use_case" in missing  # no explicit use case stated


def test_extract_laptop_programming_under_80k():
    req, missing = extract_requirement("Best laptop for programming under 80,000.")
    assert req.category == Category.LAPTOP
    assert req.budget_max == 80000
    assert UseCase.PROGRAMMING in req.use_cases


def test_extract_gaming_laptop_around_120k():
    req, missing = extract_requirement("I need a gaming laptop around 120k.")
    assert req.category == Category.LAPTOP
    assert req.budget_max == 132000  # 120k * 1.10 soft band
    assert UseCase.GAMING in req.use_cases


def test_extract_missing_category_returns_none_and_flags_it():
    req, missing = extract_requirement("Something under 50k with good battery and camera.")
    assert req is None
    assert missing == ["category"]


def test_extract_missing_budget_is_flagged():
    req, missing = extract_requirement("Best laptop for programming.")
    assert req is not None
    assert "budget" in missing


def test_llm_output_validates_when_well_formed():
    result = validate_llm_output({"category": "smartphone", "budget_max": 60000})
    assert result.category == Category.SMARTPHONE
    assert result.budget_max == 60000


def test_llm_output_rejects_unknown_fields():
    import pytest

    with pytest.raises(LLMOutputValidationError):
        validate_llm_output(
            {"category": "smartphone", "budget_max": 60000, "recommended_product_ids": ["p1", "p2"]}
        )


def test_llm_output_rejects_out_of_range_priority():
    import pytest

    with pytest.raises(LLMOutputValidationError):
        validate_llm_output({"category": "laptop", "priorities": {"camera": 5.0}})
