# pranik/evaluation/analysis/run_analysis.py
# Status: draft
# Clinical Reviewer Required: yes - analysis output must be validated by MD
"""CLI entrypoint for PRANIK failure analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.analysis.clinician_export import export_for_clinician_review
from evaluation.analysis.failure_analyzer import analyze_failures
from evaluation.analysis.failure_types import FailureAnalysisReport
from evaluation.scoring.types import ScoreReport


def _latest_path(directory: Path, pattern: str) -> Path:
    """Return latest matching file by modified time."""
    paths = sorted(
        directory.glob(pattern),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not paths:
        raise FileNotFoundError(f"No files matching {pattern} in {directory}")
    return paths[0]


def _load_score_report(path: Path) -> ScoreReport:
    """Load score report JSON."""
    return ScoreReport.model_validate_json(path.read_text(encoding="utf-8"))


def _default_clinician_csv_path(report: FailureAnalysisReport) -> Path:
    """Build default clinician CSV path."""
    timestamp = report.generated_at.strftime("%Y%m%d_%H%M%S")
    return Path("evaluation/reports") / f"clinician_review_{timestamp}.csv"


def _print_stdout_report(report: FailureAnalysisReport, csv_path: Path) -> None:
    """Print concise failure analysis summary."""
    print("Failure Analysis")
    print(f"model: {report.model}")
    print(f"task: {report.task}")
    print(f"total_cases_analyzed: {report.total_cases_analyzed}")
    print(f"total_failures: {report.total_failures}")
    print(f"failure_rate: {report.failure_rate:.3f}")
    print(f"critical_failure_count: {report.critical_failure_count}")
    print(f"most_common_failure: {report.most_common_failure}")
    print(f"failure_distribution: {report.failure_distribution}")
    print(f"failure_by_language: {report.failure_by_language}")
    print("recommendations:")
    for recommendation in report.recommendations:
        print(f"- {recommendation}")
    print(f"clinician_csv: {csv_path}")


def _parse_args() -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(description="Run PRANIK failure analysis.")
    parser.add_argument("--score-report", type=Path)
    parser.add_argument("--eval-results", type=Path)
    parser.add_argument("--gold-cases", type=Path, default=Path("examples/triage_cases.jsonl"))
    parser.add_argument("--clinician-csv", type=Path)
    return parser.parse_args()


def main() -> None:
    """Run failure analysis from files."""
    args = _parse_args()
    score_report_path = args.score_report or _latest_path(
        Path("evaluation/reports"), "*_scores.json"
    )
    eval_results_path = args.eval_results or _latest_path(
        Path("evaluation/results"), "*.jsonl"
    )
    score_report = _load_score_report(score_report_path)
    failure_report = analyze_failures(
        score_report=score_report,
        eval_results_path=eval_results_path,
        gold_cases_path=args.gold_cases,
    )
    csv_path = args.clinician_csv or _default_clinician_csv_path(failure_report)
    export_for_clinician_review(failure_report, csv_path)
    _print_stdout_report(failure_report, csv_path)


if __name__ == "__main__":
    main()
