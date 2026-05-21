"""Simple rule-aware model routing scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteDecision:
    model: str
    requires_human_review: bool
    reasons: list[str]


def route_case(text: str, default_model: str = "gemini") -> RouteDecision:
    lowered = text.lower()
    review_terms = ["chest pain", "breathless", "pregnant", "suicide", "dose"]
    reasons = [term for term in review_terms if term in lowered]
    return RouteDecision(
        model=default_model,
        requires_human_review=bool(reasons),
        reasons=reasons,
    )

