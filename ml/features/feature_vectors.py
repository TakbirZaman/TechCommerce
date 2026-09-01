"""
Category-aware product feature vectors.

Each category (laptop, smartphone, monitor) has its own feature set (spec 5).
For each feature we define:
  - which raw_specs key(s) to read
  - which normalization function converts it to a real-world unit
  - a domain-reasonable (min, max) range to scale that unit into [0, 1]
  - whether higher values are better (battery, RAM ...) or lower is better
    (weight, response time ...)

Fixed (not per-candidate-set) min/max bounds are used deliberately: they keep
a "16GB RAM" product scoring the same 0-1 value regardless of what else is in
the candidate pool, which is what the explanation engine relies on to say
things like "16GB RAM matches your requirement".

Missing specs produce `None` in the feature vector, never 0.0 — see
`build_feature_vector`. Callers (rule_based scorer) must handle None as
"exclude this dimension from scoring for this product", not "score it as
worst possible" (spec section 12).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ml.data.schemas import Category
from ml.preprocessing import normalization as norm
from ml.preprocessing import performance_lookup as perf


@dataclass(frozen=True)
class FeatureSpec:
    raw_keys: tuple[str, ...]  # tried in order; first present value wins
    normalizer: Callable[[object], float | None]
    range_min: float
    range_max: float
    higher_is_better: bool = True

    def scale(self, raw_value: float) -> float:
        lo, hi = self.range_min, self.range_max
        if hi == lo:
            return 0.5
        clipped = max(lo, min(hi, raw_value))
        scaled = (clipped - lo) / (hi - lo)
        return scaled if self.higher_is_better else 1.0 - scaled


CATEGORY_FEATURES: dict[Category, dict[str, FeatureSpec]] = {
    Category.LAPTOP: {
        "price": FeatureSpec(("price",), norm.normalize_price, 20_000, 400_000, higher_is_better=False),
        "cpu": FeatureSpec(("cpu", "processor"), perf.normalize_cpu_performance, 0, 100),
        "gpu": FeatureSpec(("gpu", "graphics"), perf.normalize_gpu_performance, 0, 100),
        "ram": FeatureSpec(("ram", "memory"), norm.normalize_ram_gb, 4, 64),
        "storage": FeatureSpec(("storage", "ssd", "storage_capacity"), norm.normalize_storage_gb, 128, 4096),
        "display": FeatureSpec(("display_size", "screen_size"), norm.normalize_display_inches, 11, 18),
        "refresh_rate": FeatureSpec(("refresh_rate",), norm.normalize_refresh_rate_hz, 60, 240),
        "battery": FeatureSpec(("battery", "battery_capacity"), norm.normalize_battery_wh, 30, 100),
        "weight": FeatureSpec(("weight",), norm.normalize_weight_kg, 0.9, 3.0, higher_is_better=False),
    },
    Category.SMARTPHONE: {
        "price": FeatureSpec(("price",), norm.normalize_price, 8_000, 200_000, higher_is_better=False),
        "cpu": FeatureSpec(("processor", "chipset", "cpu"), perf.normalize_cpu_performance, 0, 100),
        "ram": FeatureSpec(("ram", "memory"), norm.normalize_ram_gb, 2, 16),
        "storage": FeatureSpec(("storage",), norm.normalize_storage_gb, 32, 1024),
        "camera": FeatureSpec(("camera", "main_camera", "rear_camera"), norm.normalize_megapixels, 8, 200),
        "battery": FeatureSpec(("battery", "battery_capacity"), norm.normalize_battery_mah, 2500, 6000),
        "display": FeatureSpec(("display_size", "screen_size"), norm.normalize_display_inches, 5.5, 7.2),
        "charging": FeatureSpec(("charging_speed", "fast_charging"), norm.normalize_refresh_rate_hz, 10, 120),
    },
    Category.MONITOR: {
        "price": FeatureSpec(("price",), norm.normalize_price, 8_000, 150_000, higher_is_better=False),
        "size": FeatureSpec(("display_size", "screen_size"), norm.normalize_display_inches, 21, 34),
        "resolution": FeatureSpec(("resolution",), norm.normalize_resolution_pixels, 1_366 * 768, 3_840 * 2_160),
        "refresh_rate": FeatureSpec(("refresh_rate",), norm.normalize_refresh_rate_hz, 60, 360),
        "response_time": FeatureSpec(("response_time",), norm.normalize_response_time_ms, 1, 8, higher_is_better=False),
    },
}


def _first_present(raw_specs: dict, keys: tuple[str, ...]):
    for key in keys:
        if key in raw_specs and raw_specs[key] not in (None, ""):
            return raw_specs[key]
    return None


def build_feature_vector(category: Category, raw_specs: dict, price: float) -> dict[str, float | None]:
    """
    Convert raw_specs (+ the product's authoritative price field) into a
    dict of {feature_name: normalized_value_in_[0,1]_or_None}.
    """
    specs = CATEGORY_FEATURES.get(category)
    if specs is None:
        raise ValueError(f"No feature configuration for category: {category}")

    merged_raw = dict(raw_specs)
    merged_raw.setdefault("price", price)

    vector: dict[str, float | None] = {}
    for name, feature_spec in specs.items():
        raw_value = _first_present(merged_raw, feature_spec.raw_keys)
        normalized_unit = feature_spec.normalizer(raw_value)
        vector[name] = None if normalized_unit is None else feature_spec.scale(normalized_unit)
    return vector
