# pranik/preprocessing/pipeline.py
# Status: draft
# Clinical Reviewer Required: no
# DPDP 2025: this file is part of the compliance pipeline - do not skip
# TODO: Add Setu deduplication (MinHash LSH) in Phase 3.
"""Preprocessing pipeline for PRANIK benchmark cases."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import sys
from typing import Any, Optional

import jsonlines
from pydantic import BaseModel, Field
import structlog

from preprocessing.configs.preprocessing_config import PreprocessingConfig
from preprocessing.language_detector import detect_language, validate_language
from preprocessing.normalizer import normalize_case
from preprocessing.pii_scrubber import scrub_case


# TODO(dedup): add MinHash LSH deduplication via Setu in Phase 3
# TODO(indic): replace langdetect with IndicLID for better Indic accuracy
# TODO(consent): add consent_verified field check before processing real data
# TODO(erasure): implement case deletion by case_id for DPDP erasure rights
# FUTURE: integrate Presidio with custom MedNER for clinical entity types


PIPELINE_VERSION = "v1.0"
logger = structlog.get_logger(__name__)


class PreprocessingStatus(str, Enum):
    PASSED = "passed"
    SCRUBBED = "scrubbed"
    REJECTED = "rejected"
    WARNING = "warning"


class PIIFinding(BaseModel):
    entity_type: str
    start: int
    end: int
    score: float
    scrubbed_value: str


class PreprocessingResult(BaseModel):
    case_id: str
    status: PreprocessingStatus
    pii_findings: list[PIIFinding] = Field(default_factory=list)
    pii_scrubbed: bool = False
    detected_language: Optional[str] = None
    language_confidence: Optional[float] = None
    language_matches_declared: Optional[bool] = None
    rejection_reason: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    processed_case: Optional[dict[str, Any]] = None
    processed_at: datetime
    pipeline_version: str = PIPELINE_VERSION


@dataclass
class _DatasetRunReport:
    files_processed: int = 0
    total_cases: int = 0
    counts: dict[str, int] = field(
        default_factory=lambda: {
            PreprocessingStatus.PASSED.value: 0,
            PreprocessingStatus.SCRUBBED.value: 0,
            PreprocessingStatus.REJECTED.value: 0,
            PreprocessingStatus.WARNING.value: 0,
        }
    )
    pii_entity_counts: Counter[str] = field(default_factory=Counter)
    input_dir: Path = Path("datasets/synthetic")
    output_dir: Path = Path("datasets/processed")
    rejected_dir: Path = Path("datasets/rejected")
    audit_log_path: Path = Path("datasets/audit/pii_audit_log.jsonl")


_LAST_RUN_REPORT: _DatasetRunReport | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_patient_query(case: dict[str, Any]) -> Optional[str]:
    case_input = case.get("input")
    if not isinstance(case_input, dict):
        return None
    patient_query = case_input.get("patient_query")
    return patient_query if isinstance(patient_query, str) and patient_query.strip() else None


def _language_allowed(declared: Optional[str], config: PreprocessingConfig) -> bool:
    return declared in config.allowed_languages


def _write_audit_log(
    result: PreprocessingResult,
    declared_language: Optional[str],
    config: PreprocessingConfig,
) -> None:
    if not config.save_audit_log:
        return

    config.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "case_id": result.case_id,
        "timestamp": result.processed_at.isoformat(),
        "status": result.status.value,
        "pii_entity_types_found": sorted({finding.entity_type for finding in result.pii_findings}),
        "language_detected": result.detected_language,
        "language_declared": declared_language,
        "language_match": result.language_matches_declared,
        "pipeline_version": result.pipeline_version,
    }
    with jsonlines.open(config.audit_log_path, mode="a") as writer:
        writer.write(entry)


def _rejected_result(
    case_id: str,
    reason: str,
    declared_language: Optional[str],
    config: PreprocessingConfig,
    warnings: Optional[list[str]] = None,
    processed_case: Optional[dict[str, Any]] = None,
    pii_findings: Optional[list[PIIFinding]] = None,
    detected_language: Optional[str] = None,
    language_confidence: Optional[float] = None,
    language_matches_declared: Optional[bool] = None,
) -> PreprocessingResult:
    result = PreprocessingResult(
        case_id=case_id,
        status=PreprocessingStatus.REJECTED,
        pii_findings=[f.model_dump() for f in pii_findings] if pii_findings else [],
        pii_scrubbed=bool(pii_findings),
        detected_language=detected_language,
        language_confidence=language_confidence,
        language_matches_declared=language_matches_declared,
        rejection_reason=reason,
        warnings=warnings or [],
        processed_case=processed_case,
        processed_at=_utc_now(),
    )
    _write_audit_log(result, declared_language, config)
    return result


def preprocess_case(case: dict[str, Any], config: PreprocessingConfig) -> PreprocessingResult:
    """Normalize, language-check, PII-scrub, audit, and return one case result."""

    case_id = str(case.get("case_id", "unknown"))
    declared_language = case.get("language")
    declared_language = str(declared_language) if declared_language is not None else None

    normalized = normalize_case(case, config)
    patient_query = _get_patient_query(normalized)
    if patient_query is None:
        scrubbed_case, pii_findings = scrub_case(normalized, config)
        return _rejected_result(
            case_id=case_id,
            reason="Missing required field: input.patient_query",
            declared_language=declared_language,
            config=config,
            processed_case=scrubbed_case,
            pii_findings=pii_findings,
        )

    detected_language: Optional[str] = declared_language
    language_confidence: Optional[float] = 0.0
    language_matches_declared: Optional[bool] = True
    warnings: list[str] = []

    if config.language_validation_enabled:
        detected_language, language_confidence = detect_language(patient_query, declared_language)
        language_matches_declared, warnings = validate_language(
            detected_language,
            declared_language,
            language_confidence,
        )

    scrubbed_case, pii_findings = scrub_case(normalized, config)
    pii_scrubbed = bool(pii_findings)

    if config.language_validation_enabled and not _language_allowed(declared_language, config):
        return _rejected_result(
            case_id=case_id,
            reason=f"Unsupported or missing language: {declared_language}",
            declared_language=declared_language,
            config=config,
            warnings=warnings,
            processed_case=scrubbed_case,
            pii_findings=pii_findings,
            detected_language=detected_language,
            language_confidence=language_confidence,
            language_matches_declared=language_matches_declared,
        )

    if pii_scrubbed and config.fail_on_pii_detection:
        return _rejected_result(
            case_id=case_id,
            reason="PII detected and fail_on_pii_detection=True",
            declared_language=declared_language,
            config=config,
            warnings=warnings,
            processed_case=scrubbed_case,
            pii_findings=pii_findings,
            detected_language=detected_language,
            language_confidence=language_confidence,
            language_matches_declared=language_matches_declared,
        )

    if pii_scrubbed:
        status = PreprocessingStatus.SCRUBBED
    elif warnings:
        status = PreprocessingStatus.WARNING
    else:
        status = PreprocessingStatus.PASSED

    result = PreprocessingResult(
        case_id=case_id,
        status=status,
        pii_findings=[f.model_dump() for f in pii_findings],
        pii_scrubbed=pii_scrubbed,
        detected_language=detected_language,
        language_confidence=language_confidence,
        language_matches_declared=language_matches_declared,
        warnings=warnings,
        processed_case=scrubbed_case,
        processed_at=_utc_now(),
    )
    _write_audit_log(result, declared_language, config)
    return result


def _iter_jsonl_records(path: Path) -> list[tuple[int, dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any]]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                record = {
                    "case_id": f"{path.stem}:line-{line_number}",
                    "language": None,
                    "_preprocessing_parse_error": "Invalid JSONL record",
                }
            records.append((line_number, record))
    return records


def _extract_case(record: dict[str, Any]) -> dict[str, Any]:
    parsed_case = record.get("parsed_case")
    if isinstance(parsed_case, dict):
        return parsed_case
    return record


def _write_rejected(
    writer: jsonlines.Writer,
    original_record: dict[str, Any],
    result: PreprocessingResult,
) -> None:
    writer.write(
        {
            "case_id": result.case_id,
            "rejection_reason": result.rejection_reason,
            "warnings": result.warnings,
            "preprocessing_result": result.model_dump(mode="json", exclude={"processed_case"}),
            "case": result.processed_case if result.processed_case is not None else original_record,
        }
    )


def preprocess_dataset(input_dir: Path, config: PreprocessingConfig) -> dict[str, int]:
    """Preprocess every JSONL case file under input_dir."""

    global _LAST_RUN_REPORT

    input_dir = Path(input_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.rejected_dir.mkdir(parents=True, exist_ok=True)
    if config.save_audit_log:
        config.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    report = _DatasetRunReport(
        input_dir=input_dir,
        output_dir=config.output_dir,
        rejected_dir=config.rejected_dir,
        audit_log_path=config.audit_log_path,
    )

    for input_file in sorted(input_dir.glob("*.jsonl")):
        report.files_processed += 1
        output_file = config.output_dir / input_file.name
        rejected_file = config.rejected_dir / input_file.name

        with jsonlines.open(output_file, mode="w") as output_writer, jsonlines.open(
            rejected_file, mode="w"
        ) as rejected_writer:
            for _line_number, record in _iter_jsonl_records(input_file):
                case = _extract_case(record)
                result = preprocess_case(case, config)
                report.total_cases += 1
                report.counts[result.status.value] += 1
                report.pii_entity_counts.update(finding.entity_type for finding in result.pii_findings)

                if result.status == PreprocessingStatus.REJECTED:
                    _write_rejected(rejected_writer, record, result)
                elif result.processed_case is not None:
                    output_writer.write(result.processed_case)

    logger.info(
        "preprocessing_dataset_complete",
        input_dir=str(input_dir),
        output_dir=str(config.output_dir),
        rejected_dir=str(config.rejected_dir),
        counts=report.counts,
        files_processed=report.files_processed,
        total_cases=report.total_cases,
    )
    _LAST_RUN_REPORT = report
    return dict(report.counts)


def _format_percent(count: int, total: int) -> str:
    if total == 0:
        return " 0.0%"
    return f"{(count / total) * 100:4.1f}%"


def format_stdout_summary(summary: dict[str, int]) -> str:
    """Format the most recent dataset run using the requested console layout."""

    report = _LAST_RUN_REPORT or _DatasetRunReport(counts=summary)
    passed = summary.get(PreprocessingStatus.PASSED.value, 0)
    scrubbed = summary.get(PreprocessingStatus.SCRUBBED.value, 0)
    warning = summary.get(PreprocessingStatus.WARNING.value, 0)
    rejected = summary.get(PreprocessingStatus.REJECTED.value, 0)
    total = report.total_cases

    pii_lines = []
    for entity_type, count in sorted(report.pii_entity_counts.items()):
        occurrence = "occurrence" if count == 1 else "occurrences"
        pii_lines.append(f"{entity_type:<16}: {count} {occurrence}")
    pii_block = "\n".join(pii_lines) if pii_lines else "None"

    return "\n".join(
        [
            "════════════════════════════════════════════",
            "PRANIK Preprocessing Pipeline",
            f"Input : {report.input_dir}/",
            f"Output: {report.output_dir}/",
            "════════════════════════════════════════════",
            f"Files processed   : {report.files_processed}",
            f"Total cases       : {total}",
            "────────────────────────────────────────────",
            f"✅ Passed         : {passed:2d}  ({_format_percent(passed, total)})",
            f"⚠  Scrubbed (PII) : {scrubbed:2d}  ({_format_percent(scrubbed, total)})  "
            "→ kept, PII removed",
            f"⚠  Warning        : {warning:2d}  ({_format_percent(warning, total)})  "
            "→ language mismatch",
            f"❌ Rejected       : {rejected:2d}  ({_format_percent(rejected, total)})  "
            f"→ saved to {report.rejected_dir}/",
            "PII Entity Types Found:",
            pii_block,
            f"Audit log saved: {report.audit_log_path}",
            "════════════════════════════════════════════",
        ]
    )


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    pipeline_config = PreprocessingConfig()
    dataset_summary = preprocess_dataset(
        input_dir=Path("datasets/synthetic"),
        config=pipeline_config,
    )
    print(format_stdout_summary(dataset_summary))
