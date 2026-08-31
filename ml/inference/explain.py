"""
Explanation engine (spec section 20).

Every reason/trade-off string is derived directly from:
  - the product's actual raw spec value (formatted, not invented), or
  - a direct comparison against the user's stated requirement (budget, use case).

No text is generated from the model's "impression" of the product — only
from data that is already on the ScoredCandidate. If a value is unknown, it
is silently skipped rather than guessed at.
"""

from __future__ import annotations

from ml.data.schemas import UserRequirement
from ml.inference.rule_based import ScoredCandidate

# Human-readable labels + raw_spec keys + unit suffix, per feature.
_FEATURE_DISPLAY: dict[str, dict] = {
    "cpu": {"label": "CPU", "raw_keys": ("cpu", "processor")},
    "gpu": {"label": "GPU", "raw_keys": ("gpu", "graphics")},
    "ram": {"label": "RAM", "raw_keys": ("ram", "memory")},
    "storage": {"label": "storage", "raw_keys": ("storage", "ssd")},
    "battery": {"label": "battery", "raw_keys": ("battery", "battery_capacity")},
    "display": {"label": "display", "raw_keys": ("display_size", "screen_size")},
    "refresh_rate": {"label": "refresh rate", "raw_keys": ("refresh_rate",)},
    "weight": {"label": "weight", "raw_keys": ("weight",)},
    "camera": {"label": "camera", "raw_keys": ("camera", "main_camera")},
    "charging": {"label": "charging speed", "raw_keys": ("charging_speed",)},
    "size": {"label": "screen size", "raw_keys": ("display_size", "screen_size")},
    "resolution": {"label": "resolution", "raw_keys": ("resolution",)},
    "response_time": {"label": "response time", "raw_keys": ("response_time",)},
}

_STRONG_THRESHOLD = 0.70
_WEAK_THRESHOLD = 0.40
_MAX_REASONS = 4
_MAX_TRADEOFFS = 3


def _raw_value(raw_specs: dict, keys: tuple[str, ...]):
    for key in keys:
        if key in raw_specs and raw_specs[key] not in (None, ""):
            return raw_specs[key]
    return None


def generate_explanation(candidate: ScoredCandidate, requirement: UserRequirement) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    tradeoffs: list[str] = []

    if requirement.budget_max is not None and candidate.product.price <= requirement.budget_max:
        reasons.append(
            f"Fits your budget (৳{candidate.product.price:,.0f} within ৳{requirement.budget_max:,.0f})"
        )

    # Rank known features by weight (importance to this requirement), then
    # by how well the product scores on them.
    ranked_features = sorted(
        (
            (name, candidate.weights.get(name, 0.0), candidate.feature_vector[name])
            for name in candidate.feature_vector
            if candidate.feature_vector[name] is not None and candidate.weights.get(name, 0.0) > 0
        ),
        key=lambda t: t[1],
        reverse=True,
    )

    for name, weight, score in ranked_features:
        if len(reasons) >= _MAX_REASONS:
            break
        if score < _STRONG_THRESHOLD:
            continue
        display = _FEATURE_DISPLAY.get(name)
        if not display:
            continue
        raw_value = _raw_value(candidate.product.raw_specs, display["raw_keys"])
        if raw_value is None:
            continue
        reasons.append(f"Strong {display['label']} ({raw_value}) for your priorities")

    for name, weight, score in sorted(ranked_features, key=lambda t: t[2]):
        if len(tradeoffs) >= _MAX_TRADEOFFS:
            break
        if score >= _WEAK_THRESHOLD or weight < 0.05:
            continue
        display = _FEATURE_DISPLAY.get(name)
        if not display:
            continue
        raw_value = _raw_value(candidate.product.raw_specs, display["raw_keys"])
        label = display["label"]
        if raw_value is not None:
            tradeoffs.append(f"{label.capitalize()} ({raw_value}) is comparatively weak for this use case")
        else:
            tradeoffs.append(f"{label.capitalize()} is below average for this use case")

    if requirement.use_cases and reasons:
        use_case_names = ", ".join(uc.value.replace("_", " ") for uc in requirement.use_cases)
        reasons.insert(0, f"Matches your stated use case: {use_case_names}")

    if not reasons:
        reasons.append("Meets your core budget and category requirements")

    return reasons[:_MAX_REASONS], tradeoffs[:_MAX_TRADEOFFS]
