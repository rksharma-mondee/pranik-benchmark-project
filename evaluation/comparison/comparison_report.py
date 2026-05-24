# pranik/evaluation/comparison/comparison_report.py
# Status: draft
# Clinical Reviewer Required: yes
# TODO: Add clinician-facing failure slices before release use.
"""Comparison report models and persistence helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from evaluation.scoring.types import ScoreReport


class ModelComparisonRow(BaseModel):
    """One model's aggregate metrics in a comparison report."""

    model_id: str
    display_name: str
    total_cases: int
    parse_success_rate: float
    severity_accuracy: float
    weighted_f1: float
    emergency_recall: float
    escalation_accuracy: float
    mean_severity_penalty: float
    fatal_failure_count: int
    unsafe_reassurance_count: int


class ComparisonReport(BaseModel):
    """Multi-model comparison report."""

    task: str
    benchmark_path: str
    models: list[ModelComparisonRow]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def build_comparison_report(
    task: str,
    benchmark_path: Path,
    scored_reports: list[tuple[str, ScoreReport]],
) -> ComparisonReport:
    """Build a comparison report from scored model reports."""

    rows = [
        ModelComparisonRow(
            model_id=report.model_id,
            display_name=display_name,
            total_cases=report.total_cases,
            parse_success_rate=report.parse_success_rate,
            severity_accuracy=report.severity_accuracy,
            weighted_f1=report.weighted_f1,
            emergency_recall=report.emergency_recall,
            escalation_accuracy=report.escalation_accuracy,
            mean_severity_penalty=report.mean_severity_penalty,
            fatal_failure_count=report.fatal_failure_count,
            unsafe_reassurance_count=report.unsafe_reassurance_count,
        )
        for display_name, report in scored_reports
    ]
    return ComparisonReport(task=task, benchmark_path=str(benchmark_path), models=rows)


def save_comparison_report(report: ComparisonReport, output_dir: Path) -> Path:
    """Persist comparison report as JSON and return its path."""

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = report.generated_at.strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"{report.task}_comparison_{timestamp}.json"
    path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def print_comparison_report(report: ComparisonReport, output_path: Path) -> None:
    """Print a compact comparison table to stdout."""

    print("PRANIK Model Comparison")
    print(f"Task      : {report.task}")
    print(f"Benchmark : {report.benchmark_path}")
    print(f"Report    : {output_path}")
    print()
    print(
        "{:<18} {:>6} {:>8} {:>8} {:>8} {:>8} {:>7}".format(
            "Model",
            "Cases",
            "Parse",
            "SevAcc",
            "EmerRec",
            "EscAcc",
            "Fatal",
        )
    )
    for row in report.models:
        print(
            "{:<18} {:>6} {:>8.3f} {:>8.3f} {:>8.3f} {:>8.3f} {:>7}".format(
                row.display_name,
                row.total_cases,
                row.parse_success_rate,
                row.severity_accuracy,
                row.emergency_recall,
                row.escalation_accuracy,
                row.fatal_failure_count,
            )
        )
