from datetime import datetime, timedelta

import pytest

from ml.data.events import EventType, InteractionEvent
from ml.data.schemas import Category, UseCase, UserRequirement
from ml.training.train_ranker import (
    MIN_TRAINING_EXAMPLES,
    InsufficientDataError,
    build_features_for_example,
    build_training_dataframe,
    examples_from_events,
    train_ranker,
    train_test_split_temporal,
)
from tests.fixtures import SAMPLE_LAPTOPS

PRODUCTS_BY_ID = {p.product_id: p for p in SAMPLE_LAPTOPS}


def test_build_features_returns_expected_keys():
    req = UserRequirement(category=Category.LAPTOP, budget_max=100000, use_cases=[UseCase.GAMING])
    product = PRODUCTS_BY_ID["lap-1"]
    features = build_features_for_example(product, req)
    assert set(features.keys()) == {
        "price_match", "category_match", "brand_match", "content_similarity",
        "rating", "review_count", "budget_fit", "requirement_weight_sum",
    }
    assert features["category_match"] == 1.0
    assert features["budget_fit"] == 1.0  # 95,000 <= 100,000


def test_budget_fit_zero_when_over_budget():
    req = UserRequirement(category=Category.LAPTOP, budget_max=50000)
    product = PRODUCTS_BY_ID["lap-1"]  # 95,000
    features = build_features_for_example(product, req)
    assert features["budget_fit"] == 0.0


def test_train_raises_insufficient_data_error_below_threshold():
    req = UserRequirement(category=Category.LAPTOP, use_cases=[UseCase.GAMING])
    events = [
        InteractionEvent(
            user_id="u1", product_id="lap-1", event_type=EventType.PRODUCT_VIEW,
            timestamp=datetime(2026, 1, 1),
        )
    ]  # far fewer than MIN_TRAINING_EXAMPLES
    examples = examples_from_events(events, {"u1": req})
    df = build_training_dataframe(examples, PRODUCTS_BY_ID)
    assert len(df) < MIN_TRAINING_EXAMPLES
    with pytest.raises(InsufficientDataError):
        train_ranker(df)


def test_temporal_split_keeps_chronological_order():
    import pandas as pd

    df = pd.DataFrame({
        "timestamp": [datetime(2026, 1, i) for i in range(1, 11)],
        "label": list(range(10)),
    })
    train_df, test_df = train_test_split_temporal(df, test_fraction=0.3)
    assert train_df["timestamp"].max() < test_df["timestamp"].min()
    assert len(train_df) + len(test_df) == len(df)


def test_examples_from_events_skips_users_without_a_captured_requirement():
    events = [
        InteractionEvent(user_id="known", product_id="lap-1", event_type=EventType.CART_ADD,
                          timestamp=datetime(2026, 1, 1)),
        InteractionEvent(user_id="unknown", product_id="lap-2", event_type=EventType.CART_ADD,
                          timestamp=datetime(2026, 1, 1)),
    ]
    req = UserRequirement(category=Category.LAPTOP)
    examples = examples_from_events(events, {"known": req})
    assert len(examples) == 1
    assert examples[0].user_id == "known"


def test_train_ranker_pipeline_mechanics_with_synthetic_data():
    """
    SYNTHETIC DATA — this test exists only to prove the training pipeline
    (feature building -> temporal split -> XGBoost fit -> predict) runs
    end-to-end without error. It does NOT assert or imply anything about
    real-world model accuracy (spec section 34).
    """
    req_gaming = UserRequirement(category=Category.LAPTOP, budget_max=150000, use_cases=[UseCase.GAMING])
    base_time = datetime(2026, 1, 1)
    events = []
    for i in range(MIN_TRAINING_EXAMPLES + 10):
        product_id = SAMPLE_LAPTOPS[i % len(SAMPLE_LAPTOPS)].product_id
        events.append(
            InteractionEvent(
                user_id="synthetic_user",
                product_id=product_id,
                event_type=EventType.PRODUCT_VIEW if i % 3 else EventType.CART_ADD,
                timestamp=base_time + timedelta(minutes=i),
            )
        )
    examples = examples_from_events(events, {"synthetic_user": req_gaming})
    df = build_training_dataframe(examples, PRODUCTS_BY_ID)

    model = train_ranker(df)
    predictions = model.predict(df[[
        "price_match", "category_match", "brand_match", "content_similarity",
        "rating", "review_count", "budget_fit", "requirement_weight_sum",
    ]])
    assert len(predictions) == len(df)
