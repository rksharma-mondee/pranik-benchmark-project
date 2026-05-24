# pranik/evaluation/comparison/model_registry.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: Move model comparison registry into config before production runs.
"""Model registry for PRANIK comparison runs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComparisonModel:
    """A model entry used in multi-model comparison."""

    model_id: str
    display_name: str


DEFAULT_COMPARISON_MODELS: tuple[ComparisonModel, ...] = (
    ComparisonModel(
        model_id="groq:llama-3.3-70b-versatile",
        display_name="llama-3.3-70b",
    ),
    ComparisonModel(
        model_id="groq:llama-3.1-8b-instant",
        display_name="llama-3.1-8b",
    ),
    ComparisonModel(
        model_id="groq:gemma2-9b-it",
        display_name="gemma2-9b-it",
    ),
    ComparisonModel(
        model_id="groq:mixtral-8x7b-32768",
        display_name="mixtral-8x7b",
    ),
)
