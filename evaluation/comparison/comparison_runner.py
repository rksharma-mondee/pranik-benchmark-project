# pranik/evaluation/comparison/comparison_runner.py
# Status: draft
# Clinical Reviewer Required: yes
# TODO: Add paired statistical significance tests after metric stabilization.
"""Run and score a two-model PRANIK comparison."""

from __future__ import annotations

from pathlib import Path

from evaluation.comparison.comparison_report import (
    ComparisonReport,
    build_comparison_report,
    save_comparison_report,
)
from evaluation.comparison.model_registry import ComparisonModel, DEFAULT_COMPARISON_MODELS
from evaluation.configs.eval_config import EvalConfig
from evaluation.pipelines.local_eval import run_evaluation
from evaluation.scoring.score_predictions import score_predictions
from evaluation.scoring.types import ScoreReport


def _latest_result_path(model_id: str, task: str, output_dir: Path) -> Path:
    safe_model = "".join(
        character if character.isalnum() or character in {"-", "_", "."} else "_"
        for character in model_id
    ).strip("_")
    matches = sorted(
        output_dir.glob(f"{safe_model}_{task}_*.jsonl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise FileNotFoundError(f"No evaluation result found for {model_id} on {task}")
    return matches[0]


def run_model_comparison(
    models: tuple[ComparisonModel, ...] = DEFAULT_COMPARISON_MODELS,
    benchmark_path: Path = Path("datasets/processed/friend_pranik_supported_20260522.jsonl"),
    task: str = "triage",
    max_cases: int | None = None,
    output_dir: Path = Path("evaluation/results"),
    report_dir: Path = Path("evaluation/reports"),
) -> tuple[ComparisonReport, Path]:
    """Run each model, score predictions, and save a comparison report."""

    scored_reports: list[tuple[str, ScoreReport]] = []
    for model in models:
        config = EvalConfig(
            model_id=model.model_id,
            tasks=[task],
            input_paths=[benchmark_path],
            output_dir=output_dir,
            max_cases=max_cases,
        )
        run_evaluation(config)
        eval_results_path = _latest_result_path(model.model_id, task, output_dir)
        score_report_path = report_dir / (
            f"{model.display_name}_{task}_score_report.json".replace(":", "_")
        )
        score_report = score_predictions(
            eval_results_path=eval_results_path,
            gold_cases_path=benchmark_path,
            output_report_path=score_report_path,
        )
        scored_reports.append((model.display_name, score_report))

    comparison_report = build_comparison_report(
        task=task,
        benchmark_path=benchmark_path,
        scored_reports=scored_reports,
    )
    comparison_report_path = save_comparison_report(comparison_report, report_dir)
    return comparison_report, comparison_report_path
