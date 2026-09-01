"""
LLM output validation (spec section 10).

If an LLM is used for requirement extraction, its output must be validated
here before it ever reaches filtering/ranking. This module does not call
any LLM itself — it only validates a dict that a (future) LLM-integration
layer would produce, using the exact same UserRequirement schema as the
rule-based extractor (ml/inference/nl_extraction.py), so both paths are
interchangeable to the rest of the pipeline.

Anything the LLM output contains that is NOT part of UserRequirement
(e.g. a "recommended_product_ids" field, an attempt to smuggle a product
choice) is rejected outright — UserRequirement.model_config has
extra="forbid", so unknown keys raise a ValidationError rather than being
silently dropped or accepted.
"""

from __future__ import annotations

from pydantic import ValidationError

from ml.data.schemas import UserRequirement


class LLMOutputValidationError(Exception):
    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__(f"LLM output failed validation: {errors}")


def validate_llm_output(raw_output: dict) -> UserRequirement:
    """
    Validate a dict (already JSON-parsed) against UserRequirement.
    Raises LLMOutputValidationError on any schema violation — including
    unknown fields, out-of-range priorities, or an invalid category/use case.
    Callers should catch this and fall back to the rule-based extractor
    (spec section 29) rather than passing unvalidated data downstream.
    """
    try:
        return UserRequirement.model_validate(raw_output)
    except ValidationError as exc:
        raise LLMOutputValidationError(exc.errors()) from exc
