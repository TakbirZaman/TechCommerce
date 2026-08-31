"""
AI Product Advisor conversation flow (spec sections 21 & 22).

A minimal, deterministic state machine — no LLM required to run this.
Each turn: parse whatever new info the user gave, merge it into the
requirement built so far, then ask at most ONE follow-up question for the
single most material missing field. "Material" is judged by what actually
changes recommendation quality: category is always material (nothing can
be filtered without it); budget is material because laptops/phones span a
huge price range; use_case is material because it drives weighting.
Anything else (exact brand, exact RAM) is left to priorities/required_specs
and never forced as a blocking question.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import re

from ml.data.schemas import Category, UserRequirement
from ml.inference.nl_extraction import _extract_budget, _extract_use_cases, _parse_amount, extract_requirement

_BARE_AMOUNT_RE = re.compile(r"^\s*(?:৳|tk\.?)?\s*([\d,]+)\s*(k|thousand)?\s*\.?\s*$", re.IGNORECASE)

_QUESTION_PRIORITY = ["category", "budget", "use_case"]

_FOLLOW_UP_TEXT = {
    "category": "What kind of product are you looking for? (laptop, smartphone, or monitor)",
    "budget": "What's your approximate budget?",
    "use_case": "What will you mainly use it for? (e.g. programming, gaming, machine learning, "
                "video editing, university, business, general use)",
}


@dataclass
class AdvisorState:
    partial: dict = field(default_factory=dict)  # accumulated known fields
    turns: int = 0


def advance_conversation(
    state: AdvisorState, user_message: str
) -> tuple[AdvisorState, str | None, UserRequirement | None]:
    """
    Process one user turn.

    Returns (updated_state, follow_up_question_or_None, requirement_or_None).
    If follow_up_question is not None, the requirement is not yet complete
    enough to recommend from and the caller should show the question (the
    frontend may render it as free text or as suggested option chips, e.g.
    for use_case — see spec section 21's example options).
    If requirement is not None, enough is known to call the recommendation
    pipeline.
    """
    state.turns += 1
    extracted, _missing = extract_requirement(user_message)

    if extracted is not None:
        state.partial.update(extracted.model_dump(exclude_none=True, exclude_defaults=True))
    else:
        # Category couldn't be parsed this turn — but the user may have
        # answered a budget/use_case-only question (e.g. just "90k").
        _merge_partial_answer(state, user_message)

    missing_now = _compute_missing(state)
    if missing_now:
        next_field = next(f for f in _QUESTION_PRIORITY if f in missing_now)
        return state, _FOLLOW_UP_TEXT[next_field], None

    requirement = UserRequirement.model_validate(state.partial)
    return state, None, requirement


def _merge_partial_answer(state: AdvisorState, user_message: str) -> None:
    """Salvage a budget-only or use-case-only answer with no category present."""
    text = user_message.lower().strip()

    _, budget_max = _extract_budget(text)
    if budget_max is None:
        bare_match = _BARE_AMOUNT_RE.match(text)
        if bare_match:
            budget_max = _parse_amount(bare_match.group(1), bare_match.group(2))
    if budget_max is not None:
        state.partial["budget_max"] = budget_max

    use_cases = _extract_use_cases(text)
    if use_cases:
        existing = state.partial.get("use_cases", [])
        state.partial["use_cases"] = list({*existing, *[uc.value for uc in use_cases]})

    if "category" not in state.partial:
        for cat in Category:
            if cat.value in text:
                state.partial["category"] = cat.value


def _compute_missing(state: AdvisorState) -> list[str]:
    missing = []
    if not state.partial.get("category"):
        missing.append("category")
    elif not state.partial.get("budget_max"):
        missing.append("budget")
    elif not state.partial.get("use_cases"):
        missing.append("use_case")
    return missing
