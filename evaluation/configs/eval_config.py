# pranik/evaluation/configs/eval_config.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: Move environment-specific overrides into checked config files before release runs.
"""Configuration for local PRANIK evaluation runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvalConfig:
    """Local evaluation runner configuration.

    Attributes:
        model_id: Model identifier string.
        tasks: Task names included in this run.
        input_paths: JSONL benchmark files to evaluate.
        output_dir: Directory where JSONL evaluation results are written.
        max_cases: Optional cap for development runs.
        temperature: Sampling temperature.
        max_tokens: Maximum output tokens.
        save_failed_cases: Whether failures should be persisted for analysis.
    """

    model_id: str = "gemini-2.0-flash"
    tasks: list[str] = field(default_factory=lambda: ["triage"])
    input_paths: list[Path] = field(
        default_factory=lambda: [Path("datasets/gold/triage_gold_v1.jsonl")]
    )
    output_dir: Path = Path("evaluation/results")
    max_cases: int | None = None
    temperature: float = 0.0
    max_tokens: int = 1024
    save_failed_cases: bool = True


# TODO(batch): replace single-case loop with batch inference in Phase 3
# TODO(safety): pipe EvaluationResult through safety/pipeline.py after scoring
# TODO(metrics): add task-specific scorer after raw outputs are stable
# FUTURE: replace file-based output with DVC-tracked dataset in Phase 4
