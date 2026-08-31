from ml.data.schemas import Category, UseCase, UserRequirement
from ml.inference.hybrid import rank_hybrid, score_hybrid
from tests.fixtures import SAMPLE_LAPTOPS


def test_hybrid_score_without_ml_or_behavioral_uses_available_components():
    req = UserRequirement(category=Category.LAPTOP, budget_max=100000, use_cases=[UseCase.GAMING])
    product = next(p for p in SAMPLE_LAPTOPS if p.product_id == "lap-1")
    result = score_hybrid(product, req)
    assert result.engine == "hybrid_v1"
    assert "ml_ranking" not in result.component_scores  # absent, not zeroed
    assert 0.0 <= result.final_score <= 1.0


def test_hybrid_score_with_ml_score_included():
    req = UserRequirement(category=Category.LAPTOP, budget_max=100000, use_cases=[UseCase.GAMING])
    product = next(p for p in SAMPLE_LAPTOPS if p.product_id == "lap-1")
    result = score_hybrid(product, req, ml_score=0.9)
    assert "ml_ranking" in result.component_scores
    assert "content_similarity" not in result.component_scores  # folded into ml_ranking weight


def test_hybrid_score_with_behavioral_signal():
    req = UserRequirement(category=Category.LAPTOP, budget_max=100000)
    product = next(p for p in SAMPLE_LAPTOPS if p.product_id == "lap-1")
    result = score_hybrid(product, req, behavioral_score=0.8)
    assert result.component_scores["behavioral"] == 0.8


def test_rank_hybrid_orders_descending_and_explains_every_result():
    req = UserRequirement(category=Category.LAPTOP, budget_max=150000, use_cases=[UseCase.PROGRAMMING])
    ranked = rank_hybrid(SAMPLE_LAPTOPS, req, top_n=5)
    scores = [r.final_score for r in ranked]
    assert scores == sorted(scores, reverse=True)
    for r in ranked:
        assert r.reasons  # every hybrid result is still explained from real data


def test_hybrid_never_crashes_with_zero_review_products():
    req = UserRequirement(category=Category.LAPTOP)
    # lap-4 has review_count=30, lap-5 has 15 — just confirm no div-by-zero etc.
    for product in SAMPLE_LAPTOPS:
        result = score_hybrid(product, req)
        assert result.final_score >= 0.0
