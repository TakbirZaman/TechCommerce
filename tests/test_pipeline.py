from ml.data.schemas import Category, UseCase, UserRequirement
from ml.inference.explain import generate_explanation
from ml.inference.pipeline import recommend
from ml.inference.rule_based import score_product
from tests.fixtures import SAMPLE_LAPTOPS


def test_reasons_reference_actual_spec_values():
    req = UserRequirement(category=Category.LAPTOP, budget_max=100000, use_cases=[UseCase.GAMING])
    product = next(p for p in SAMPLE_LAPTOPS if p.product_id == "lap-1")
    candidate = score_product(product, req)
    reasons, tradeoffs = generate_explanation(candidate, req)
    combined = " ".join(reasons)
    # the actual raw spec strings should be traceable in the explanation
    assert "RTX 4060" in combined or "95,000" in combined or "i7" in combined


def test_budget_fit_reason_present_when_within_budget():
    req = UserRequirement(category=Category.LAPTOP, budget_max=100000)
    product = next(p for p in SAMPLE_LAPTOPS if p.product_id == "lap-1")
    candidate = score_product(product, req)
    reasons, _ = generate_explanation(candidate, req)
    assert any("budget" in r.lower() for r in reasons)


def test_explanation_never_exceeds_max_items():
    req = UserRequirement(category=Category.LAPTOP, use_cases=[UseCase.PROGRAMMING])
    product = next(p for p in SAMPLE_LAPTOPS if p.product_id == "lap-4")
    candidate = score_product(product, req)
    reasons, tradeoffs = generate_explanation(candidate, req)
    assert len(reasons) <= 4
    assert len(tradeoffs) <= 3


def test_pipeline_end_to_end_produces_ranked_recommendations():
    req = UserRequirement(
        category=Category.LAPTOP,
        budget_max=100000,
        use_cases=[UseCase.PROGRAMMING, UseCase.MACHINE_LEARNING, UseCase.GAMING],
    )
    response = recommend(SAMPLE_LAPTOPS, req, top_n=5)
    assert response.candidates_considered == len(SAMPLE_LAPTOPS)
    assert response.candidates_after_filtering < len(SAMPLE_LAPTOPS)  # budget/stock filtered some out
    assert len(response.recommendations) > 0
    assert response.recommendations[0].score >= response.recommendations[-1].score
    for rec in response.recommendations:
        assert rec.reasons  # every recommendation must be explained


def test_pipeline_returns_empty_list_when_nothing_matches():
    req = UserRequirement(category=Category.LAPTOP, budget_max=1000)
    response = recommend(SAMPLE_LAPTOPS, req)
    assert response.recommendations == []
    assert response.candidates_after_filtering == 0
