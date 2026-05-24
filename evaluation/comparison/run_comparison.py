# pranik/evaluation/comparison/run_comparison.py
# Status: draft
# Clinical Reviewer Required: yes
# TODO: Add CLI flags for benchmark path and model selection.
"""CLI entrypoint for PRANIK model comparison."""

from __future__ import annotations

from evaluation.comparison.comparison_report import print_comparison_report
from evaluation.comparison.comparison_runner import run_model_comparison


def main() -> None:
    """Run the default llama-3.3-70b vs llama-3.1-8b triage comparison."""

    report, output_path = run_model_comparison()
    print_comparison_report(report, output_path)


if __name__ == "__main__":
    main()
