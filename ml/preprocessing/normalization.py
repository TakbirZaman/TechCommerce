"""
Normalization functions for raw product specifications.

Raw catalog data is inconsistent: "16GB", "16 GB", "16384MB" all mean the
same thing. These functions convert a raw value (str | int | float | None)
into a single consistent unit. They never guess a missing value — if the
input is None/empty/unparseable, the function returns None, and callers
must treat that as "unknown", not "zero" (see ml/features/feature_vectors.py).
"""

from __future__ import annotations

import re

# Captures a leading number and the unit token immediately attached to it
# (e.g. "1TB", "16 GB", "1500g", "5Ah" -> (1, "TB"), (16, "GB"), (1500, "g"), (5, "Ah")).
# This avoids the classic word-boundary bug where \b fails between a digit
# and an adjacent letter (both are \w characters, so no boundary exists there).
_NUMBER_UNIT_RE = re.compile(r"([-+]?\d*\.?\d+)\s*([a-zA-Z\"]*)")
_NUMBER_RE = re.compile(r"[-+]?\d*\.?\d+")


def _split_number_unit(text: str) -> tuple[float, str] | None:
    match = _NUMBER_UNIT_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        number = float(match.group(1))
    except ValueError:
        return None
    unit = match.group(2).strip().lower()
    return number, unit


def _extract_number(text: str) -> float | None:
    match = _NUMBER_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def normalize_price(value: str | int | float | None) -> float | None:
    """Return price as numeric BDT. Strips currency symbols/words/commas."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"(?i)(bdt|tk\.?|৳|taka)", "", text).strip()
    num = _extract_number(text)
    return num if num is not None and num > 0 else None


def normalize_ram_gb(value: str | int | float | None) -> float | None:
    """Return RAM in GB. Accepts '16GB', '16 GB', '16384MB', 16 (assumed GB)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value).strip()
    if not text:
        return None
    parsed = _split_number_unit(text)
    if parsed is None:
        return None
    num, unit = parsed
    if unit == "mb":
        return round(num / 1024, 3)
    return num  # GB, or unitless assumed GB


def normalize_storage_gb(value: str | int | float | None) -> float | None:
    """Return storage in GB. Accepts '512GB', '1TB', '1 TB', 512 (assumed GB)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value).strip()
    if not text:
        return None
    parsed = _split_number_unit(text)
    if parsed is None:
        return None
    num, unit = parsed
    if unit == "tb":
        return num * 1024
    if unit == "mb":
        return round(num / 1024, 3)
    return num  # GB, or unitless assumed GB


def normalize_display_inches(value: str | int | float | None) -> float | None:
    """Return display size in inches. Accepts '15.6"', '15.6 inch', '39.6cm'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value).strip()
    if not text:
        return None
    num = _extract_number(text)
    if num is None:
        return None
    if re.search(r"(?i)cm", text):
        return round(num / 2.54, 2)
    return num  # inches (covers '"', 'inch', 'in', or unitless)


def normalize_refresh_rate_hz(value: str | int | float | None) -> float | None:
    """Return refresh rate in Hz. Accepts '144Hz', '144 Hz', 144."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    return _extract_number(str(value))


def normalize_battery_mah(value: str | int | float | None) -> float | None:
    """Return battery capacity in mAh. Accepts '5000mAh', '5000 mAh', '5Ah', 5000."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value).strip()
    if not text:
        return None
    parsed = _split_number_unit(text)
    if parsed is None:
        return None
    num, unit = parsed
    if unit == "ah":  # Ah, but not mAh (unit token would be "mah")
        return num * 1000
    return num


def normalize_battery_wh(value: str | int | float | None) -> float | None:
    """Return battery capacity in Wh (common for laptops). Accepts '70Wh', '70 Wh'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    return _extract_number(str(value))


def normalize_weight_kg(value: str | int | float | None) -> float | None:
    """Return weight in kg. Accepts '1.5kg', '1500g', '3.3lb'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value).strip()
    if not text:
        return None
    parsed = _split_number_unit(text)
    if parsed is None:
        return None
    num, unit = parsed
    if unit in ("g", "gram", "grams"):
        return round(num / 1000, 4)
    if unit in ("lb", "lbs", "pound", "pounds"):
        return round(num * 0.453592, 4)
    return num  # kg, or unitless assumed kg


def normalize_megapixels(value: str | int | float | None) -> float | None:
    """Return camera resolution in MP. Accepts '108MP', '108 MP', 108."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    return _extract_number(str(value))


def normalize_response_time_ms(value: str | int | float | None) -> float | None:
    """Return monitor response time in ms. Accepts '1ms', '1 ms', 1."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else None
    return _extract_number(str(value))


def normalize_resolution_pixels(value: str | int | float | None) -> int | None:
    """
    Return total pixel count for a resolution string like '1920x1080' or
    '3840 x 2160'. Used as a comparable proxy for display/monitor sharpness.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    text = str(value).strip().lower().replace(" ", "")
    match = re.match(r"(\d+)x(\d+)", text)
    if not match:
        return None
    w, h = int(match.group(1)), int(match.group(2))
    return w * h
