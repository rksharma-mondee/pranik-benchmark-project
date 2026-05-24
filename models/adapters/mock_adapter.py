# pranik/models/adapters/mock_adapter.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: Expand deterministic responses for non-triage tasks before CI uses mixed-task inputs.
"""Deterministic mock adapter for offline evaluation tests."""

from __future__ import annotations

import json

from models.adapters.base import AdapterConfig, ModelAdapter


class MockAdapter(ModelAdapter):
    """Offline adapter returning stable JSON responses."""

    def __init__(self, config: AdapterConfig) -> None:
        """Initialize mock adapter.

        Args:
            config: Adapter runtime configuration.
        """
        super().__init__(config)

    def generate(self, prompt: str) -> str:
        """Return a deterministic fake response matching triage gold-label shape.

        Args:
            prompt: Prompt string. It is accepted for interface compatibility.

        Returns:
            JSON string shaped like a `TriageGoldLabel`.
        """
        _ = prompt
        payload = {
            "label_type": "triage",
            "urgency": "ROUTINE",
            "action": "Mock response: route to routine clinician follow-up if symptoms persist.",
            "detected_red_flags": [],
            "reasoning": "Mock adapter uses deterministic low-risk output for offline testing.",
            "escalation_required": False,
            "escalation_reasoning": "No escalation in mock response.",
            "is_ambiguous": False,
            "ambiguity_reason": None,
            "arbitration_rule": None,
            "failure_modes": [],
            "reviewer_todo": None,
            "validation_notes": ["Mock output only; not clinically reviewed."],
            "future_improvements": ["Add task-aware mock outputs."],
        }
        return json.dumps(payload, ensure_ascii=False)

    def health_check(self) -> bool:
        """Verify mock adapter is available.

        Returns:
            Always True for offline testing.
        """
        return True


# TODO(batch): replace single-case loop with batch inference in Phase 3
# TODO(safety): pipe EvaluationResult through safety/pipeline.py after scoring
# TODO(metrics): add task-specific scorer after raw outputs are stable
# FUTURE: replace file-based output with DVC-tracked dataset in Phase 4
