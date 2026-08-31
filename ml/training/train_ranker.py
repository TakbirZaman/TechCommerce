"""
Stage 4: ML ranking model training (spec section 16).

IMPORTANT (spec sections 16, 27, 34):
- This module trains ONLY on real InteractionEvent + Product +
  UserRequirement data. It refuses to train (raises InsufficientDataError)
  below MIN_TRAINING_EXAMPLES, rather than silently training on too little
  data and reporting misleading metrics.
- Temporal splitting: `train_test_split_temporal` splits by timestamp, not
  randomly, so a model is never evaluated on examples that occurred before
  ones it was trained on being reversed — training data must never include
  interactions that happened after the prediction point for the same user
  journey. This is the concrete guard against the leakage described in
  spec section 27.
- Nothing in this module is run against fabricated data in this codebase.
  ml/training/tests exercise the pipeline's mechanics with clearly-labeled
  synthetic fixtures ONLY to prove the code runs end-to-end; those results
  are never reported as real model performance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split

from ml.data.events import DEFAULT_EVENT_WEIGHTS, EventType, InteractionEvent
from ml.data.schemas import Product, UserRequirement
from ml.features.feature_vectors import build_feature_vector
from ml.features.weights import resolve_weights

MIN_TRAINING_EXAMPLES = 500  # below this, Stage 4 must not run — use fallback (spec 29)

FEATURE_COLUMNS = [
    "price_match", "category_match", "brand_match", "content_similarity",
    "rating", "review_count", "budget_fit", "requirement_weight_sum",
]


class InsufficientDataError(Exception):
    """Raised when there isn't enough real interaction data to train responsibly."""


@dataclass
class TrainingExample:
    user_id: str
    product_id: str
    requirement: UserRequirement
    label: float  # weighted interaction outcome (spec 14) — the training target
    timestamp: datetime


def build_features_for_example(product: Product, requirement: UserRequirement) -> dict[str, float]:
    """Spec section 16's candidate feature list, computed from real product/requirement data only."""
    vector = build_feature_vector(product.category, product.raw_specs, product.price)
    weights = resolve_weights(requirement.category, requirement.use_cases, requirement.priorities)

    price_match = 0.0
    if requirement.budget_max:
        price_match = 1.0 - min(1.0, abs(product.price - requirement.budget_max) / requirement.budget_max)

    budget_fit = 1.0
    if requirement.budget_max is not None and product.price > requirement.budget_max:
        budget_fit = 0.0
    elif requirement.budget_min is not None and product.price < requirement.budget_min:
        budget_fit = 0.0

    known_pairs = [(vector[k], weights.get(k, 0.0)) for k in vector if vector[k] is not None]
    content_similarity = (
        sum(v * w for v, w in known_pairs) / sum(w for _, w in known_pairs)
        if known_pairs and sum(w for _, w in known_pairs) > 0
        else 0.0
    )

    return {
        "price_match": round(price_match, 4),
        "category_match": 1.0 if product.category == requirement.category else 0.0,
        "brand_match": 1.0 if product.brand in requirement.preferred_brands else 0.0,
        "content_similarity": round(content_similarity, 4),
        "rating": product.rating or 0.0,
        "review_count": float(product.review_count),
        "budget_fit": budget_fit,
        "requirement_weight_sum": round(sum(weights.values()), 4),
    }


def build_training_dataframe(
    examples: list[TrainingExample], products_by_id: dict[str, Product]
) -> pd.DataFrame:
    rows = []
    for ex in examples:
        product = products_by_id.get(ex.product_id)
        if product is None:
            continue
        features = build_features_for_example(product, ex.requirement)
        features["label"] = ex.label
        features["timestamp"] = ex.timestamp
        rows.append(features)
    return pd.DataFrame(rows)


def examples_from_events(
    events: list[InteractionEvent],
    requirements_by_user: dict[str, UserRequirement],
    weights: dict[EventType, float] | None = None,
) -> list[TrainingExample]:
    """
    Convert raw interaction events into labeled training examples. A user
    with no captured requirement (e.g. they never used the advisor/search
    filters) contributes no examples — we do not invent a requirement for
    them.
    """
    active_weights = weights or DEFAULT_EVENT_WEIGHTS
    examples = []
    for event in events:
        requirement = requirements_by_user.get(event.user_id)
        if requirement is None:
            continue
        examples.append(
            TrainingExample(
                user_id=event.user_id,
                product_id=event.product_id,
                requirement=requirement,
                label=active_weights.get(event.event_type, 0),
                timestamp=event.timestamp,
            )
        )
    return examples


def train_test_split_temporal(df: pd.DataFrame, test_fraction: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split by timestamp (not randomly): the earliest (1 - test_fraction) of
    events train the model, the most recent test_fraction evaluate it. This
    guarantees no future interaction leaks into training (spec section 27).
    """
    sorted_df = df.sort_values("timestamp")
    split_idx = int(len(sorted_df) * (1 - test_fraction))
    return sorted_df.iloc[:split_idx], sorted_df.iloc[split_idx:]


def train_ranker(df: pd.DataFrame) -> xgb.XGBRegressor:
    """
    Train an XGBoost ranker on real labeled examples.
    Raises InsufficientDataError if there isn't enough data to train
    responsibly — callers must fall back to rule-based/content-based
    scoring in that case (spec section 29), never train on too little data
    and present the result as reliable.
    """
    if len(df) < MIN_TRAINING_EXAMPLES:
        raise InsufficientDataError(
            f"Only {len(df)} labeled examples available; "
            f"need at least {MIN_TRAINING_EXAMPLES} to train responsibly. "
            "Falling back to rule-based/content-based recommendation."
        )

    train_df, _test_df = train_test_split_temporal(df)
    X = train_df[FEATURE_COLUMNS]
    y = train_df["label"]

    model = xgb.XGBRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.05, objective="reg:squarederror"
    )
    model.fit(X, y)
    return model
