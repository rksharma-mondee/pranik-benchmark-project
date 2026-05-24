# api/routes/benchmark.py
# Status: draft
# Clinical Reviewer Required: no
# TODO: add dataset version metadata once DVC versioning is enabled
"""Benchmark dataset and preprocessing status endpoints."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter


router = APIRouter()

PROCESSED_DIR = Path("datasets/processed")
SYNTHETIC_DIR = Path("datasets/synthetic")
REJECTED_DIR = Path("datasets/rejected")
AUDIT_LOG_PATH = Path("datasets/audit/pii_audit_log.jsonl")


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _count_jsonl_lines(directory: Path) -> int:
    total = 0
    if not directory.exists():
        return total
    for path in directory.glob("*.jsonl"):
        with path.open("r", encoding="utf-8") as file:
            total += sum(1 for line in file if line.strip())
    return total


def _latest_mtime(paths: list[Path]) -> str | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    latest = max(path.stat().st_mtime for path in existing)
    return datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()


def _processed_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not PROCESSED_DIR.exists():
        return records
    for path in PROCESSED_DIR.glob("*.jsonl"):
        records.extend(_iter_jsonl(path))
    return records


def _pii_scrubbed_count() -> int:
    count = 0
    for entry in _iter_jsonl(AUDIT_LOG_PATH):
        if entry.get("status") == "scrubbed":
            count += 1
    return count


@router.get("/stats")
def get_benchmark_stats() -> dict[str, Any]:
    """Return dataset and preprocessing pipeline statistics."""

    records = _processed_records()
    task_distribution = Counter(str(record.get("task", "unknown")) for record in records)
    language_distribution = Counter(str(record.get("language", "unknown")) for record in records)
    processed_files = list(PROCESSED_DIR.glob("*.jsonl")) if PROCESSED_DIR.exists() else []
    synthetic_files = list(SYNTHETIC_DIR.glob("*.jsonl")) if SYNTHETIC_DIR.exists() else []
    rejected_files = list(REJECTED_DIR.glob("*.jsonl")) if REJECTED_DIR.exists() else []

    total_processed_cases = len(records)
    return {
        "total_processed_cases": total_processed_cases,
        "total_synthetic_cases": _count_jsonl_lines(SYNTHETIC_DIR),
        "total_rejected_cases": _count_jsonl_lines(REJECTED_DIR),
        "pii_scrubbed_count": _pii_scrubbed_count(),
        "task_distribution": dict(sorted(task_distribution.items())),
        "language_distribution": dict(sorted(language_distribution.items())),
        "last_updated": _latest_mtime(
            [*processed_files, *synthetic_files, *rejected_files, AUDIT_LOG_PATH]
        ),
        "pipeline_status": "healthy" if total_processed_cases > 0 else "no_data",
    }
