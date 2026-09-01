"""
Feature weight profiles (spec section 7).

Weights change according to user intent. Each use case defines a partial
weight profile over a category's features; profiles for multiple selected
use cases are averaged, then explicit user-stated priorities (UserRequirement
.priorities) override the corresponding entries — the user's own stated
preference always wins over an inferred default.

These starting weights are a deterministic, inspectable baseline (Stage 1).
They are not learned and are not claimed to be optimal — see spec section 16
for where a learned ranking model eventually supplements this.
"""

from __future__ import annotations

from ml.data.schemas import Category, Priorities, UseCase

# Default weights per category when no use case / priority narrows them.
DEFAULT_WEIGHTS: dict[Category, dict[str, float]] = {
    Category.LAPTOP: {
        "cpu": 0.20, "gpu": 0.10, "ram": 0.15, "storage": 0.10,
        "price": 0.25, "battery": 0.10, "display": 0.05, "refresh_rate": 0.03, "weight": 0.02,
    },
    Category.SMARTPHONE: {
        "cpu": 0.20, "ram": 0.15, "storage": 0.10, "camera": 0.20,
        "price": 0.20, "battery": 0.10, "display": 0.03, "charging": 0.02,
    },
    Category.MONITOR: {
        "price": 0.25, "size": 0.15, "resolution": 0.25,
        "refresh_rate": 0.20, "response_time": 0.15,
    },
}

# Use-case overrides: only the features that should shift are listed.
# These are merged onto (not replacing) the category default before
# renormalization.
USE_CASE_WEIGHTS: dict[Category, dict[UseCase, dict[str, float]]] = {
    Category.LAPTOP: {
        UseCase.GAMING: {"cpu": 0.25, "gpu": 0.30, "ram": 0.15, "price": 0.15, "refresh_rate": 0.10, "storage": 0.05},
        UseCase.PROGRAMMING: {"cpu": 0.30, "ram": 0.25, "storage": 0.15, "price": 0.20, "battery": 0.05, "gpu": 0.05},
        UseCase.MACHINE_LEARNING: {"cpu": 0.25, "gpu": 0.30, "ram": 0.25, "storage": 0.10, "price": 0.10},
        UseCase.VIDEO_EDITING: {"cpu": 0.25, "gpu": 0.20, "ram": 0.20, "storage": 0.15, "display": 0.10, "price": 0.10},
        UseCase.UNIVERSITY: {"battery": 0.25, "weight": 0.20, "price": 0.25, "cpu": 0.15, "ram": 0.10, "storage": 0.05},
        UseCase.BUSINESS: {"battery": 0.20, "weight": 0.15, "price": 0.20, "cpu": 0.20, "ram": 0.15, "display": 0.10},
        UseCase.GENERAL: DEFAULT_WEIGHTS[Category.LAPTOP],
    },
    Category.SMARTPHONE: {
        UseCase.PHOTOGRAPHY: {"camera": 0.40, "display": 0.15, "cpu": 0.15, "storage": 0.15, "price": 0.15},
        UseCase.GAMING: {"cpu": 0.35, "ram": 0.20, "battery": 0.15, "display": 0.15, "price": 0.15},
        UseCase.BUSINESS: {"battery": 0.25, "cpu": 0.20, "storage": 0.15, "price": 0.20, "camera": 0.10, "display": 0.10},
        UseCase.GENERAL: DEFAULT_WEIGHTS[Category.SMARTPHONE],
    },
    Category.MONITOR: {
        UseCase.GAMING: {"refresh_rate": 0.35, "response_time": 0.25, "resolution": 0.20, "price": 0.15, "size": 0.05},
        UseCase.VIDEO_EDITING: {"resolution": 0.35, "size": 0.20, "price": 0.20, "refresh_rate": 0.10, "response_time": 0.15},
        UseCase.GENERAL: DEFAULT_WEIGHTS[Category.MONITOR],
    },
}

# Maps Priorities field names -> the feature-vector keys they influence.
# A user priority can affect more than one underlying feature (e.g.
# "performance" boosts both cpu and gpu).
_PRIORITY_TO_FEATURES: dict[str, tuple[str, ...]] = {
    "performance": ("cpu", "gpu"),
    "cpu": ("cpu",),
    "gpu": ("gpu",),
    "ram": ("ram",),
    "storage": ("storage",),
    "battery": ("battery",),
    "weight": ("weight",),
    "display": ("display", "size"),
    "camera": ("camera",),
    "price": ("price",),
}


def _normalize(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        n = len(weights) or 1
        return {k: 1.0 / n for k in weights}
    return {k: v / total for k, v in weights.items()}


def resolve_weights(
    category: Category,
    use_cases: list[UseCase],
    priorities: Priorities,
) -> dict[str, float]:
    """
    Produce the final, normalized (sums to 1.0) feature weight profile for
    a requirement: category default -> blended with selected use cases ->
    overridden by any explicit user priorities.
    """
    base = dict(DEFAULT_WEIGHTS[category])
    profiles = USE_CASE_WEIGHTS.get(category, {})

    if use_cases:
        matched = [profiles[uc] for uc in use_cases if uc in profiles]
        if matched:
            blended: dict[str, float] = {k: 0.0 for k in base}
            for profile in matched:
                for k, v in profile.items():
                    blended[k] = blended.get(k, 0.0) + v
            for k in blended:
                blended[k] /= len(matched)
            # Keep any base feature not touched by any matched use case.
            for k, v in base.items():
                blended.setdefault(k, v)
            base = blended

    priorities_dict = priorities.model_dump(exclude_none=True)
    for priority_name, value in priorities_dict.items():
        for feature_key in _PRIORITY_TO_FEATURES.get(priority_name, ()):
            if feature_key in base:
                base[feature_key] = value

    return _normalize(base)
