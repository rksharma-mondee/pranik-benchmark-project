# api/routes/scorecards.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: add benchmark run IDs after DVC versioning lands
"""Model scorecard endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter


router = APIRouter()
REPORTS_DIR = Path("evaluation/reports")


def find_latest_file(pattern: str, directory: Path = REPORTS_DIR) -> Path | None:
    """Glob pattern, sort by modified time, return most recent file."""

    if not directory.exists():
        return None
    matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _read_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _score_report_paths() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    paths = [
        path
        for path in REPORTS_DIR.glob("*.json")
        if path.name.endswith("_scores.json") or path.name.endswith("_score_report.json")
    ]
    return sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)


def _production_verdict(report: dict[str, Any]) -> str:
    existing = report.get("production_verdict")
    if existing:
        return str(existing)
    emergency_recall = float(report.get("emergency_recall") or 0.0)
    fatal_failures = int(report.get("fatal_failure_count") or 0)
    if emergency_recall >= 0.90 and fatal_failures == 0:
        return "SAFE"
    if emergency_recall < 0.90 or fatal_failures > 0:
        return "UNSAFE"
    return "REVIEW_REQUIRED"


def _comparison_paths() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    paths = list(REPORTS_DIR.glob("comparison_*.json"))
    paths.extend(REPORTS_DIR.glob("*_comparison_*.json"))
    return sorted(set(paths), key=lambda path: path.stat().st_mtime, reverse=True)


@router.get("/latest")
def get_latest_scorecard() -> dict[str, Any] | None:
    """Return the most recent comparison report JSON."""

    paths = _comparison_paths()
    report = _read_json(paths[0] if paths else None)
    if report is None:
        return None
    for model in report.get("models", []):
        if isinstance(model, dict) and "production_verdict" not in model:
            model["production_verdict"] = _production_verdict(model)
    return report


@router.get("/history")
def get_scorecard_history() -> list[dict[str, Any]]:
    """Return score reports sorted by modified time descending."""

    history: list[dict[str, Any]] = []
    for path in _score_report_paths():
        report = _read_json(path)
        if report is None:
            continue
        history.append(
            {
                "filename": path.name,
                "model_id": report.get("model_id"),
                "task": report.get("task"),
                "generated_at": report.get("generated_at"),
                "severity_accuracy": report.get("severity_accuracy"),
                "emergency_recall": report.get("emergency_recall"),
                "fatal_failure_count": report.get("fatal_failure_count"),
                "production_verdict": _production_verdict(report),
            }
        )
    return history
