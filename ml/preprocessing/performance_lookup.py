"""
CPU / GPU performance normalization.

Unlike RAM or storage, "CPU performance" has no unit conversion — it needs a
reference score. We use a small curated lookup table (0-100 scale, roughly
anchored to relative multi-core benchmark standing) for common chips, and a
conservative heuristic fallback for chips not in the table.

IMPORTANT: if a chip cannot be matched or estimated with reasonable
confidence, these functions return None. The feature-engineering layer must
treat None as "unknown" (excluded from scoring, not scored as 0) — see
ml/features/feature_vectors.py. This table is a starting point and should be
maintained/expanded as real catalog data is seen; it is not a substitute for
a proper benchmark data source.
"""

from __future__ import annotations

import re

# Curated reference points, 0-100. Not exhaustive — extend as needed.
_CPU_TABLE: dict[str, float] = {
    "i3-12": 35, "i3-13": 38, "i5-12": 55, "i5-13": 60, "i5-14": 62,
    "i7-12": 72, "i7-13": 78, "i7-14": 80, "i9-12": 88, "i9-13": 92, "i9-14": 94,
    "ryzen 3 5": 32, "ryzen 3 7": 38, "ryzen 5 5": 52, "ryzen 5 7": 62,
    "ryzen 7 5": 68, "ryzen 7 7": 78, "ryzen 9 5": 85, "ryzen 9 7": 90,
    "m1": 65, "m1 pro": 78, "m1 max": 85, "m2": 70, "m2 pro": 82, "m2 max": 88,
    "m3": 74, "m3 pro": 84, "m3 max": 90,
    "snapdragon 8 gen 3": 82, "snapdragon 8 gen 2": 75, "snapdragon 8 gen 1": 68,
    "snapdragon 7": 45, "snapdragon 6": 30,
    "dimensity 9300": 80, "dimensity 9200": 74, "dimensity 8": 55, "dimensity 7": 42,
    "exynos 2400": 76, "exynos 2200": 65,
    "bionic a17": 88, "bionic a16": 82, "bionic a15": 76,
}

_GPU_TABLE: dict[str, float] = {
    "rtx 4090": 100, "rtx 4080": 92, "rtx 4070": 82, "rtx 4060": 68, "rtx 4050": 55,
    "rtx 3090": 90, "rtx 3080": 85, "rtx 3070": 75, "rtx 3060": 62, "rtx 3050": 48,
    "gtx 1660": 40, "gtx 1650": 32,
    "rx 7900": 90, "rx 7800": 80, "rx 7600": 60,
    "iris xe": 15, "uhd graphics": 8, "vega": 20,
    "apple gpu": 40,  # generic fallback for M-series integrated GPU mentions
}


def _match_table(text: str, table: dict[str, float]) -> float | None:
    text_l = text.lower()
    best_match: tuple[str, float] | None = None
    for key, score in table.items():
        if key in text_l:
            if best_match is None or len(key) > len(best_match[0]):
                best_match = (key, score)
    return best_match[1] if best_match else None


def normalize_cpu_performance(value: str | float | int | None) -> float | None:
    """
    Return a 0-100 relative CPU performance score, or None if the chip
    cannot be identified. Never fabricates a score for an unknown chip.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if 0 <= value <= 100 else None
    text = str(value).strip()
    if not text:
        return None
    return _match_table(text, _CPU_TABLE)


def normalize_gpu_performance(value: str | float | int | None) -> float | None:
    """
    Return a 0-100 relative GPU performance score, or None if the GPU
    cannot be identified. Integrated graphics with no dedicated GPU should
    be passed explicitly (e.g. 'Intel Iris Xe', 'integrated') rather than
    left blank, so they score low rather than unknown.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if 0 <= value <= 100 else None
    text = str(value).strip()
    if not text:
        return None
    score = _match_table(text, _GPU_TABLE)
    if score is not None:
        return score
    if re.search(r"(?i)integrated|no dedicated|shared graphics", text):
        return 10.0
    return None
