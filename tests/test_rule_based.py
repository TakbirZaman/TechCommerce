from ml.data.schemas import Category, Priorities, UseCase, UserRequirement
from ml.features.weights import resolve_weights
from ml.inference.rule_based import rank_candidates, score_product
from tests.fixtures import SAMPLE_LAPTOPS


def test_weights_sum_to_one():
    req = UserRequirement(category=Category.LAPTOP, use_cases=[UseCase.GAMING])
    weights = resolve_weights(req.category, req.use_cases, req.priorities)
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_gaming_boosts_gpu_weight_over_default():
    default_weights = resolve_weights(Category.LAPTOP, [], Priorities())
    gaming_weights = resolve_weights(Category.LAPTOP, [UseCase.GAMING], Priorities())
    assert gaming_weights["gpu"] > default_weights["gpu"]


def test_university_boosts_battery_and_weight():
    default_weights = resolve_weights(Category.LAPTOP, [], Priorities())
    uni_weights = resolve_weights(Category.LAPTOP, [UseCase.UNIVERSITY], Priorities())
    assert uni_weights["battery"] > default_weights["battery"]
    assert uni_weights["weight"] > default_weights["weight"]


def test_explicit_priority_overrides_use_case_default():
    weights = resolve_weights(
        Category.LAPTOP, [UseCase.UNIVERSITY], Priorities(performance=0.9)
    )
    # explicit "performance" priority should push cpu/gpu weight up directly
    assert weights["cpu"] > 0 and weights["gpu"] > 0


def test_gaming_laptop_scores_higher_for_gaming_requirement():
    req = UserRequirement(category=Category.LAPTOP, budget_max=100000, use_cases=[UseCase.GAMING])
    gaming_laptop = next(p for p in SAMPLE_LAPTOPS if p.product_id == "lap-1")
    budget_laptop = next(p for p in SAMPLE_LAPTOPS if p.product_id == "lap-3")
    gaming_score = score_product(gaming_laptop, req)
    budget_score = score_product(budget_laptop, req)
    assert gaming_score.score > budget_score.score


def test_missing_specs_do_not_zero_out_score():
    req = UserRequirement(category=Category.LAPTOP, use_cases=[UseCase.PROGRAMMING])
    # lap-3 has no gpu/refresh_rate/battery specs at all
    budget_laptop = next(p for p in SAMPLE_LAPTOPS if p.product_id == "lap-3")
    result = score_product(budget_laptop, req)
    assert result.score > 0.0  # not crushed to zero just for missing fields
    assert result.feature_vector["gpu"] is None


def test_rank_candidates_orders_descending():
    req = UserRequirement(category=Category.LAPTOP, budget_max=150000, use_cases=[UseCase.MACHINE_LEARNING])
    ranked = rank_candidates(SAMPLE_LAPTOPS, req, top_n=10)
    scores = [c.score for c in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_candidates_respects_top_n():
    req = UserRequirement(category=Category.LAPTOP, budget_max=150000)
    ranked = rank_candidates(SAMPLE_LAPTOPS, req, top_n=2)
    assert len(ranked) == 2
