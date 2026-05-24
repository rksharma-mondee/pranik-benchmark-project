# api/routes/failures.py
# Status: draft
# Clinical Reviewer Required: yes
# TODO: connect critical failures to clinician review workflow
"""Failure analysis endpoints."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter


router = APIRouter()
REPORTS_DIR = Path("evaluation/reports")


def _read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _latest_file(pattern: str) -> Path | None:
    if not REPORTS_DIR.exists():
        return None
    matches = sorted(REPORTS_DIR.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _latest_score_reports() -> list[dict[str, Any]]:
    if not REPORTS_DIR.exists():
        return []
    paths = [
        path
        for path in REPORTS_DIR.glob("*.json")
        if path.name.endswith("_scores.json") or path.name.endswith("_score_report.json")
    ]
    if not paths:
        return []
    latest_by_model_task: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
    for path in sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True):
        report = _read_json(path)
        if not report:
            continue
        key = (str(report.get("model_id")), str(report.get("task")))
        if key not in latest_by_model_task:
            latest_by_model_task[key] = (path.stat().st_mtime, report)
    return [entry[1] for entry in latest_by_model_task.values()]


def _critical_from_score_reports() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for report in _latest_score_reports():
        for score in report.get("case_scores", []):
            if not isinstance(score, dict):
                continue
            if score.get("is_fatal_miss") or score.get("is_unsafe_reassurance"):
                records.append(
                    {
                        "case_id": score.get("case_id"),
                        "task": score.get("task"),
                        "language": score.get("language"),
                        "model": score.get("model") or report.get("model_id"),
                        "failure_types": [
                            failure
                            for failure, enabled in {
                                "fatal_under_triage": score.get("is_fatal_miss"),
                                "unsafe_reassurance": score.get("is_unsafe_reassurance"),
                            }.items()
                            if enabled
                        ],
                        "primary_failure": (
                            "fatal_under_triage"
                            if score.get("is_fatal_miss")
                            else "unsafe_reassurance"
                        ),
                        "failure_severity": "critical",
                        "gold_urgency": score.get("gold_urgency"),
                        "predicted_urgency": score.get("predicted_urgency"),
                        "gold_escalation": score.get("gold_escalation"),
                        "predicted_escalation": score.get("predicted_escalation"),
                        "severity_penalty": score.get("severity_penalty"),
                        "raw_response_preview": score.get("raw_response_preview"),
                        "recommended_action": "Immediate MD review required.",
                        "clinician_review_required": True,
                    }
                )
    return records


def _derived_failure_report() -> dict[str, Any]:
    critical = _critical_from_score_reports()
    by_language = Counter(str(record.get("language", "unknown")) for record in critical)
    by_task = Counter(str(record.get("task", "unknown")) for record in critical)
    distribution = Counter(str(record.get("primary_failure", "unknown")) for record in critical)
    return {
        "model": "latest_score_reports",
        "task": "mixed",
        "total_cases_analyzed": None,
        "total_failures": len(critical),
        "failure_rate": None,
        "critical_failure_count": len(critical),
        "failure_distribution": dict(sorted(distribution.items())),
        "failure_by_language": dict(sorted(by_language.items())),
        "failure_by_task": dict(sorted(by_task.items())),
        "most_common_failure": distribution.most_common(1)[0][0] if distribution else None,
        "critical_failures": critical,
        "all_failures": critical,
        "source": "score_reports",
    }


def _latest_failure_report() -> dict[str, Any] | None:
    failure_path = _latest_file("failure_analysis_*.json")
    failure_report = _read_json(failure_path)
    score_reports = _latest_score_reports()
    latest_score_mtime = 0.0
    if REPORTS_DIR.exists():
        score_paths = [
            path
            for path in REPORTS_DIR.glob("*.json")
            if path.name.endswith("_scores.json") or path.name.endswith("_score_report.json")
        ]
        if score_paths:
            latest_score_mtime = max(path.stat().st_mtime for path in score_paths)
    failure_mtime = failure_path.stat().st_mtime if failure_path else 0.0
    if score_reports and latest_score_mtime > failure_mtime:
        return _derived_failure_report()
    return failure_report


@router.get("/latest")
def get_latest_failures() -> dict[str, Any] | None:
    """Return latest failure analysis data."""

    return _latest_failure_report()


@router.get("/critical")
def get_critical_failures() -> list[dict[str, Any]]:
    """Return CRITICAL severity failures requiring immediate MD review."""

    report = _latest_failure_report()
    if not report:
        return []
    critical = report.get("critical_failures")
    if isinstance(critical, list):
        return [record for record in critical if isinstance(record, dict)]
    failures = report.get("all_failures", [])
    return [
        record
        for record in failures
        if isinstance(record, dict)
        and str(record.get("failure_severity", "")).lower() == "critical"
    ]


@router.get("/by-language")
def get_failures_by_language() -> dict[str, int]:
    """Return failure counts grouped by language."""

    report = _latest_failure_report()
    if not report:
        return {}
    existing = report.get("failure_by_language")
    if isinstance(existing, dict):
        return {str(key): int(value) for key, value in existing.items()}
    return dict(Counter(str(row.get("language", "unknown")) for row in get_critical_failures()))


@router.get("/by-task")
def get_failures_by_task() -> dict[str, int]:
    """Return failure counts grouped by task."""

    report = _latest_failure_report()
    if not report:
        return {}
    existing = report.get("failure_by_task")
    if isinstance(existing, dict):
        return {str(key): int(value) for key, value in existing.items()}
    return dict(Counter(str(row.get("task", "unknown")) for row in get_critical_failures()))
