# pranik/annotation/exporters/to_label_studio.py
# Status: draft
# Clinical Reviewer Required: yes - this is the clinical review system
# TODO: Add per-task reviewer instructions once clinician guidelines are signed off.
"""Convert PRANIK benchmark cases into Label Studio task payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonlines
import structlog

from schemas.gold_label.gold_schema_v1 import BenchmarkCase, ValidationStatus

# TODO(tier4): add arbitration workflow for kappa < 0.60 cases
# TODO(audit): export full annotation audit trail for ICMR compliance
# TODO(credits): integrate NMC CME credit tracking for annotators
# FUTURE: replace manual Label Studio with automated annotation API


logger = structlog.get_logger(__name__)

TIER_3_TASKS = {"triage", "escalation", "refusal_behavior"}


def _get_required_tier(task: str) -> int:
    """Return minimum reviewer tier for the task."""

    return 3 if task in TIER_3_TASKS else 2


def benchmark_case_to_ls_task(case: BenchmarkCase) -> dict[str, Any]:
    """Convert one validated benchmark case into a Label Studio task."""

    return {
        "data": {
            "case_id": case.case_id,
            "task": case.task,
            "language": case.language.value,
            "patient_query": case.input.patient_query,
            "context_type": case.input.context_type.value,
            "literacy_level": case.input.literacy_level.value,
            "ai_prelabel": json.dumps(
                case.gold_label.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            "is_synthetic": case.annotation.annotator_tier == 1,
        },
        "meta": {
            "case_id": case.case_id,
            "tier_required": _get_required_tier(case.task),
            "source_case": case.model_dump(mode="json"),
        },
    }


def load_draft_cases(input_dir: Path) -> list[BenchmarkCase]:
    """Load schema-valid draft benchmark cases from JSONL files."""

    cases: list[BenchmarkCase] = []
    for path in _jsonl_paths(input_dir):
        with jsonlines.open(path, mode="r") as reader:
            for payload in reader:
                try:
                    case = BenchmarkCase.model_validate(payload)
                except Exception as exc:
                    logger.warning(
                        "label_studio_case_skipped",
                        source_path=str(path),
                        case_id=payload.get("case_id") if isinstance(payload, dict) else None,
                        error=str(exc),
                    )
                    continue

                if case.annotation.validation_status == ValidationStatus.DRAFT:
                    cases.append(case)
    return cases


def export_label_studio_tasks(input_dir: Path, output_path: Path) -> dict[str, int]:
    """Write draft benchmark cases as Label Studio import JSONL."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cases = load_draft_cases(input_dir)
    with jsonlines.open(output_path, mode="w") as writer:
        for case in cases:
            writer.write(benchmark_case_to_ls_task(case))

    logger.info(
        "label_studio_tasks_exported",
        input_dir=str(input_dir),
        output_path=str(output_path),
        task_count=len(cases),
    )
    return {"exported": len(cases)}


def _jsonl_paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    return sorted(item for item in path.glob("*.jsonl") if item.is_file())
