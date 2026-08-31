from ml.data.schemas import Category, UseCase, UserRequirement
from ml.inference.content_based import content_similarity_score, rank_by_content_similarity
from tests.fixtures import SAMPLE_LAPTOPS


def test_similarity_score_in_valid_range():
    req = UserRequirement(category=Category.LAPTOP, use_cases=[UseCase.GAMING])
    for product in SAMPLE_LAPTOPS:
        score = content_similarity_score(product, req)
        assert 0.0 <= score <= 1.0


def test_gaming_laptop_more_similar_to_gaming_requirement_than_budget_laptop():
    req = UserRequirement(category=Category.LAPTOP, use_cases=[UseCase.GAMING])
    gaming_laptop = next(p for p in SAMPLE_LAPTOPS if p.product_id == "lap-1")
    budget_laptop = next(p for p in SAMPLE_LAPTOPS if p.product_id == "lap-3")
    assert content_similarity_score(gaming_laptop, req) > content_similarity_score(budget_laptop, req)


def test_rank_by_content_similarity_orders_descending():
    req = UserRequirement(category=Category.LAPTOP, use_cases=[UseCase.PROGRAMMING])
    ranked = rank_by_content_similarity(SAMPLE_LAPTOPS, req, top_n=5)
    scores = [score for _, score in ranked]
    assert scores == sorted(scores, reverse=True)
