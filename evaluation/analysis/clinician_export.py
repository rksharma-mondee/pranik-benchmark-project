# pranik/evaluation/analysis/clinician_export.py
# Status: draft
# Clinical Reviewer Required: yes - CSV workflow must be approved by reviewers
"""Clinician-review exports for PRANIK failure analysis."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import structlog

from evaluation.analysis.failure_types import FailureAnalysisReport


logger = structlog.get_logger(__name__)

CSV_COLUMNS = [
    "case_id",
    "language",
    "task",
    "failure_type",
    "severity",
    "gold_urgency",
    "predicted_urgency",
    "patient_query_preview",
    "raw_response_preview",
    "recommended_action",
]


def _safe_model_name(model: str) -> str:
    """Create filesystem-safe model segment."""
    return "".join(
        character if character.isalnum() or character in {"-", "_", "."} else "_"
        for character in model
    ).strip("_")


def _json_report_path(failure_report: FailureAnalysisReport, csv_path: Path) -> Path:
    """Derive full JSON report path next to the CSV."""
    timestamp = failure_report.generated_at.strftime("%Y%m%d_%H%M%S")
    model = _safe_model_name(failure_report.model)
    return csv_path.parent / f"failure_analysis_{model}_{timestamp}.json"


def export_for_clinician_review(
    failure_report: FailureAnalysisReport,
    output_path: Path,
) -> Path:
    """Export high-severity failure cases to CSV and full report to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    review_cases = [
        record
        for record in failure_report.all_failures
        if record.clinician_review_required
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for record in review_cases:
            writer.writerow(
                {
                    "case_id": record.case_id,
                    "language": record.language,
                    "task": record.task,
                    "failure_type": record.primary_failure.value,
                    "severity": record.failure_severity.value,
                    "gold_urgency": record.gold_urgency,
                    "predicted_urgency": record.predicted_urgency,
                    "patient_query_preview": record.patient_query_preview,
                    "raw_response_preview": record.raw_response_preview,
                    "recommended_action": record.recommended_action,
                }
            )

    json_path = _json_report_path(failure_report, output_path)
    json_path.write_text(
        json.dumps(failure_report.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(
        "clinician_failure_export_written",
        csv_path=str(output_path),
        json_path=str(json_path),
        review_cases=len(review_cases),
    )
    return output_path
