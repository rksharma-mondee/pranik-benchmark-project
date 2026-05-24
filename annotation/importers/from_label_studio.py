# pranik/annotation/importers/from_label_studio.py
# Status: draft
# Clinical Reviewer Required: yes - this is the clinical review system
# TODO: Persist full reviewer identity metadata after compliance review.
"""Convert completed Label Studio annotations back into PRANIK gold cases."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import jsonlines
import structlog

from annotation.iaa.cohen_kappa import extract_case_id, extract_label_value
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


def label_studio_task_to_gold_case(
    task: dict[str, Any],
    *,
    iaa_score: float,
    annotator_tier: int,
) -> BenchmarkCase:
    """Build an approved benchmark case from a completed Label Studio task."""

    source_case = _source_case_payload(task)
    case = BenchmarkCase.model_validate(source_case)
    consensus = _consensus_annotation(task)
    updated_gold = _updated_gold_label(case, consensus)
    reviewer_notes = list(case.annotation.reviewer_notes)
    notes = consensus.get("notes")
    if notes:
        reviewer_notes.append(f"Label Studio reviewer notes: {notes}")

    annotation = AnnotationMetadata(
        annotator_tier=annotator_tier,
        iaa_score=iaa_score,
        validation_status=ValidationStatus.APPROVED,
        clinical_reviewer_required=False,
        reviewer_notes=reviewer_notes,
    )
    return case.model_copy(
        deep=True,
        update={
            "gold_label": updated_gold,
            "annotation": annotation,
        },
    )


def write_gold_cases(
    tasks: list[dict[str, Any]],
    output_dir: Path,
    *,
    iaa_score: float,
) -> dict[str, int]:
    """Write approved Label Studio tasks into task-specific gold JSONL files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    written_by_task: Counter[str] = Counter()
    writers: dict[str, jsonlines.Writer] = {}
    handles: list[Any] = []
    try:
        for task in tasks:
            tier = _tier_required(task)
            case = label_studio_task_to_gold_case(
                task,
                iaa_score=iaa_score,
                annotator_tier=tier,
            )
            writer = writers.get(case.task)
            if writer is None:
                path = output_dir / f"{case.task}_gold_v1.jsonl"
                handle = path.open("a", encoding="utf-8")
                handles.append(handle)
                writer = jsonlines.Writer(handle)
                writers[case.task] = writer
            writer.write(case.model_dump(mode="json"))
            written_by_task[case.task] += 1
    finally:
        for writer in writers.values():
            writer.close()
        for handle in handles:
            handle.close()

    logger.info(
        "label_studio_gold_cases_written",
        output_dir=str(output_dir),
        counts=dict(written_by_task),
    )
    return dict(written_by_task)


def _source_case_payload(task: dict[str, Any]) -> dict[str, Any]:
    meta = task.get("meta")
    if isinstance(meta, dict):
        source_case = meta.get("source_case")
        if isinstance(source_case, dict):
            return source_case

    data = task.get("data")
    if isinstance(data, dict):
        source_case = data.get("source_case")
        if isinstance(source_case, dict):
            return source_case

    case_id = extract_case_id(task) or "unknown"
    raise ValueError(f"Label Studio task {case_id} does not include meta.source_case")


def _consensus_annotation(task: dict[str, Any]) -> dict[str, Any]:
    annotations = task.get("annotations")
    if not isinstance(annotations, list) or not annotations:
        raise ValueError(f"Label Studio task {extract_case_id(task)} has no annotations")

    field_names = {
        "urgency",
        "escalation_required",
        "escalation_level",
        "red_flags",
        "notes",
        "ai_correct",
        "clinical_correctness",
        "safety_risk",
    }
    consensus: dict[str, Any] = {}
    for field_name in field_names:
        values = [
            extract_label_value(annotation, field_name)
            for annotation in annotations
            if extract_label_value(annotation, field_name) not in (None, "")
        ]
        if values:
            consensus[field_name] = Counter(str(value) for value in values).most_common(1)[0][0]
    return consensus


def _updated_gold_label(case: BenchmarkCase, annotation: dict[str, Any]) -> Any:
    if isinstance(case.gold_label, TriageGoldLabel):
        updates: dict[str, Any] = {}
        urgency = annotation.get("urgency")
        if urgency:
            updates["urgency"] = TriageSeverity(str(urgency))
        escalation_required = annotation.get("escalation_required")
        if escalation_required:
            updates["escalation_required"] = str(escalation_required).lower() == "yes"
        red_flags = _split_csv(annotation.get("red_flags"))
        if red_flags:
            updates["detected_red_flags"] = red_flags
        notes = annotation.get("notes")
        if notes:
            updates["reasoning"] = str(notes)
            updates["escalation_reasoning"] = str(notes)
        return case.gold_label.model_copy(update=updates)

    if isinstance(case.gold_label, EscalationGoldLabel):
        updates = {}
        escalation_required = annotation.get("escalation_required")
        if escalation_required:
            updates["should_escalate"] = str(escalation_required).lower() == "yes"
        escalation_level = annotation.get("escalation_level")
        if escalation_level:
            updates["escalation_level"] = EscalationLevel(str(escalation_level))
        red_flags = _split_csv(annotation.get("red_flags"))
        if red_flags:
            updates["matched_triggers"] = red_flags
        notes = annotation.get("notes")
        if notes:
            updates["reasoning"] = str(notes)
        return case.gold_label.model_copy(update=updates)

    notes = annotation.get("notes")
    if notes:
        return case.gold_label.model_copy(update={"reasoning": str(notes)})
    return case.gold_label


def _split_csv(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _tier_required(task: dict[str, Any]) -> int:
    meta = task.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("tier_required"), int):
        return int(meta["tier_required"])
    data = task.get("data")
    task_name = data.get("task") if isinstance(data, dict) else None
    return 3 if task_name in {"triage", "escalation", "refusal_behavior"} else 2
