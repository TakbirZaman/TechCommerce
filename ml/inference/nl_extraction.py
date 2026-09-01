"""
Natural language requirement extraction (spec sections 9 & 10).

This is a DETERMINISTIC, rule-based extractor (regex + keyword matching) —
no LLM call is made here. It exists so the system works end-to-end without
depending on an external LLM, and so there is always a transparent fallback
extractor to validate an LLM's output against or use when no LLM is
configured (spec section 29 — fallback behavior).

If/when an LLM-based extractor is added (see llm_validation.py), it MUST:
  1. Only output the same UserRequirement-shaped JSON.
  2. Be validated through validate_llm_output() before use.
  3. Never be allowed to pick or invent products/specs — that stays with the
     database-driven pipeline in ml/inference/.

Ambiguity handling: extract() returns (UserRequirement, list[str] missing_info).
missing_info lists which fields the extractor could NOT determine, and are
material enough to ask a follow-up about (spec section 22 — do not ask
unnecessary questions). The advisor conversation flow (ml/inference/advisor.py)
decides whether/how to ask, this module only reports what's known.
"""

from __future__ import annotations

import re

from ml.data.schemas import Category, Priorities, UseCase, UserRequirement

_CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.LAPTOP: ("laptop", "notebook", "ultrabook", "macbook"),
    Category.SMARTPHONE: ("phone", "smartphone", "mobile"),
    Category.MONITOR: ("monitor", "display screen", "external display"),
}

_USE_CASE_KEYWORDS: dict[UseCase, tuple[str, ...]] = {
    UseCase.PROGRAMMING: ("programming", "coding", "development", "developer", "software engineering"),
    UseCase.MACHINE_LEARNING: ("machine learning", "deep learning", "ml", "ai training", "data science"),
    UseCase.GAMING: ("gaming", "games", "gamer", "esports"),
    UseCase.VIDEO_EDITING: ("video editing", "editing videos", "premiere", "davinci"),
    UseCase.UNIVERSITY: ("university", "college", "student", "school"),
    UseCase.BUSINESS: ("business", "office work", "work laptop", "corporate"),
    UseCase.PHOTOGRAPHY: ("photography", "photo editing", "camera work"),
    UseCase.GENERAL: ("general use", "everyday use", "browsing"),
}

# "good/great camera", "good battery" style soft-priority phrases.
_QUALITY_PRIORITY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "camera": ("good camera", "great camera", "camera quality", "best camera"),
    "battery": ("good battery", "great battery", "long battery", "battery life"),
    "performance": ("fast", "powerful", "high performance", "good performance"),
    "display": ("good display", "great screen", "vibrant display"),
}

_BUDGET_PATTERNS = [
    # "under 100,000", "under 100k", "under 100000 BDT", "below 80k"
    re.compile(r"(?:under|below|less than|within)\s*(?:৳|tk\.?)?\s*([\d,]+)\s*(k|thousand)?", re.IGNORECASE),
    # "around 120k", "about 90,000"
    re.compile(r"(?:around|about|approx(?:imately)?)\s*(?:৳|tk\.?)?\s*([\d,]+)\s*(k|thousand)?", re.IGNORECASE),
    # "70k-100k", "70,000-100,000"
    re.compile(r"([\d,]+)\s*(k)?\s*(?:-|to)\s*([\d,]+)\s*(k)?", re.IGNORECASE),
]


def _parse_amount(num_str: str, suffix: str | None) -> float:
    value = float(num_str.replace(",", ""))
    if suffix and suffix.lower() in ("k", "thousand"):
        value *= 1000
    return value


def _extract_budget(text: str) -> tuple[float | None, float | None]:
    range_match = _BUDGET_PATTERNS[2].search(text)
    if range_match:
        lo = _parse_amount(range_match.group(1), range_match.group(2))
        hi = _parse_amount(range_match.group(3), range_match.group(4))
        return min(lo, hi), max(lo, hi)

    under_match = _BUDGET_PATTERNS[0].search(text)
    if under_match:
        return None, _parse_amount(under_match.group(1), under_match.group(2))

    around_match = _BUDGET_PATTERNS[1].search(text)
    if around_match:
        target = _parse_amount(around_match.group(1), around_match.group(2))
        # "around X" -> treat as a +/-10% band, used as budget_max for filtering
        # (budget_min is intentionally left soft/None to avoid over-filtering).
        return None, round(target * 1.10)

    return None, None


def _extract_category(text: str) -> Category | None:
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return None


def _extract_use_cases(text: str) -> list[UseCase]:
    found = []
    for use_case, keywords in _USE_CASE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            found.append(use_case)
    return found


def _extract_priorities(text: str) -> Priorities:
    values: dict[str, float] = {}
    for field, keywords in _QUALITY_PRIORITY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            values[field] = 0.85
    return Priorities(**values)


def extract_requirement(query: str) -> tuple[UserRequirement | None, list[str]]:
    """
    Parse a free-text query into a UserRequirement.

    Returns (requirement_or_None, missing_info). If category cannot be
    determined, requirement is None and missing_info includes "category" —
    the caller must ask a follow-up, since nothing meaningful can be
    filtered/ranked without knowing what kind of product is wanted.
    """
    text = query.lower().strip()
    missing: list[str] = []

    category = _extract_category(text)
    if category is None:
        return None, ["category"]

    budget_min, budget_max = _extract_budget(text)
    if budget_max is None:
        missing.append("budget")

    use_cases = _extract_use_cases(text)
    if not use_cases:
        missing.append("use_case")

    priorities = _extract_priorities(text)

    requirement = UserRequirement(
        category=category,
        budget_min=budget_min,
        budget_max=budget_max,
        use_cases=use_cases,
        priorities=priorities,
    )
    return requirement, missing
