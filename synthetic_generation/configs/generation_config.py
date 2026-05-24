# pranik/synthetic_generation/configs/generation_config.py
# Status: draft
# Clinical Reviewer Required: yes - ALL synthetic cases need MD review before gold
# TODO(validation): add Giskard safety pre-scan before writing to output
# TODO(diversity): audit symptom distribution across cases quarterly
# TODO(clinician): route all synthetic cases to Label Studio review queue
# TODO(dedup): add MinHash deduplication before adding to benchmark pool
# FUTURE: replace Groq generator with MedGemma 4B self-hosted for clinical domain quality
"""Configuration for synthetic PRANIK benchmark case generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GenerationConfig:
    """Synthetic dataset generation configuration."""

    model_id: str = "llama-3.3-70b-versatile"
    temperature: float = 0.7
    max_tokens: int = 1500
    cases_per_task_per_language: int = 10
    output_dir: Path = Path("datasets/synthetic")
    tasks: list[str] = field(
        default_factory=lambda: [
            "triage",
            "escalation",
            "symptom_extraction",
            "refusal_behavior",
            "medication_explanation",
            "discharge_simplification",
            "counseling",
            "preventive_care",
            "doctor_note_summary",
        ]
    )
    languages: list[str] = field(
        default_factory=lambda: [
            "hi",
            "te",
            "kn",
            "bn",
            "en-IN",
            "mix",
        ]
    )
    dry_run: bool = False
