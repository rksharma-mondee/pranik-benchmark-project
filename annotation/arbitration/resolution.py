# pranik/annotation/arbitration/resolution.py
# Status: draft
# Clinical Reviewer Required: yes - this is the senior arbitration workflow
# TODO: Replace CSV handoff with signed reviewer identity and immutable audit export.
"""Prepare and apply Tier 4 arbitration decisions for PRANIK cases."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonlines
import structlog

from schemas.gold_label.gold_schema_v1 import (
    AnnotationMetadata,
    BenchmarkCase,
    EscalationGoldLabel,
    EscalationLevel,
    TriageGoldLabel,
    TriageSeverity,
    ValidationStatus,
)

# TODO(tier4): add arbitration workflow for kappa < 0.60 cases
# TODO(audit): export full annotation audit trail for ICMR compliance
# TODO(credits): integrate NMC CME credit tracking for annotators
# FUTURE: replace manual Label Studio with automated annotation API


logger = structlog.get_logger(__name__)

ARBITRATION_COLUMNS = [
    "case_id",
    "task",
    "language",
    "patient_query",
    "reviewer1_urgency",
    "reviewer2_urgency",
    "reviewer1_escalation_required",
    "reviewer2_escalation_required",
    "reviewer1_red_flags",
    "reviewer2_red_flags",
    "reviewer1_notes",
    "reviewer2_notes",
    "final_urgency",
    "final_escalation_required",
    "final_red_flags",
    "final_notes",
    "senior_reviewer",
    "decision_status",
]


def latest_arbitration_queue(queue_dir: Path) -> Path:
    """Return the newest non-empty Tier 4 queue JSONL."""

    candidates = sorted(
        queue_dir.glob("tier4_arbitration_*.jsonl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        if path.stat().st_size > 0:
            return path
    raise FileNotFoundError(f"No non-empty Tier 4 arbitration queue found in {queue_dir}")


def prepare_arbitration_template(
    queue_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Create a senior-review CSV template from a Tier 4 queue."""

    records = _read_queue(queue_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{queue_path.stem}_resolution_template_{timestamp}.csv"

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=ARBITRATION_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(_template_row(record))

    logger.info(
        "tier4_arbitration_template_prepared",
        queue_path=str(queue_path),
        output_path=str(output_path),
        rows=len(records),
    )
    return {"rows": len(records), "output_path": str(output_path)}


def apply_arbitration_resolutions(
    queue_path: Path,
    resolution_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Apply approved senior-review decisions and write gold cases."""

    queue_by_case_id = {
        str(record["case_id"]): record
        for record in _read_queue(queue_path)
        if record.get("case_id")
    }
    rows = _read_resolution_rows(resolution_path)
    approved_rows = [
        row for row in rows if row.get("decision_status", "").strip().lower() == "approved"
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    written_by_task: Counter[str] = Counter()
    skipped: list[dict[str, str]] = []
    existing_case_ids = _existing_gold_case_ids(output_dir)

    for row in approved_rows:
        case_id = row.get("case_id", "").strip()
        record = queue_by_case_id.get(case_id)
        if record is None:
            skipped.append({"case_id": case_id, "reason": "case_id_not_found_in_queue"})
            continue
        if case_id in existing_case_ids:
            skipped.append({"case_id": case_id, "reason": "already_exists_in_gold"})
            continue
        try:
            case = _arbitrated_gold_case(record, row)
        except Exception as exc:
            skipped.append({"case_id": case_id, "reason": str(exc)})
            continue
        _append_gold_case(case, output_dir)
        existing_case_ids.add(case.case_id)
        written_by_task[case.task] += 1

    summary = {
        "queue_path": str(queue_path),
        "resolution_path": str(resolution_path),
        "approved_rows": len(approved_rows),
        "written": sum(written_by_task.values()),
        "written_by_task": dict(written_by_task),
        "skipped": skipped,
        "output_dir": str(output_dir),
    }
    logger.info("tier4_arbitration_resolutions_applied", **summary)
    return summary


def _read_queue(queue_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with jsonlines.open(queue_path, mode="r") as reader:
        for payload in reader:
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _read_resolution_rows(resolution_path: Path) -> list[dict[str, str]]:
    with resolution_path.open("r", encoding="utf-8", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _template_row(record: dict[str, Any]) -> dict[str, str]:
    reviewer_labels = record.get("reviewer_labels")
    reviewers = reviewer_labels if isinstance(reviewer_labels, list) else []
    first = _labels_at(reviewers, 0)
    second = _labels_at(reviewers, 1)
    return {
        "case_id": str(record.get("case_id") or ""),
        "task": str(record.get("task") or ""),
        "language": str(record.get("language") or ""),
        "patient_query": str(record.get("patient_query") or ""),
        "reviewer1_urgency": first.get("urgency", ""),
        "reviewer2_urgency": second.get("urgency", ""),
        "reviewer1_escalation_required": first.get("escalation_required", ""),
        "reviewer2_escalation_required": second.get("escalation_required", ""),
        "reviewer1_red_flags": first.get("red_flags", ""),
        "reviewer2_red_flags": second.get("red_flags", ""),
        "reviewer1_notes": first.get("notes", ""),
        "reviewer2_notes": second.get("notes", ""),
        "final_urgency": "",
        "final_escalation_required": "",
        "final_red_flags": "",
        "final_notes": "",
        "senior_reviewer": "",
        "decision_status": "pending",
    }


def _labels_at(reviewers: list[Any], index: int) -> dict[str, str]:
    if index >= len(reviewers) or not isinstance(reviewers[index], dict):
        return {}
    labels = reviewers[index].get("labels")
    if not isinstance(labels, dict):
        return {}
    return {str(key): str(value) for key, value in labels.items()}


def _arbitrated_gold_case(record: dict[str, Any], row: dict[str, str]) -> BenchmarkCase:
    source_task = record.get("source_task")
    if not isinstance(source_task, dict):
        raise ValueError("missing source_task in arbitration queue")
    meta = source_task.get("meta")
    if not isinstance(meta, dict) or not isinstance(meta.get("source_case"), dict):
        raise ValueError("missing source_case in arbitration queue")

    case = BenchmarkCase.model_validate(meta["source_case"])
    gold_label = _updated_gold_label(case, row)
    reviewer_notes = list(case.annotation.reviewer_notes)
    senior_reviewer = row.get("senior_reviewer", "").strip()
    final_notes = row.get("final_notes", "").strip()
    note_parts = ["Tier 4 senior arbitration approved this case."]
    if senior_reviewer:
        note_parts.append(f"Senior reviewer: {senior_reviewer}.")
    if final_notes:
        note_parts.append(f"Decision notes: {final_notes}")
    reviewer_notes.append(" ".join(note_parts))

    annotation = AnnotationMetadata(
        annotator_tier=4,
        iaa_score=1.0,
        validation_status=ValidationStatus.APPROVED,
        clinical_reviewer_required=False,
        reviewer_notes=reviewer_notes,
    )
    return case.model_copy(
        deep=True,
        update={"gold_label": gold_label, "annotation": annotation},
    )


def _updated_gold_label(case: BenchmarkCase, row: dict[str, str]) -> Any:
    final_notes = row.get("final_notes", "").strip()
    final_red_flags = _split_csv(row.get("final_red_flags", ""))

    if isinstance(case.gold_label, TriageGoldLabel):
        final_urgency = row.get("final_urgency", "").strip()
        final_escalation = row.get("final_escalation_required", "").strip()
        if final_urgency not in {item.value for item in TriageSeverity}:
            raise ValueError("final_urgency must be one of EMERGENCY/URGENT/ROUTINE/SELF_CARE")
        if final_escalation.lower() not in {"yes", "no", "true", "false"}:
            raise ValueError("final_escalation_required must be yes/no")
        updates: dict[str, Any] = {
            "urgency": TriageSeverity(final_urgency),
            "escalation_required": final_escalation.lower() in {"yes", "true"},
        }
        if final_red_flags:
            updates["detected_red_flags"] = final_red_flags
        if final_notes:
            updates["reasoning"] = final_notes
            updates["escalation_reasoning"] = final_notes
        return case.gold_label.model_copy(update=updates)

    if isinstance(case.gold_label, EscalationGoldLabel):
        final_escalation = row.get("final_escalation_required", "").strip()
        final_level = row.get("final_escalation_level", "").strip()
        if final_escalation.lower() not in {"yes", "no", "true", "false"}:
            raise ValueError("final_escalation_required must be yes/no")
        updates = {
            "should_escalate": final_escalation.lower() in {"yes", "true"},
        }
        if final_level:
            updates["escalation_level"] = EscalationLevel(final_level)
        if final_red_flags:
            updates["matched_triggers"] = final_red_flags
        if final_notes:
            updates["reasoning"] = final_notes
        return case.gold_label.model_copy(update=updates)

    if final_notes:
        return case.gold_label.model_copy(update={"reasoning": final_notes})
    return case.gold_label


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _existing_gold_case_ids(output_dir: Path) -> set[str]:
    case_ids: set[str] = set()
    if not output_dir.exists():
        return case_ids
    for path in output_dir.glob("*_gold_v1.jsonl"):
        with jsonlines.open(path, mode="r") as reader:
            for payload in reader:
                if isinstance(payload, dict) and isinstance(payload.get("case_id"), str):
                    case_ids.add(payload["case_id"])
    return case_ids


def _append_gold_case(case: BenchmarkCase, output_dir: Path) -> None:
    path = output_dir / f"{case.task}_gold_v1.jsonl"
    with jsonlines.open(path, mode="a") as writer:
        writer.write(case.model_dump(mode="json"))
